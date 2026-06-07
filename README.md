# vLLM Contributions — Ethan Feng (chfeng-cs)

Focused area: **KV Cache Transfer · Scheduler Optimization · HMA**

Core repos: [vllm-project/vllm](https://github.com/vllm-project/vllm)

---

## Contributions

<!-- PR_TABLE_START -->

<details>
<summary>Issue</summary>

| Issue | Title | Status | Impact |
|-------|-------|--------|--------|
| [vllm#42846](https://github.com/vllm-project/vllm/issues/42846) | [Bug][CI] NIXL + FlashInfer fails with Qwen3 MRV2 and --block-size 128 | ☑️ Closed | — |
</details>

### Core Feature

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42321](https://github.com/vllm-project/vllm/pull/42321) | [KV Connector] Eager KV prefetch at request enqueue time in `LMCacheMPConnector` | 🔄 Open | ~25% TTFT reduction (benchmarked under high load with disk KV prefetch, L20) |
| [vllm#41847](https://github.com/vllm-project/vllm/pull/41847) | [KV Transfer] Enable HMA by default for connectors that support it | ✅ Merged | Reduces user config burden; fixes MultiConnector gap vs PR #42045 |

### Bug Fix

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#44101](https://github.com/vllm-project/vllm/pull/44101) | [LMCache] fix lookup lock leak when request is aborted before alloc | 🔄 Open | — |
| [vllm#44097](https://github.com/vllm-project/vllm/pull/44097) | [LMCache] fix missing cache_salt in free_lookup_locks call | 🔄 Open | — |
| [vllm#42872](https://github.com/vllm-project/vllm/pull/42872) | [Bugfix][Model Runner v2] Fix MRV2 KV cache kernel block sizing. | ❌ Closed | Closed: implemented by core maintainer |

### Docs

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#42160](https://github.com/vllm-project/vllm/pull/42160) | [Docs] Fix broken local links | ✅ Merged | — |
| [vllm#42077](https://github.com/vllm-project/vllm/pull/42077) | [Docs] Update server entrypoint examples | ✅ Merged | — |
| [vllm#42073](https://github.com/vllm-project/vllm/pull/42073) | [Docs] Fix RLHF example links | ✅ Merged | — |
| [vllm#42066](https://github.com/vllm-project/vllm/pull/42066) | [Docs] Fix OpenAI batch model argument examples | ✅ Merged | — |

### Other

| PR | Title | Status | Impact |
|----|-------|--------|--------|
| [vllm#44100](https://github.com/vllm-project/vllm/issues/44100) | [Bug]: [LMCache] `_cleanup_request_tracker` leaks lookup state and server read locks when request is aborted before allocation | 🔄 Open | — |
| [vllm#44096](https://github.com/vllm-project/vllm/issues/44096) | [Bug]:  [LMCache] `update_state_after_alloc` passes wrong `cache_salt` to `free_lookup_locks`, leaking server read locks in multi-tenant deployments | 🔄 Open | — |
| [vllm#42214](https://github.com/vllm-project/vllm/pull/42214) | [Test][Bugfix] Fix mypy error: missing enable_prompt_embeds arg in test_tp_sp_nvfp4_generation | ❌ Closed | Closed: duplicate |
| [vllm#42086](https://github.com/vllm-project/vllm/pull/42086) | [Core][KV Connector] Bounded early prefetch for waiting requests | ❌ Closed | Closed: first version of PR #42321, abandoned due to significant design differences |

> Last synced: 2026-06-07 10:57 UTC
<!-- PR_TABLE_END -->

---

## Background

Brief context on the work: prefill-decode disaggregation requires efficient KV cache
transfer between nodes. The PRs above address scheduler-level prefetch scheduling and
hybrid KV cache manager (HMA) defaults to reduce latency and simplify configuration.

Related design notes in [`notes/`](./notes/).
