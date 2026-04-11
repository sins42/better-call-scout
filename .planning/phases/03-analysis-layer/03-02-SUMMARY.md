---
phase: "03"
plan: "02"
subsystem: analysis-layer
tags: [adk, synthesis-agent, matplotlib, seaborn, visualization, pytest-fixtures]
dependency_graph:
  requires: [src/models/schemas.py, src/agents/analysis/_prompts.py, google-adk, matplotlib, seaborn, pandas]
  provides: [src/agents/synthesis_agent.py, src/visualization/charts.py]
  affects: [src/orchestrator.py, app/streamlit_app.py, tests/test_e2e.py]
tech_stack:
  added: [matplotlib Agg backend, seaborn heatmap/scatter/barplot, pandas DataFrame CSV export]
  patterns: [ADK LlmAgent with output_schema, Python fallback constructor for malformed LLM output, in-memory PNG export via BytesIO]
key_files:
  created:
    - .planning/phases/03-analysis-layer/03-02-SUMMARY.md
  modified:
    - src/agents/synthesis_agent.py
    - src/visualization/charts.py
    - tests/conftest.py
    - tests/test_analysis.py
decisions:
  - "D-08: _SYNTHESIS_INSTRUCTION explicitly instructs Gemini to write a new unified narrative, not concatenate analyst outputs"
  - "D-09: Overall confidence computed as equal-weighted mean in generate_scout_report_md(), not stored as a field on SynthesisReport"
  - "D-10: mock_synthesis_report fixture uses hardcoded Pydantic instances — no Phase 2 dependency"
  - "Fixed seaborn FutureWarning: passed hue=persona and legend=False to barplot to match seaborn v0.13+ API"
  - "Fixed test byte literal bug: plan's test used b'\\x89PNG' (escaped string) instead of b'\\x89PNG' (true bytes); corrected to b'\\x89PNG'"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-06"
  tasks_completed: 2
  files_created: 1
  files_modified: 4
---

# Phase 3 Plan 02: Synthesis Agent + Visualizations Summary

Synthesis Agent (LlmAgent with output_schema=SynthesisReport), Python fallback constructor, Markdown/CSV export functions, and four matplotlib/seaborn chart functions returning PNG bytes — all backed by 13 new offline tests, bringing the analysis layer test suite to 28 passing tests.

## Objective

Implement `src/agents/synthesis_agent.py` (filled from stub) and `src/visualization/charts.py` (filled from stub), extend `tests/conftest.py` with `mock_synthesis_report` fixture and `query` key, and append synthesis + visualization tests to `tests/test_analysis.py`.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Synthesis Agent — LlmAgent, fallback constructor, export functions | 1717afa | `src/agents/synthesis_agent.py` |
| 2 | Four visualization charts + conftest/test extensions | 45c349d | `src/visualization/charts.py`, `tests/conftest.py`, `tests/test_analysis.py` |

## Files Created / Modified

### Modified (stubs filled)
- `src/agents/synthesis_agent.py` — `synthesis_agent` (LlmAgent, output_schema=SynthesisReport), `build_synthesis_report_from_state()` fallback constructor, `generate_scout_report_md()` Markdown export, `generate_top_repos_csv()` CSV export via pandas
- `src/visualization/charts.py` — `star_velocity_chart` (line chart, 6 simulated weeks), `category_heatmap` (seaborn heatmap, topics x weeks), `hn_buzz_scatter` (scatter plot, HN proxy score vs stars), `persona_score_bars` (barplot with uncertainty threshold); all return PNG bytes via `_fig_to_png`
- `tests/conftest.py` — added `"query"` key to `mock_session_state`; added `mock_synthesis_report` fixture at end of file
- `tests/test_analysis.py` — appended 13 new tests: 8 synthesis agent tests (SYNTH-01/02/03, D-09, fallback constructor) + 5 visualization tests (VIZ-01 through VIZ-05)

