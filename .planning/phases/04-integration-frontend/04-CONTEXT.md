# Phase 4: Integration + Frontend - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

ADK orchestrator wires the full pipeline (Collection → Critic → Analysis → Synthesis) and exposes it via a FastAPI backend. A plain HTML/CSS/JS frontend lets users submit a query, watch SSE progress, view per-persona results in tabs, inspect charts, and download all artifacts. Deployment to Cloud Run is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Frontend Stack
- **D-01:** Replace Streamlit with **FastAPI + plain HTML/CSS/JS**. Full design control, no framework constraints. FastAPI is natively async — no asyncio bridging needed to call the ADK pipeline.
- **D-02:** Single-page app served by FastAPI's static file mount or a single `GET /` route returning the HTML file. No build step, no bundler.

### Orchestrator API Design
- **D-03:** FastAPI exposes `POST /run` → returns `SynthesisReport` as JSON. Always runs all 3 analyst agents regardless of persona selection — persona filtering is UI-only.
- **D-04:** Artifacts (scout_report.md, top_repos.csv, 4x PNG charts) served via separate `GET /download/{artifact}` endpoints after `/run` completes.
- **D-05:** `src/orchestrator.py` exposes an `async def run_pipeline(query: str) -> SynthesisReport` function. FastAPI route calls it directly (no asyncio.run wrapper needed).
- **D-06:** FastAPI also exposes a `GET /stream` (or `POST /run/stream`) endpoint using Server-Sent Events for pipeline progress updates. SSE events correspond to pipeline stages.

### Progress UX
- **D-07:** SSE streaming status — JS `EventSource` connects to the SSE endpoint. Each pipeline stage emits an event as it starts/completes: `Collection started → Critic filtering → Analysis running → Synthesis complete`. Displayed as a step-progress indicator (breadcrumb style: ► Collection ► Critic ► Analysis ► Synthesis).
- **D-08:** On pipeline failure: show an inline error message describing what failed (e.g., "GitHub API error") with a **Retry** button that re-submits the same query. Run button re-enabled.

### Persona Selection
- **D-09:** Persona multi-select controls which **tabs are visible** in the results section only. All 3 analysts always run. Default: all 3 selected. Unselected personas are hidden from results display but data is available in the JSON response.

