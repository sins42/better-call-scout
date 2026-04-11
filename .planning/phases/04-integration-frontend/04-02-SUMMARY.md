---
phase: 04-integration-frontend
plan: "02"
subsystem: frontend
tags: [fastapi, sse, html, css, js, frontend, spa, download]
dependency_graph:
  requires:
    - 04-01  # src/orchestrator.py (run_pipeline, generate_artifacts)
    - 03-02  # synthesis_agent, charts
  provides:
    - app/main.py  # FastAPI app: POST /run, GET /stream, GET /download/{artifact}, GET /
    - app/static/index.html  # Complete single-page HTML/CSS/JS frontend
  affects:
    - app/  # All frontend entry points
tech_stack:
  added:
    - FastAPI app instance (fastapi>=0.111.0)
    - sse-starlette EventSourceResponse
    - StaticFiles mount for app/static/
  patterns:
    - asyncio.Queue SSE bridge (progress_cb -> EventSource events)
    - UUID session_id keyed _artifact_store (prevents concurrent contamination)
    - asyncio.wait_for timeout=120s (T-04-02-04)
    - model_dump(mode="json") for HttpUrl coercion
    - Allowlist validation on /download/{artifact} (T-04-02-02)
    - Self-contained SPA: all CSS+JS inline, no bundler, no framework
key_files:
  created:
    - app/main.py
    - app/static/index.html
    - app/__init__.py
  modified: []
decisions:
  - "SSE via GET /stream?query= (not POST): EventSource browser standard only supports GET"
  - "Two-phase session model: POST /run returns session_id; SSE emits session_id event after complete; both key _artifact_store"
  - "Complete confidence_score dot-rating uses Math.floor((score * 100) / 20) per RESEARCH.md Pitfall 4"
  - "Worktree reset-soft to 85a292c caused planning/test file deletions; restored in chore commit 2a32d50"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_changed: 3
---

# Phase 4 Plan 02: FastAPI App + Single-Page Frontend Summary

**One-liner:** FastAPI app with SSE progress streaming and self-contained HTML/CSS/JS SPA implementing all FE-01 through FE-06 requirements.

## What Was Built

### app/main.py (240 lines)

