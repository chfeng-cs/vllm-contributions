# Open Source Contributions — Ethan Feng (chfeng-cs)

Focused area: **KV Cache Transfer · Scheduler Optimization**

Core repos: [vllm-project/vllm](https://github.com/vllm-project/vllm) · [sgl-project/sglang](https://github.com/sgl-project/sglang) · [flashinfer-ai/flashinfer](https://github.com/flashinfer-ai/flashinfer)

---

## Contributions

<!-- PR_TABLE_START -->

<details open>
<summary>Issue</summary>

| Issue | Title | Status | Impact |
|-------|-------|--------|--------|
| [vllm#42846](https://github.com/vllm-project/vllm/issues/42846) | [Bug][CI] NIXL + FlashInfer fails with Qwen3 MRV2 and --block-size 128 | ☑️ Closed | — |
</details>

### Feature

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42321](https://github.com/vllm-project/vllm/pull/42321) | [KV Connector] Eager KV prefetch at request enqueue time in `LMCacheMPConnector` | 🔄 Open | ~25% TTFT reduction (benchmarked under high load with disk KV prefetch, L20) |
| [vllm#41847](https://github.com/vllm-project/vllm/pull/41847) | [KV Transfer] Enable HMA by default for connectors that support it | ☑️ Merged | Reduces user config burden; fixes MultiConnector gap vs PR #42045 |
| [flashinfer#3280](https://github.com/flashinfer-ai/flashinfer/pull/3280) | feat(norm): support weightless RMSNorm for FlashNorm weight folding (#3200) | 🔄 Open | — |

### Metrics

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42206](https://github.com/vllm-project/vllm/pull/42206) | [Metrics] Add group-aware KV cache capacity to vllm:cache_config_info | ☑️ Merged | Add group-aware KV cache capacity Prometheus gauges |

### Bug Fix

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#44101](https://github.com/vllm-project/vllm/pull/44101) | [LMCache] fix lookup lock leak when request is aborted before alloc | 🔄 Open | — |
| [vllm#44097](https://github.com/vllm-project/vllm/pull/44097) | [LMCache] fix missing cache_salt in free_lookup_locks call | 🔄 Open | — |
| [vllm#42872](https://github.com/vllm-project/vllm/pull/42872) | [Bugfix][Model Runner v2] Fix MRV2 KV cache kernel block sizing. | ❌ Closed | Closed: implemented by core maintainer |
| [sglang#24434](https://github.com/sgl-project/sglang/pull/24434) | [NemotronH] Fix expert scale weight loading | ☑️ Merged | — |

### Docs

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42160](https://github.com/vllm-project/vllm/pull/42160) | [Docs] Fix broken local links | ☑️ Merged | — |
| [vllm#42077](https://github.com/vllm-project/vllm/pull/42077) | [Docs] Update server entrypoint examples | ☑️ Merged | — |
| [vllm#42073](https://github.com/vllm-project/vllm/pull/42073) | [Docs] Fix RLHF example links | ☑️ Merged | — |
| [vllm#42066](https://github.com/vllm-project/vllm/pull/42066) | [Docs] Fix OpenAI batch model argument examples | ☑️ Merged | — |

### Other

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#45497](https://github.com/vllm-project/vllm/pull/45497) | [Core][KV Connector] Avoid hybrid KV load failure crash | 🔄 Open | — |
| [vllm#42214](https://github.com/vllm-project/vllm/pull/42214) | [Test][Bugfix] Fix mypy error: missing enable_prompt_embeds arg in test_tp_sp_nvfp4_generation | ❌ Closed | Closed: duplicate |
| [vllm#42086](https://github.com/vllm-project/vllm/pull/42086) | [Core][KV Connector] Bounded early prefetch for waiting requests | ❌ Closed | Closed: first version of PR #42321, abandoned due to significant design differences |
| [flashinfer#3273](https://github.com/flashinfer-ai/flashinfer/pull/3273) | docs: update contributing repository layout | 🔄 Open | — |

> Last synced: 2026-07-13 05:31 UTC
<!-- PR_TABLE_END -->

---

## Background

Brief context on the work: prefill-decode disaggregation requires efficient KV cache
transfer between nodes. The PRs above address scheduler-level prefetch scheduling and
hybrid KV cache manager (HMA) defaults to reduce latency and simplify configuration.

Related design notes in [`notes/`](./notes/).

