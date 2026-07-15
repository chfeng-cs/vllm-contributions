# 入队时 KV Cache 预取：隐藏排队阶段的存储 I/O

> PR：[vllm-project/vllm#42321](https://github.com/vllm-project/vllm/pull/42321)  
> 主题：在 `LMCacheMPConnector` 中实现 eager KV prefetch  
> 关键词：vLLM、LMCache、KV Cache、异步预取、TTFT、调度器

## 背景

在使用磁盘作为 L2 KV Cache 的场景里，从磁盘加载 KV Cache 可能需要数百毫秒。
原来的流程要等请求真正被 scheduler 选中后，才会发起 LMCache lookup：

```text
请求入队 → 排队等待 → scheduler 选中 → 从磁盘加载 KV → prefill
```

当系统负载较高时，请求会在 waiting queue 中停留一个或多个调度周期。这段排队时间
本来可以用来加载 KV Cache，但旧流程没有利用它。结果是请求已经排完队，GPU 还要继续
等待磁盘 I/O，TTFT（Time to First Token）因此增加。

PR #42321 将 lookup 提前到请求入队的时刻：

```text
请求入队 → 异步加载磁盘 KV ┐
         → 排队等待         ├→ scheduler 选中 → prefill
                            ┘
```

这个优化没有让磁盘变快，而是把磁盘 I/O 隐藏在本来就存在的排队时间里。

## 实现

此前的 [PR #41383](https://github.com/vllm-project/vllm/pull/41383) 增加了
`on_new_request()` hook，它会在请求进入 waiting queue 时被调用。PR #42321 在
`LMCacheMPConnector` 中实现这个 hook，并调用 `maybe_submit_lookup_request()`，将 lookup
交给后台 worker 异步执行。

改动保持了较小的范围：

- 只修改 `LMCacheMPConnector`，不修改 scheduler、engine core 或其他 connector；
- 使用 `kv_transfer_config.extra_config` 中的 `lmcache.mp.eager_prefetch` 开关；
- 默认关闭，确保现有用户的行为不变；
- 跳过 resumable request，因为它在入队时的 token IDs 可能还不完整。

启用方式：

```yaml
kv_transfer_config:
  extra_config:
    lmcache.mp.eager_prefetch: true
```

这里需要特别区分 LMCache 的两个 connector：`LMCacheConnectorV1` 是同步、同进程的实现，
而 `LMCacheMPConnector` 会把 lookup 分发给后台进程。提前预取依赖后者的异步能力，因此
这个 PR 的实现目标是 `LMCacheMPConnector`。

## 实验设计

### 环境

- NVIDIA L20 45 GiB
- Llama 3.1 8B
- Intel Xeon
- 64 GiB RAM
- 每个请求复用磁盘上 8,767 tokens 的 KV context
- 5 个请求，以 2.4 秒固定间隔依次提交
- 每组数据重复 3 次后取平均值

为了定位每个阶段的耗时，我分别在 vLLM 和 LMCache 中加入了计时：

- [vLLM benchmark 分支](https://github.com/chfeng-cs/vllm/tree/lmcache-eager-prefetch-bench)
- [LMCache timing 分支](https://github.com/chfeng-cs/LMCache/tree/eager-prefetch-timing)

### 排除多层缓存干扰

这个 PR 最难的部分不是十几行实现，而是证明优化确实来自“提前发起磁盘读取”。KV Cache
的读取路径上有多层缓存，任何一层命中都会掩盖真实的磁盘开销。

首先，vLLM 的 GPU prefix cache 会让重复请求直接命中显存，因此实验使用：

```bash
--no-enable-prefix-caching
```

其次，LMCache 的 L1 内存缓存也会让后续请求绕过磁盘。实验使用 `skip_l1`，让 L1 退化为
不保留数据的 write-through buffer，保证读取落到 L2 磁盘。

操作系统 page cache 更难完全排除。在虚拟化云主机上，我没有权限通过系统接口清理缓存；
`O_DIRECT` 也不能消除所有存储栈干扰。因此实验需要准备多条请求、重复测量，并结合分阶段
计时确认数据确实来自预期路径。

## 结果

第一个请求没有队列压力，baseline 与 eager prefetch 的 TTFT 基本相同，约为 304–306 ms，
说明在无 backlog 时没有测得明显额外开销。

后续请求中，decode 约需 2.24 秒，而请求每 2.4 秒提交一次；再算上 lookup 和 prefill，
完整处理周期超过了提交间隔。每轮留下的小幅重叠逐渐累积，使 baseline 请求越来越晚才开始
磁盘 lookup；到第 5 个请求时，纯排队等待约为 467 ms。

启用 eager prefetch 后，每个请求一入队就开始读取磁盘，等 scheduler 选中它时 KV Cache
通常已经就绪。因此 TTFT 稳定在约 306 ms，最后一个请求约提前 470 ms 完成；在这组高负载
实验中，TTFT 最多降低约 28%。

结果验证了这项优化的核心：单项操作耗时没有变短，收益来自将磁盘 I/O 与 scheduler queue
wait 重叠。

## 实验过程中踩过的坑

1. **选错 connector。** 一开始没有分清 `LMCacheConnectorV1` 和
   `LMCacheMPConnector`，在同步 connector 上花了不少时间。理解执行模型比直接开始改代码更重要。
2. **缓存会让结果看起来过于漂亮。** GPU prefix cache、LMCache L1 和操作系统 page cache
   必须分别处理，不能只关闭其中一层。
3. **冷启动状态难以复现。** LMCache 当时不能在重启后直接复用之前的缓存；但重新 warm-up
   又可能给后续测量留下缓存，实验流程必须在可复现性和冷读真实性之间权衡。
4. **缺少端到端分阶段指标。** TTFT、入队时间、queue wait 和磁盘加载时间没有一个现成 API
   能全部提供，只能在 vLLM 与 LMCache 两侧插桩，并反复核对时间点。
5. **负载太轻或太重都不合适。** 太轻看不到优化，太重则无法代表生产环境，还可能把结论
   变成“磁盘越慢收益越大”。

## 延伸发现

在理解 lookup 生命周期和设计实验的过程中，我还发现了几个独立问题，包括 `cache_salt`
传递遗漏、请求中止时 lookup lock 可能泄漏，以及 LMCache 重启后缓存复用能力不足。这些问题
后来也成为继续排查和贡献的方向。

## 总结

PR #42321 是一个代码改动很小、验证成本却很高的性能优化。它带给我的主要经验是：

- 对异步系统而言，优化的关键经常不是减少工作量，而是改变工作的开始时间；
- 性能结论必须建立在可解释的 timeline 上，只有 TTFT 总数还不够；
