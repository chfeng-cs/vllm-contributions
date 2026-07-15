# LMCache KV 加载函数源码分析

## `get_num_new_matched_tokens()`

位置：
[`LMCacheMPConnector.get_num_new_matched_tokens()`](https://github.com/vllm-project/vllm/blob/main/vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py)

接口定义：

```python
def get_num_new_matched_tokens(
    request: Request,
    num_computed_tokens: int,
) -> tuple[int | None, bool]:
    ...
```

这个函数在 scheduler 尝试调度 waiting request 时调用。它回答两个问题：

1. 除了 vLLM 本地已经计算或缓存的 token，外部 KV Cache 还能提供多少 token？
2. 如果存在外部命中，后续加载是否是异步的？

参数含义：

- `request`：当前请求，包含 `request_id`、完整 token IDs、`cache_salt` 和请求状态；
- `num_computed_tokens`：vLLM 本地已经拥有 KV 的 token 数量；它可能来自本次计算，也可能来自
  vLLM 自己的 prefix cache。

返回值是 `(num_external_tokens, load_kv_async)`：

| 返回值 | scheduler 的处理 |
|---|---|
| `(None, True)` | lookup 尚未完成；请求移出本轮候选，放回 waiting queue，之后再次查询 |
| `(0, False)` | LMCache 没有额外命中，不需要外部加载 |
| `(N, True)` | 需要从 LMCache 异步加载 `N` 个 token 的 KV |

函数内部首先取得或创建 `LMCacheMPRequestTracker`。对于 preempted request，当前实现直接返回
`(0, False)`，因为暂不支持为被抢占请求重新加载外部 KV。

随后它调用：

```python
scheduler_adapter.maybe_submit_lookup_request(...)
ret = scheduler_adapter.check_lookup_result(request.request_id)
```

`maybe_submit_lookup_request()` 是幂等入口：如果同一个 `request_id` 已经存在 lookup future，
它不会重复提交。因此入队时预取优化可以在请求入队时先调用它，而
`get_num_new_matched_tokens()` 仍保留这次调用作为兜底。

当 `ret` 是命中的 token 总数时，还需要扣掉本地已有的部分：

```python
need_to_load = max(0, ret - num_computed_tokens)
```

例如 LMCache 命中前 8,192 tokens，而 vLLM 本地已经命中前 2,048 tokens，那么真正需要从
外部加载的只有 6,144 tokens。

函数还会检查 LMCache 命中长度是否与 chunk 和 vLLM block 的边界对齐，并把本地、外部命中
block 数写入 request tracker，供后续 block 分配、retrieve 和 lock 释放使用。

## `maybe_submit_lookup_request()`

这个函数位于 scheduler adapter 中，负责把 lookup 请求发送给 LMCache，并将返回的 future
记录在 `lookup_futures[request_id]`。

它的关键行为包括：

- 同一个 `request_id` 只允许存在一个进行中的 lookup；
- token 模式会把 token IDs 截断到 LMCache chunk 对齐的长度；
- lookup 会锁定命中的 LMCache chunks，避免它们在后续 retrieve 前被淘汰；
- 函数只负责提交，不等待结果，因此不会阻塞 scheduler。

原流程第一次执行 `get_num_new_matched_tokens()` 时才提交 lookup。入队时预取优化利用
`on_new_request()` hook，在请求刚进入 waiting queue 时就执行这一步，让 lookup 与 queue wait
并行。

## `check_lookup_result()`

`check_lookup_result(request_id)` 是 lookup 的非阻塞结果检查函数，也是
`get_num_new_matched_tokens()` 的下一步。

它先找到之前保存的 future：

```python
future = lookup_futures[request_id]
```

然后检查 future 是否完成：

```python
if not future.query():
    return None
```

返回 `None` 不代表未命中，而是“结果还没准备好”。scheduler 因此不会阻塞等待，而是跳过
这个请求，在后续调度轮次再次调用 `get_num_new_matched_tokens()`。

future 完成后，LMCache 返回连续命中的 chunk 数量。adapter 将它转换为 token 数：

```python
num_chunks = future.result()
return num_chunks * chunk_size
```

KV Cache 必须从 prompt 开头连续命中，才能直接作为已计算前缀使用。因此，这个函数返回的是 LMCache 中可用的**最长连续 prefix**长度，而不是所有零散命中chunk 的总和。

## `update_state_after_alloc()`

lookup 只告诉 scheduler 需要加载多少 token。scheduler 还要先调用 KV cache manager 分配
目标 GPU blocks，然后通过 `update_state_after_alloc()` 把 block IDs 记录到 request tracker。

对于需要 retrieve 的请求，状态机会发生如下变化：

```text
PREFETCHING → WAITING_FOR_LOAD → READY
```

- `PREFETCHING`：lookup 正在进行，或结果已经得到但尚未完成 block 分配；
- `WAITING_FOR_LOAD`：目标 blocks 已分配，可以生成 retrieve metadata；
- `READY`：不需要 retrieve，或加载流程已经完成。

这个函数还负责清理 lookup future，并释放本地 vLLM 已命中部分对应的 LMCache lookup locks。
只保留真正需要 retrieve 的 chunk locks，可以避免缓存块长期被无意义地占用。

## `start_load_kv()`

`start_load_kv()` 是 worker-side 函数，在 model forward 开始前调用：

```python
def start_load_kv(forward_context: ForwardContext, **kwargs) -> None:
    ...
```

在调用之前，scheduler 已经通过 `build_connector_meta()` 把 request ID、操作描述、GPU block
映射和 `cache_salt` 等信息放进 `LMCacheMPConnectorMetadata`，并随 scheduler output 发送到
worker。

`start_load_kv()` 的主要步骤是：

1. 从当前 connector metadata 中筛选 `direction == "RETRIEVE"` 的请求；
2. 收集每个请求的 `request_id`、`LoadStoreOp` 和 `cache_salt`；
3. 在当前 CUDA stream 上记录一个可跨进程使用的 CUDA event；
4. 调用 `worker_adapter.batched_submit_retrieve_requests()` 批量提交加载任务。

CUDA event 用来建立正确的执行顺序：LMCache 后台 worker 必须等 vLLM 当前 stream 到达该
event 后，才能安全地向目标 paged KV blocks 写入数据。

这个函数名虽然是 `start_load_kv`，但它主要负责**发起**异步 retrieve：执行 H2D，将 CPU
memory 中已经暂存的 KV 写入 GPU memory。初始化时预先注册的 CUDA IPC 显存映射让 LMCache
server 能访问 vLLM 分配的 paged KV blocks；本次调用创建的 IPC event 则负责跨进程同步。
它不会同步等待所有 KV 搬运结束；加载完成
情况由 connector 的异步完成机制继续跟踪，worker forward 结束时还会通过 `get_finished()`
和 `get_block_ids_with_load_errors()` 回传完成请求与失败 block 信息。