Four endpoints:
- **POST /run** — validates query (strip + 500-char cap), calls `run_pipeline(query)` with 120s timeout, stores all 6 artifacts in `_artifact_store` keyed by UUID session_id, returns `{session_id, report}` with `model_dump(mode="json")` for HttpUrl coercion
- **GET /stream** — EventSourceResponse SSE endpoint; uses asyncio.Queue bridge between `progress_cb` and generator; emits stage events (`collection_started`, etc.) plus `complete` (SynthesisReport JSON) and `session_id` events; 120s timeout
- **GET /download/{artifact}** — allowlist validation against 6 known artifact names (path traversal prevention T-04-02-02); returns bytes/str with correct MIME headers
- **GET /** — serves `app/static/index.html` from disk via HTMLResponse

`_artifact_store: dict[str, dict[str, bytes | str]]` — in-memory, keyed by UUID4 session_id.

### app/static/index.html (850 lines)

Complete SPA with all CSS+JS inline:
- Fixed 56px header with "Better Call Scout" title and "Run Scout" button (disabled + "Running…" during pipeline)
- Query card with text input + 3 persona checkboxes (VC/Developer/Journalist, all checked by default, min-height 44px touch targets)
- SSE progress strip: Collection › Critic › Analysis › Synthesis with pulse animation (active) and ✓ prefix + #6366f1 color (complete)
- Shimmer skeleton cards during pipeline run
- Persona pill tabs with accent colors (#6366f1 VC, #10b981 Developer, #f59e0b Journalist); active tab style uses `color + '26'` for 15% opacity background
- Result card: hypothesis text, confidence dot-rating (●●●●○ N%), collapsible evidence/counter-evidence list
- Download bar: 6 buttons (`window.open('/download/{artifact}?session_id=...')`)
- 2×2 charts grid (img src wired after session_id event); responsive @media 640px → 1 column
- Error state (#fef2f2/#fca5a5) with inline "Retry Query" button
- Empty state on initial load
- aria-selected (pill tabs), aria-expanded (evidence toggle), aria-live (progress strip)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree reset-soft dropped planning/test files**
- **Found during:** Task 1 commit
- **Issue:** `git reset --soft 85a292c` moved HEAD to the correct commit but the working tree was at `02d5e47` (pre-phase-04 state). Staging `git add app/main.py app/__init__.py` then committing captured the full diff, which included deletions of planning artifacts and test files that were added between `02d5e47` and `85a292c`.
- **Fix:** Restored all deleted files from `85a292c` using `git checkout 85a292c -- .planning/ tests/conftest.py tests/test_orchestrator.py .claude/settings.local.json` and committed as `chore(04-02)`.
- **Files modified:** All planning artifacts and test files (restored, not changed)
- **Commit:** 2a32d50

**2. [Rule 3 - Blocking] Worktree venv missing annotated_doc**
- **Found during:** Task 1 verification
- **Issue:** The worktree's `.venv` was missing `annotated_doc` package required by fastapi>=0.111.0. `uv run` failed with file-lock errors from a parallel agent installing packages. Used main repo `.venv` for import verification instead.
- **Fix:** Used `/c/Users/sindh/.../better-call-scout/.venv/Scripts/python.exe` for import verification; `from app.main import app` prints "FastAPI app import OK".
- **Impact:** No code change needed; venv state is resolved by the orchestrator after wave completion.

**3. [Rule 1 - Bug] Server emits 'complete' event, not 'synthesis_complete'**
- **Found during:** Task 2 JS implementation review
- **Issue:** The orchestrator's `run_pipeline` emits progress via the callback as `("synthesis", "complete")` → event name `synthesis_complete`. However, the SSE generator in `app/main.py` emits `{"event": "complete", ...}` for the final report (separate from the progress callback). The HTML must handle both.
- **Fix:** Registered both `synthesis_complete` and `complete` EventSource listeners in the JS so either event name triggers result rendering. No server-side change needed.

## Tests

No new test file created for this plan (FastAPI endpoints are verified by the human checkpoint). The existing `tests/test_orchestrator.py` (13 tests) covers the orchestrator called by these endpoints.

## Threat Model Coverage

| Threat ID | Mitigation | Location |
|-----------|-----------|----------|
| T-04-02-01 | query.strip() + len <= 500 check | run_scout(), stream_progress() |
| T-04-02-02 | Allowlist: artifact in {allowed set} | download_artifact() |
| T-04-02-03 | session_id is UUID4 (122 bits entropy) | run_scout() |
| T-04-02-04 | asyncio.wait_for(timeout=120.0) | run_scout(), stream_progress().run() |
| T-04-02-05 | Accepted (course scope) | — |
| T-04-02-06 | Same-origin: GET / serves HTML from FastAPI | — |

## Known Stubs

None. All endpoints are fully implemented and the frontend wires all described functionality.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond the plan's threat model.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/main.py (240 lines) | FOUND |
| app/static/index.html (850 lines) | FOUND |
| app/__init__.py | FOUND |
| commit 6186dd4 (Task 1 - FastAPI) | FOUND |
| commit 2a32d50 (chore - restore files) | FOUND |
| commit 827b50f (Task 2 - HTML SPA) | FOUND |
| EventSource in index.html | FOUND (3 occurrences) |
| All 3 persona accent colors | FOUND |
| confidence_score + Math.floor | FOUND |
| aria-selected, aria-expanded | FOUND |
| pulse, shimmer animations | FOUND |
| /download/ references | FOUND (9 occurrences) |
| Retry Query button | FOUND |
| grid-template-columns | FOUND |
| 640px breakpoint | FOUND |
