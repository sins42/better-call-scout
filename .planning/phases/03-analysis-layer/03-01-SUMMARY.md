---
phase: "03"
plan: "01"
subsystem: analysis-layer
tags: [adk, llm-agents, generator-critic, parallel-agents, pytest-fixtures]
dependency_graph:
  requires: [src/models/schemas.py, google-adk]
  provides: [src/agents/analysis/__init__.py, src/agents/analysis/_prompts.py, src/agents/analysis/vc_analyst.py, src/agents/analysis/developer_analyst.py, src/agents/analysis/journalist_analyst.py, tests/conftest.py, tests/test_analysis.py]
  affects: [src/orchestrator.py, tests/test_e2e.py]
tech_stack:
  added: [google-adk LlmAgent, google-adk LoopAgent, google-adk ParallelAgent]
  patterns: [generator-critic loop, parallel agent orchestration, ADK output_schema structured output, pytest fixtures via conftest.py]
key_files:
  created:
    - src/agents/analysis/_prompts.py
    - tests/conftest.py
  modified:
    - src/agents/analysis/vc_analyst.py
    - src/agents/analysis/developer_analyst.py
    - src/agents/analysis/journalist_analyst.py
    - src/agents/analysis/__init__.py
    - tests/test_analysis.py
decisions:
  - "ADK output_schema on generators, no output_schema on critics (free-text critique is correct for critic role)"
  - "max_iterations=2 on all LoopAgent instances per D-05 — prevents runaway latency"
  - "No tools on generator LlmAgents — output_schema + tools is incompatible in ADK (confirmed via ADK pitfall research)"
  - "ParallelAgent wraps all three LoopAgent instances — three analyst loops run concurrently"
  - "All 9 session state keys pre-seeded in mock_session_state to prevent ADK placeholder substitution errors"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-06"
  tasks_completed: 3
  files_created: 2
  files_modified: 5
---

# Phase 3 Plan 01: Three Analyst Agents + Generator-Critic Loop Summary

Three ADK LlmAgent generator-critic LoopAgents (VC, Developer, Journalist) running in parallel via ParallelAgent, each producing a validated AnalystHypothesis with max_iterations=2 refinement, backed by 15 offline structural tests and shared pytest fixtures.

## Objective

Build three LlmAgent generator-critic loops running in parallel, each producing a valid `AnalystHypothesis`, backed by mock fixtures in `conftest.py`.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | System prompt constants + mock fixtures | e483926 | `src/agents/analysis/_prompts.py`, `tests/conftest.py` |
| 2 | VC Analyst — Generator, Critic, LoopAgent | 3205ae4 | `src/agents/analysis/vc_analyst.py` |
| 3 | Developer Analyst, Journalist Analyst, ParallelAgent, tests | 2080be8 | `developer_analyst.py`, `journalist_analyst.py`, `__init__.py`, `test_analysis.py` |

## Files Created / Modified

### Created
- `src/agents/analysis/_prompts.py` — Six prompt constants (3 generator, 3 critic) + `GEMINI_MODEL` constant. All generator prompts include all required `{placeholder}` keys for ADK session state substitution.
- `tests/conftest.py` — Eight shared pytest fixtures: `mock_repos`, `mock_news`, `mock_rag_chunks`, `mock_session_state`, `mock_vc_hypothesis`, `mock_dev_hypothesis`, `mock_journalist_hypothesis`. All constructed via Pydantic model constructors.

### Modified (stubs filled)
- `src/agents/analysis/vc_analyst.py` — `vc_generator` (LlmAgent, output_schema=AnalystHypothesis), `vc_critic` (LlmAgent, free-text), `vc_analyst_loop` (LoopAgent, max_iterations=2)
- `src/agents/analysis/developer_analyst.py` — `dev_generator`, `dev_critic`, `dev_analyst_loop`
- `src/agents/analysis/journalist_analyst.py` — `journalist_generator`, `journalist_critic`, `journalist_loop`
- `src/agents/analysis/__init__.py` — `analysis_layer` (ParallelAgent wrapping all three loops)
- `tests/test_analysis.py` — 15 structural/offline tests (no LLM calls)

## Verification Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.0.2
collected 15 items