### Visual Style
- **D-10:** Clean, light, modern aesthetic — white background, subtle card shadows (box-shadow), rounded corners. Font: Inter or DM Sans (loaded from Google Fonts).
- **D-11:** Persona-specific accent colors: VC = indigo/purple (#6366f1), Developer = emerald/teal (#10b981), Journalist = amber/orange (#f59e0b). Pill tabs and confidence badges tinted per persona.
- **D-12:** Single scrolling page layout (no routing, no SPA framework):
  - Header bar (name + Run button)
  - Query card (text input + persona checkboxes)
  - SSE progress strip (hidden until run starts)
  - Persona pill tabs + result card (hypothesis text, confidence dot-rating, collapsible evidence list)
  - Charts panel (2×2 grid of 4 PNG charts)
  - Download bar (buttons for scout_report.md, top_repos.csv, 4x PNG charts)

### Results Layout
- **D-13:** Each persona tab contains: rendered hypothesis text, confidence score as a visual dot-rating (e.g., ●●●●○ 82%), and a collapsible evidence/counter-evidence list.
- **D-14:** 4 charts displayed in a **2×2 responsive grid** below the tabs section. Charts are `<img>` tags pointing to `GET /download/chart_{n}.png` endpoints. Collapses to 1-column on narrow screens via CSS grid.
- **D-15:** Download bar sits **above** the charts panel. Buttons: "Download Report" (scout_report.md), "Download CSV" (top_repos.csv), "Download Charts" (zipped PNGs or individual buttons). Served via FastAPI file response endpoints.

### Claude's Discretion
- Exact CSS animation for the SSE progress breadcrumb (fade-in, pulse, or step fill)
- Whether charts are fetched as individual PNGs or one zipped bundle
- Mobile breakpoint pixel values
- Loading skeleton or placeholder while SSE events arrive before results render
- How to handle the case where a persona's analyst returns no data (empty state per tab)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Contracts
- `src/models/schemas.py` — `SynthesisReport` is the primary output consumed by the frontend. `AnalystHypothesis` fields (persona, confidence_score, evidence, counter_evidence, reasoning, hypothesis_text) map directly to tab content.

### Requirements
- `.planning/REQUIREMENTS.md` §Frontend — FE-01 through FE-06 (note: Streamlit replaced by FastAPI + HTML/CSS/JS; all functional requirements still apply)
- `.planning/REQUIREMENTS.md` §Orchestration — ORCH-01, ORCH-02, ORCH-03

### Architecture
- `.planning/codebase/ARCHITECTURE.md` — Full pipeline data flow; Stage 5 (Frontend) and orchestrator sections are directly relevant.
- `.planning/codebase/STACK.md` — Confirmed stack; FastAPI replaces Streamlit for the frontend layer.

### Prior Phase Contexts
- `.planning/phases/03-analysis-layer/03-CONTEXT.md` — Analyst persona voices (decisive VC, pragmatic Dev, skeptic Journalist), synthesis strategy, mock fixture approach. Phase 4 wires to real output.
- `.planning/phases/02-collection-layer/02-CONTEXT.md` — ADK ParallelAgent pattern, orchestrator interface expectations.

### Project Constraints
- `.planning/PROJECT.md` §Constraints — API rate limits; relevant for ensuring orchestrator doesn't over-call APIs during frontend testing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/models/schemas.py` — `SynthesisReport` and `AnalystHypothesis` are the JSON response shape for `POST /run`. Import and use for FastAPI response_model.
- `src/orchestrator.py` — Stub; implement `async def run_pipeline(query: str) -> SynthesisReport` here. FastAPI route calls this directly.
- `app/streamlit_app.py` — Stub; replace with FastAPI app entry point or rename to `app/main.py` (or keep as `app/app.py`). Decision for planner.
- `src/visualization/charts.py` — Chart generation already implemented in Phase 3. Phase 4 calls this and exposes chart PNGs via download endpoints.
- `src/agents/analysis/` — vc_analyst.py, developer_analyst.py, journalist_analyst.py are Phase 3 deliverables. Orchestrator wires them via ADK ParallelAgent.
- `src/agents/synthesis_agent.py` — Phase 3 deliverable. Orchestrator calls after analysis completes.
- `src/agents/critic_agent.py` — Phase 2 deliverable. Orchestrator calls after collection, before analysis.

### Established Patterns
- **Google ADK ParallelAgent** — Used in Phase 2 for collection. Phase 4 orchestrator uses same pattern for analysis layer (3 analyst agents concurrent). See Phase 2 CONTEXT D-02.
- **Pydantic v2** — All response models. FastAPI's `response_model=SynthesisReport` gives automatic JSON serialization.
- **Async-first** — All ADK agent functions are `async def`. FastAPI async routes call them natively.
- **uv** — `uv add fastapi uvicorn` for new dependencies.

### Integration Points
- `src/orchestrator.py` — The seam between FastAPI and the ADK pipeline. Phase 4 implements this file.
- `app/streamlit_app.py` → becomes FastAPI entry point — `uvicorn app.main:app --port 8080` (or equivalent).
- `src/visualization/charts.py` — Called by synthesis agent or orchestrator post-synthesis; charts saved to a temp dir and served by FastAPI.

</code_context>

<specifics>
## Specific Ideas

- Visual design reference: clean SaaS product feel (Notion/Linear aesthetic) — white, cards, subtle shadows, Inter font.
- Persona colors locked: VC=indigo (#6366f1), Developer=emerald (#10b981), Journalist=amber (#f59e0b).
- SSE progress should feel like a pipeline status board — breadcrumb-style, each stage lights up as it completes.
- Pill-style tabs (rounded pill shape, not underline tabs) for persona switching.
- Confidence score shown as dot rating (●●●●○ 82%) — visual, not just a number.
- Evidence list is collapsible (▼ toggle) so hypothesis text is readable at a glance.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 4 scope.

</deferred>

---

*Phase: 04-integration-frontend*
*Context gathered: 2026-04-10*
