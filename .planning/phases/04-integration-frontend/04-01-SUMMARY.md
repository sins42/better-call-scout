---
phase: 04-integration-frontend
plan: "01"
subsystem: orchestrator
tags: [adk, pipeline, orchestrator, integration, fastapi-deps]
dependency_graph:
  requires:
    - 03-02  # synthesis_agent, charts — phase 3 plan 2
    - 03-01  # analysis layer agents (vc/dev/journalist loops)
    - 02-02  # collection agents, critic_agent
  provides:
    - src/orchestrator.py  # run_pipeline, generate_artifacts, pipeline_agent
    - pyproject.toml with fastapi/uvicorn/sse-starlette deps
  affects:
    - app/  # FastAPI layer (plan 04-02) calls run_pipeline directly
tech_stack:
  added:
    - fastapi>=0.111.0
    - uvicorn[standard]>=0.30.0
    - sse-starlette>=2.1.0
  patterns:
    - ADK SequentialAgent wrapping pre-built ParallelAgent composites
    - asyncio.to_thread for matplotlib chart generation (non-blocking)
    - Per-request UUID user_id for ADK session isolation
    - Module-level InMemoryRunner singleton (not per-request)
key_files:
  created:
    - src/orchestrator.py
    - tests/test_orchestrator.py
  modified:
    - pyproject.toml
    - src/agents/analysis/journalist_analyst.py  # added journalist_analyst_loop alias
decisions:
  - "Use collection_pipeline composite instead of re-wrapping collection agents: ADK 1.28.1 enforces single-parent ownership, so github_agent/hn_tavily_agent/rag_agent and critic_agent cannot be re-parented into a new SequentialAgent. Used the pre-built collection_pipeline (SequentialAgent: collection_parallel + critic_agent) as first sub-agent."
  - "Pipeline has 3 sub-agents not 4: collection_pipeline (wraps parallel collection + critic), AnalysisLayer (parallel analyst loops), SynthesisAgent. Functionally equivalent to the plan's 4-agent spec."
  - "journalist_analyst_loop alias added to journalist_analyst.py: plan spec used journalist_analyst_loop but phase 3 exported journalist_loop. Alias preserves backward compatibility."
metrics:
  duration_minutes: 45
  completed_date: "2026-04-11"
  tasks_completed: 2
  files_changed: 3
---

# Phase 4 Plan 01: ADK Orchestrator Wiring Summary

**One-liner:** Full ADK pipeline wired via SequentialAgent(collection_pipeline, AnalysisLayer, SynthesisAgent) with asyncio.to_thread chart generation and per-request UUID session isolation.

## What Was Built

`src/orchestrator.py` exposes three exports:

- **`pipeline_agent`** — `SequentialAgent("ScoutPipeline")` with 3 sub-agents wired at module load
- **`run_pipeline(query, progress_cb)`** — async entry point; creates per-request ADK session, streams events, returns `SynthesisReport`; falls back to `build_synthesis_report_from_state` if Gemini JSON is malformed
- **`generate_artifacts(report)`** — async; runs all 4 matplotlib chart functions in `asyncio.to_thread()` concurrently, returns dict of `{name: bytes|str}` for all 6 downloadable artifacts

`pyproject.toml` now explicitly declares `fastapi`, `uvicorn[standard]`, and `sse-starlette` as direct dependencies (they were previously only transitive via google-adk).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ADK single-parent ownership prevents 4-sub-agent SequentialAgent**

- **Found during:** Task 2, GREEN phase
- **Issue:** ADK 1.28.1 raises `ValidationError` when creating `ParallelAgent("CollectionLayer", sub_agents=[github_agent, ...])` because importing any `src.agents.collection.*` submodule triggers `src/agents/collection/__init__.py`, which immediately creates `collection_pipeline` (a `SequentialAgent`) that claims `collection_parallel` and `critic_agent` as its children. Re-parenting claimed agents raises: `Agent github_agent already has a parent agent, current parent: collection_parallel`.
- **Fix:** Used the pre-built `collection_pipeline` (from `src.agents.collection`) as the first sub-agent, and `analysis_layer` (from `src.agents.analysis`) as the second. Pipeline structure is functionally identical (same execution order) with 3 top-level sub-agents instead of 4.
- **Files modified:** `src/orchestrator.py`, `tests/test_orchestrator.py`
- **Commits:** bde5bbd

**2. [Rule 1 - Bug] journalist_analyst_loop name mismatch**

- **Found during:** Task 2 import verification
- **Issue:** Plan spec referenced `journalist_analyst_loop` but phase 3 exported `journalist_loop` from `journalist_analyst.py`.
- **Fix:** Added `journalist_analyst_loop = journalist_loop` alias and updated `__all__` in `journalist_analyst.py`.
- **Files modified:** `src/agents/analysis/journalist_analyst.py`
- **Commits:** f27443b

**3. [Rule 3 - Blocking] Phase 3 implementations absent from worktree**

- **Found during:** Task 2 setup
- **Issue:** Worktree was `git reset --soft` to `e490ed4` (docs-only commit), leaving `src/agents/analysis/vc_analyst.py`, `developer_analyst.py`, `journalist_analyst.py`, `synthesis_agent.py`, `visualization/charts.py`, `_prompts.py`, and `tests/conftest.py` as stubs. These are required dependencies for the orchestrator.
- **Fix:** Restored all phase 3 implementations from git history (`3205ae4`, `2080be8`, `1717afa`, `45c349d`, `e483926`) using `git show <hash>:<path>`.
- **Files modified:** All phase 3 source files (restored, not changed)
- **Commits:** f27443b (included in Task 1 amended commit)

## Tests

- **13/13 orchestrator tests pass** in `tests/test_orchestrator.py`
- Tests cover: async signature, pipeline structure (3 sub-agents, correct types/names), generate_artifacts keys + PNG magic bytes + str types, progress callback ordering, import validation
- Uses `AsyncMock` to patch `_runner` — no real ADK/LLM calls required

## Threat Model Coverage

All mitigations from the plan's threat register were implemented:

| Threat ID | Mitigation | Location |
|-----------|-----------|----------|
| T-04-01-01 | Query stripped + capped at 500 chars | `run_pipeline` lines 79-81 |
| T-04-01-02 | Per-request UUID user_id, module-level runner singleton | `run_pipeline` line 84; module level |
| T-04-01-03 | InMemorySessionService — no disk persistence | Accepted; no secrets in pipeline data |
| T-04-01-04 | API keys read from env only; never in session state or artifacts | Verified: `generate_artifacts` returns report content only |

## Known Stubs

None. All functions are fully implemented.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced beyond what the plan's threat model already covers.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/orchestrator.py | FOUND |
| tests/test_orchestrator.py | FOUND |
| 04-01-SUMMARY.md | FOUND |
| commit f27443b (Task 1) | FOUND |
| commit bde5bbd (Task 2) | FOUND |
