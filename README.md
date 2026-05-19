# vLLM Contributions — Ethan Feng (chfeng-cs)

Focused area: **KV Cache Transfer · Scheduler Optimization · HMA**

Core repos: [vllm-project/vllm](https://github.com/vllm-project/vllm)

---

## Contributions

<!-- PR_TABLE_START -->

### Core Feature

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42086](https://github.com/vllm-project/vllm/pull/42086) | [Core][KV Connector] Bounded early prefetch for waiting requests | ❌ Closed | ~102ms TTFT reduction (benchmark on A10) |
| [vllm#41847](https://github.com/vllm-project/vllm/pull/41847) | [KV Transfer] Enable HMA by default for connectors that support it | 🔄 Open | Reduces user config burden; fixes MultiConnector gap vs PR #42045 |

### Docs

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42073](https://github.com/vllm-project/vllm/pull/42073) | [Docs] Fix RLHF example links | ✅ Merged | — |
| [vllm#42066](https://github.com/vllm-project/vllm/pull/42066) | [Docs] Fix OpenAI batch model argument examples | ✅ Merged | — |

### Other

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42872](https://github.com/vllm-project/vllm/pull/42872) | [Bugfix][Model Runner v2] Fix MRV2 KV cache kernel block sizing. | ❌ Closed | — |
| [vllm#42321](https://github.com/vllm-project/vllm/pull/42321) | [KV Connector] Implement on_new_request for LMCacheMPConnector | 🔄 Open | — |
| [vllm#42214](https://github.com/vllm-project/vllm/pull/42214) | [Test][Bugfix] Fix mypy error: missing enable_prompt_embeds arg in test_tp_sp_nvfp4_generation | ❌ Closed | — |
| [vllm#42206](https://github.com/vllm-project/vllm/pull/42206) | [Metrics] Add group-aware KV cache capacity Prometheus gauges | 🔄 Open | — |
| [vllm#42160](https://github.com/vllm-project/vllm/pull/42160) | [Docs] Fix broken local links | ✅ Merged | — |
| [vllm#42077](https://github.com/vllm-project/vllm/pull/42077) | [Docs] Update server entrypoint examples | ✅ Merged | — |

> Last synced: 2026-05-19 17:01 UTC
<!-- PR_TABLE_END -->

---

## Background

Brief context on the work: prefill-decode disaggregation requires efficient KV cache
transfer between nodes. The PRs above address scheduler-level prefetch scheduling and
hybrid KV cache manager (HMA) defaults to reduce latency and simplify configuration.

Related design notes in [`notes/`](./notes/).