## Verification Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.0.2
collected 28 items

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
tests/test_analysis.py::test_synthesis_agent_has_output_schema PASSED
tests/test_analysis.py::test_synthesis_agent_output_key PASSED
tests/test_analysis.py::test_synthesis_agent_has_no_tools PASSED
tests/test_analysis.py::test_generate_scout_report_md_structure PASSED
tests/test_analysis.py::test_generate_scout_report_md_overall_confidence PASSED
tests/test_analysis.py::test_generate_top_repos_csv_columns PASSED
tests/test_analysis.py::test_generate_top_repos_csv_empty_repos PASSED
tests/test_analysis.py::test_build_synthesis_report_from_state PASSED
tests/test_analysis.py::test_star_velocity_chart_returns_png PASSED
tests/test_analysis.py::test_category_heatmap_returns_png PASSED
tests/test_analysis.py::test_hn_buzz_scatter_returns_png PASSED
tests/test_analysis.py::test_persona_score_bars_returns_png PASSED
tests/test_analysis.py::test_all_charts_return_valid_png_magic_bytes PASSED

======================= 28 passed, 1 warning in 19.07s ========================
```

Additional verification:
- `synthesis_agent.name` prints `SynthesisAgent` — confirmed
- `from src.visualization.charts import star_velocity_chart, ...` prints `charts OK` — confirmed (Agg backend, no X server error)

## Key Design Decisions

| Decision | Implementation | Rationale |
|----------|---------------|-----------|
| D-08 (Synthesis writes new narrative) | `_SYNTHESIS_INSTRUCTION` explicitly says "write a new unified narrative that is NOT a concatenation" | Required by architecture spec |
| D-09 (Equal-weighted average confidence) | `generate_scout_report_md()` computes `sum(h.confidence_score) / len(report.hypotheses)` | Not a field on SynthesisReport — computed at render time |
| D-10 (Mock data, no Phase 2 dependency) | `mock_synthesis_report` fixture uses hardcoded Pydantic model instances | All chart tests are offline — no LLM or API calls |
| No tools on synthesis_agent | `synthesis_agent` has no `tools=` argument | ADK incompatibility: output_schema + tools conflict (Pitfall 1) |
| matplotlib Agg backend | `matplotlib.use("Agg")` as first matplotlib call at module level | Required for headless rendering (Cloud Run has no X server) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PNG magic byte test assertion**
- **Found during:** Task 2 test run
- **Issue:** Plan's test code used `b"\\x89PNG"[1:]` which evaluates to `b'x89PNG'` (literal escaped string sliced), not the actual PNG magic bytes `b'\x89PNG'`
- **Fix:** Replaced with `b'\x89PNG'` and `b'\x89PNG\r\n\x1a\n'` (true byte literals)
- **Files modified:** `tests/test_analysis.py`
- **Commit:** 45c349d (included in Task 2 commit)

**2. [Rule 2 - Deprecation Warning] Fixed seaborn barplot palette API**
- **Found during:** Task 2 test run (FutureWarning in pytest output)
- **Issue:** `sns.barplot(palette="Blues_d")` without `hue=` triggers FutureWarning in seaborn v0.13+ and will break in v0.14
- **Fix:** Added `hue="persona"` and `legend=False` to match current seaborn API
- **Files modified:** `src/visualization/charts.py`
- **Commit:** 45c349d (included in Task 2 commit)

## Known Stubs

None. Both `synthesis_agent.py` and `charts.py` are fully implemented. The `news_scores` parameter in `hn_buzz_scatter` defaults to `None` intentionally — Phase 4 will wire real HN scores from the collection layer. The synthetic proxy is correct for now per plan spec.

## Threat Flags

None. This plan creates no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All new code is agent configuration, pure Python export functions, and offline chart rendering.

## Self-Check: PASSED

- `src/agents/synthesis_agent.py` — EXISTS (filled)
- `src/visualization/charts.py` — EXISTS (filled)
- `tests/conftest.py` — EXISTS (mock_synthesis_report fixture added)
- `tests/test_analysis.py` — EXISTS (13 new tests appended)
- Commit 1717afa — EXISTS
- Commit 45c349d — EXISTS
- All 28 tests PASSED