tests/test_analysis.py::test_analysis_layer_has_three_sub_agents PASSED
tests/test_analysis.py::test_vc_loop_max_iterations PASSED
tests/test_analysis.py::test_dev_loop_max_iterations PASSED
tests/test_analysis.py::test_journalist_loop_max_iterations PASSED
tests/test_analysis.py::test_generator_output_keys_are_unique PASSED
tests/test_analysis.py::test_critic_output_keys_are_unique PASSED
tests/test_analysis.py::test_generators_have_output_schema PASSED
tests/test_analysis.py::test_generators_have_no_tools PASSED
tests/test_analysis.py::test_mock_session_state_has_all_keys PASSED
tests/test_analysis.py::test_mock_repos_are_valid PASSED
tests/test_analysis.py::test_mock_session_state_repo_json_is_parseable PASSED
tests/test_analysis.py::test_analyst_hypothesis_persona_values PASSED
tests/test_analysis.py::test_vc_prompt_covers_required_domains PASSED
tests/test_analysis.py::test_dev_prompt_covers_required_domains PASSED
tests/test_analysis.py::test_journalist_prompt_covers_required_domains PASSED

============================= 15 passed in 10.47s =============================
```

Additional verification checks (all pass):
- `analysis_layer.name` prints `AnalysisLayer`
- `'{repo_data_json}' in VC_GENERATOR_PROMPT` — True
- `vc_analyst_loop.max_iterations` prints `2`

## Key Design Decisions

| Decision | Implementation | Rationale |
|----------|---------------|-----------|
| D-01 (VC decisive & contrarian) | `VC_GENERATOR_PROMPT` — no hedging, clear verdicts | Required by persona spec |
| D-02 (Dev pragmatic engineer) | `DEV_GENERATOR_PROMPT` — focuses on ecosystem, not just stars | Required by persona spec |
| D-03 (Journalist tech media skeptic) | `JOURNALIST_GENERATOR_PROMPT` — HN sentiment, real story vs hype | Required by persona spec |
| D-04 (Critics are separate adversarial agents) | `vc_critic`, `dev_critic`, `journalist_critic` as separate LlmAgent instances | Required by architecture |
| D-05 (Always 2 iterations) | `max_iterations=2` on all three LoopAgent instances | Prevents runaway latency |
| D-06 (Independent loops per analyst) | Three separate LoopAgent instances | Required by architecture |
| D-07 (Full data pool to all analysts) | `{repo_data_json}`, `{news_items_json}`, `{rag_chunks_json}` in all three generator prompts | Required by spec |
| D-10 (Mock data fixtures) | `tests/conftest.py` with hardcoded Pydantic model instances | Required by plan |
| No tools on generators | Confirmed via ADK model field inspection | ADK incompatibility: output_schema + tools |

## Deviations from Plan

None — plan executed exactly as written.

The worktree venv required manual pytest installation (`python -m ensurepip` + `pip install pytest pytest-asyncio`) because `uv run` resolved to system Python 3.10 which lacked the project's dependencies. The worktree's own `.venv` (Python 3.12.2) had all project dependencies installed but lacked pytest. This is a worktree setup detail, not a code deviation.

## Known Stubs

None. All agent modules are fully implemented. The `tests/test_analysis.py` tests are structural/offline — live LLM integration tests are out of scope for this plan (covered in plan 03-02 or test_e2e.py).

## Threat Flags

None. This plan creates no new network endpoints, auth paths, file access patterns, or schema changes. All new code is agent configuration and test fixtures.

## Self-Check: PASSED

- `src/agents/analysis/_prompts.py` — EXISTS
- `tests/conftest.py` — EXISTS
- `src/agents/analysis/vc_analyst.py` — EXISTS (filled)
- `src/agents/analysis/developer_analyst.py` — EXISTS (filled)
- `src/agents/analysis/journalist_analyst.py` — EXISTS (filled)
- `src/agents/analysis/__init__.py` — EXISTS (filled)
- `tests/test_analysis.py` — EXISTS (filled)
- Commit e483926 — EXISTS
- Commit 3205ae4 — EXISTS
- Commit 2080be8 — EXISTS
- All 15 tests PASSED
