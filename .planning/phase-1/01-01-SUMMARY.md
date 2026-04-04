---
phase: 01-data-contracts
plan: 01
subsystem: database
tags: [pydantic, schemas, data-models, type-safety]

requires: []
provides:
  - "Five Pydantic v2 models: RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport"
  - "Typed data contract between collection layer (Raghav) and analysis layer (Sindhuja)"
  - "17 unit tests covering valid instantiation and validation rejection for all five models"
affects:
  - "02-collection"
  - "03-analysis"
  - "04-critic-rag"
  - "05-synthesis-ui"

tech-stack:
  added: [pydantic>=2.7.0, pytest>=8.0.0, pytest-asyncio>=0.23.0]
  patterns:
    - "Pydantic v2 ConfigDict with json_schema_extra fixtures for all models"
    - "Field constraints (ge/le/min_length) for validation without custom validators"
    - "Optional fields with explicit defaults (None, [], {})"

key-files:
  created:
    - src/models/schemas.py
    - tests/unit/__init__.py
    - tests/unit/test_schemas.py
  modified: []

key-decisions:
  - "HttpUrl used for url fields on RepoData and NewsItem; RAGContextChunk.source is plain str to support file paths and ChromaDB doc IDs"
  - "SynthesisReport.generated_at defaults via lambda to datetime.now(timezone.utc) — each instance gets current UTC time"
  - "star_velocity bounded to [-1.0, 1.0] as a normalized rate, not raw delta"
  - "pytest installed via uv sync --extra dev (was missing from lockfile)"

patterns-established:
  - "Pydantic v2: use model_validator and field_validator (imported), Field constraints preferred over custom validators"
  - "Google-style docstrings on all model classes listing all attributes"
  - "from __future__ import annotations for forward reference support"

requirements-completed: [SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04, SCHEMA-05]

duration: 8min
completed: 2026-04-04
---

# Phase 1 Plan 01: Data Contracts Summary

**Five Pydantic v2 models (RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport) with Field constraints, ConfigDict fixtures, and 17 passing unit tests establishing the typed contract for both teammates**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-04T15:39:40Z
- **Completed:** 2026-04-04T15:47:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced stub schemas.py with five complete Pydantic v2 model classes with typed fields, ge/le/min_length constraints, and json_schema_extra fixtures
- Created 17 unit tests covering valid instantiation and validation rejection for all five models — 17/17 pass
- Established the shared data contract that unblocks Phase 2 (collection, Raghav) and Phase 3 (analysis, Sindhuja)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement five Pydantic v2 models** - `caba1dd` (feat)
2. **Task 2: Write unit tests for all five models** - `5d467bd` (test)

_Note: TDD tasks — implementation first then tests (both same plan since models were defined before tests in this plan)._

## Files Created/Modified

- `src/models/schemas.py` - Five Pydantic v2 models: RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport
- `tests/unit/__init__.py` - Empty init for unit test package
- `tests/unit/test_schemas.py` - 17 unit tests covering valid instantiation and validation rejection for all five models

## Decisions Made

- Used `HttpUrl` for `url` fields on `RepoData` and `NewsItem`; `RAGContextChunk.source` is plain `str` to support file paths and ChromaDB doc IDs
- `SynthesisReport.generated_at` defaults via `lambda: datetime.now(timezone.utc)` — ensures each instance captures the exact creation time
- `star_velocity` bounded `[-1.0, 1.0]` as a normalized growth rate
- `field_validator` and `model_validator` kept in imports (available for future use; Field constraints handle all current validation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed pytest dev dependency**
- **Found during:** Task 2 (unit tests)
- **Issue:** `pytest` was listed in `[project.optional-dependencies].dev` but not installed — `uv run pytest` failed with "No such file or directory"
- **Fix:** Ran `uv sync --extra dev` to install pytest 9.0.2 and pytest-asyncio 1.3.0
- **Files modified:** uv.lock (auto-updated)
- **Verification:** `uv run pytest tests/unit/test_schemas.py -v` reports 17 passed
- **Committed in:** Not committed separately — lockfile auto-managed by uv

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required to run tests; no scope creep. uv.lock updated automatically.

## Issues Encountered

None beyond the missing dev dependency noted above.

## User Setup Required

None - no external service configuration required.

## Human Checkpoint

**Both teammates should review `src/models/schemas.py` field names and types before Phase 2 (collection) and Phase 3 (analysis) work begins.** The field contract is now stable. Any changes to field names, types, or constraints after Phase 2/3 starts will require coordinated updates across both pipelines.

Key fields to agree on:
- `RepoData.star_velocity` — normalized float in `[-1.0, 1.0]` (not raw star delta)
- `NewsItem.score` — relevance float in `[0.0, 1.0]` (not raw HN points)
- `AnalystHypothesis.persona` — free string (e.g. "vc_analyst", "developer_analyst", "journalist")

## Verification Results

```
uv run python -c "from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport; print('All imports OK')"
All imports OK

uv run pytest tests/unit/test_schemas.py -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.0.2, pluggy-1.6.0
collected 17 items

tests/unit/test_schemas.py::test_repo_data_valid PASSED
tests/unit/test_schemas.py::test_repo_data_rejects_negative_stars PASSED
tests/unit/test_schemas.py::test_repo_data_star_velocity_bounds PASSED
tests/unit/test_schemas.py::test_repo_data_topics_defaults_empty PASSED
tests/unit/test_schemas.py::test_repo_data_language_optional PASSED
tests/unit/test_schemas.py::test_news_item_valid PASSED
tests/unit/test_schemas.py::test_news_item_score_bounds PASSED
tests/unit/test_schemas.py::test_news_item_published_at_coercion PASSED
tests/unit/test_schemas.py::test_rag_chunk_valid PASSED
tests/unit/test_schemas.py::test_rag_chunk_metadata_defaults PASSED
tests/unit/test_schemas.py::test_analyst_hypothesis_valid PASSED
tests/unit/test_schemas.py::test_analyst_hypothesis_confidence_too_high PASSED
tests/unit/test_schemas.py::test_analyst_hypothesis_empty_evidence_allowed PASSED
tests/unit/test_schemas.py::test_synthesis_report_valid PASSED
tests/unit/test_schemas.py::test_synthesis_report_empty_hypotheses_rejected PASSED
tests/unit/test_schemas.py::test_synthesis_report_generated_at_defaults PASSED
tests/unit/test_schemas.py::test_synthesis_report_top_repos_defaults_empty PASSED

============================== 17 passed in 0.07s
```

## Next Phase Readiness

- Phase 2 (Collection — Raghav): unblocked. Import `RepoData`, `NewsItem`, `RAGContextChunk` from `src.models.schemas`
- Phase 3 (Analysis — Sindhuja): unblocked. Import `AnalystHypothesis`, `SynthesisReport` from `src.models.schemas`
- Both teammates must review field names above before starting their phases

---
*Phase: 01-data-contracts*
*Completed: 2026-04-04*
