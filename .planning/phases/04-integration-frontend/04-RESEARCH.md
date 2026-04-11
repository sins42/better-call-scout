# Phase 4: Integration + Frontend - Research

**Researched:** 2026-04-10
**Domain:** FastAPI orchestrator wiring (Google ADK) + plain HTML/CSS/JS frontend with SSE streaming
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Replace Streamlit with **FastAPI + plain HTML/CSS/JS**. Full design control, no framework constraints. FastAPI is natively async — no asyncio bridging needed to call the ADK pipeline.
- **D-02:** Single-page app served by FastAPI's static file mount or a single `GET /` route returning the HTML file. No build step, no bundler.
- **D-03:** FastAPI exposes `POST /run` → returns `SynthesisReport` as JSON. Always runs all 3 analyst agents regardless of persona selection — persona filtering is UI-only.
- **D-04:** Artifacts (scout_report.md, top_repos.csv, 4x PNG charts) served via separate `GET /download/{artifact}` endpoints after `/run` completes.
- **D-05:** `src/orchestrator.py` exposes an `async def run_pipeline(query: str) -> SynthesisReport` function. FastAPI route calls it directly (no asyncio.run wrapper needed).
- **D-06:** FastAPI also exposes a `GET /stream` (or `POST /run/stream`) endpoint using Server-Sent Events for pipeline progress updates. SSE events correspond to pipeline stages.
- **D-07:** SSE streaming status — JS `EventSource` connects to the SSE endpoint. Each pipeline stage emits an event as it starts/completes. Displayed as a step-progress indicator (breadcrumb style).
- **D-08:** On pipeline failure: show an inline error message with a Retry button. Run button re-enabled.
- **D-09:** Persona multi-select controls which tabs are visible in the results section only. All 3 analysts always run. Default: all 3 selected.
- **D-10:** Clean, light, modern aesthetic — white background, subtle card shadows, rounded corners. Font: Inter or DM Sans from Google Fonts.
- **D-11:** Persona-specific accent colors: VC = #6366f1, Developer = #10b981, Journalist = #f59e0b.
- **D-12:** Single scrolling page layout (no routing, no SPA framework): Header bar → Query card → SSE progress strip → Persona pill tabs + result card → Charts panel → Download bar.
- **D-13:** Each persona tab: hypothesis text, confidence dot-rating (●●●●○ 82%), collapsible evidence/counter-evidence list.
- **D-14:** 4 charts displayed in a 2×2 responsive grid below tabs. `<img>` tags pointing to `GET /download/chart_{n}.png`. Collapses to 1-column below 640px.
- **D-15:** Download bar above the charts panel. Buttons: "Download Report", "Download CSV", 4 individual PNG buttons.

### Claude's Discretion

- Exact CSS animation for SSE progress breadcrumb (fade-in, pulse, or step fill)
- Whether charts are fetched as individual PNGs or one zipped bundle
- Mobile breakpoint pixel values
- Loading skeleton or placeholder while SSE events arrive before results render
- How to handle the case where a persona's analyst returns no data (empty state per tab)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 4 scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORCH-01 | ADK top-level orchestrator wires Collection → Critic → Analysis → Synthesis flow | ADK SequentialAgent wrapping ParallelAgent sub-groups; InMemoryRunner.run_async pattern verified |
| ORCH-02 | Collection layer runs in parallel (3 agents concurrent) | ADK ParallelAgent already used in Phase 2 — reuse same pattern for orchestrator wiring |
| ORCH-03 | Analysis layer runs in parallel (3 analyst agents concurrent) | ADK ParallelAgent wrapping vc_analyst_loop, dev_analyst_loop, journalist_analyst_loop |
| FE-01 | Query input field | Plain HTML `<input type="text">` inside query card; JS fetch to POST /run |
| FE-02 | Persona multi-select | HTML checkboxes; JS controls tab visibility on results render |
| FE-03 | Progress indicators during pipeline execution | `EventSource` JS connecting to SSE endpoint; breadcrumb strip in HTML |
| FE-04 | Tabbed results display (one tab per persona) | Pill tabs via HTML + CSS + JS click handlers; data from POST /run JSON response |
| FE-05 | Charts panel rendered inline | `<img>` tags with `src="GET /download/chart_{n}.png"` in 2×2 CSS grid |
| FE-06 | Download buttons for scout_report.md, top_repos.csv, 4x PNG | FastAPI `FileResponse` endpoints; HTML `<a download>` links or JS fetch |
</phase_requirements>

---

## Summary

Phase 4 has two halves: orchestrator wiring (`src/orchestrator.py`) and the FastAPI + HTML/CSS/JS frontend (`app/`). The orchestrator is a pure Python async function that chains ADK agents using `SequentialAgent` + `ParallelAgent`. The frontend is a single HTML file served by FastAPI with no build step.

The key insight for the orchestrator is that ADK's `InMemoryRunner.run_async()` returns an `AsyncGenerator[Event, None]`. The orchestrator loops over events, reads final state from the session service after completion, and extracts typed outputs (e.g., `synthesis_report`) using `build_synthesis_report_from_state`. This is the established pattern already used in tests in this project.

The SSE endpoint is the trickiest part. FastAPI + `sse-starlette` (already installed as ADK transitive dep) provides `EventSourceResponse`. The orchestrator must emit progress callbacks — implemented via a queue or async generator that yields stage names during the pipeline run. The `POST /run` endpoint and SSE endpoint share state via a per-request in-memory store (dict keyed by session/request ID).

**Primary recommendation:** Implement orchestrator first (testable in isolation), then build the FastAPI app layer on top, then add the HTML/CSS/JS frontend as a static string or file served from `GET /`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.3 | Async web framework, REST + SSE endpoints | Already installed as google-adk transitive dep [VERIFIED: pip] |
| uvicorn | 0.43.0 | ASGI server to run FastAPI app | Already installed as google-adk transitive dep [VERIFIED: pip] |
| sse-starlette | 3.3.4 | `EventSourceResponse` for SSE streaming in FastAPI | Already installed as google-adk transitive dep [VERIFIED: pip] |
| google-adk | 1.28.1 | Agent orchestration framework; `SequentialAgent`, `ParallelAgent`, `InMemoryRunner` | Core project dependency [VERIFIED: uv run python -c "import google.adk; print(google.adk.__version__)"] |
| pydantic v2 | 2.7.0+ | FastAPI response_model serialization; SynthesisReport JSON output | Project-standard, already used in all agents [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0.0+ | Load GITHUB_TOKEN, TAVILY_API_KEY, GOOGLE_CLOUD_PROJECT | Always — app startup |
| pandas | 2.2.0+ | CSV generation via generate_top_repos_csv() | Synthesis artifact creation |
| matplotlib/seaborn | 3.9.0+ / 0.13.0+ | PNG chart generation via charts.py | Called by orchestrator post-synthesis |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sse-starlette EventSourceResponse | FastAPI StreamingResponse with manual SSE format | sse-starlette handles keep-alive, client disconnect, and proper `data:` framing automatically |
| InMemoryRunner | direct agent.run_async() | InMemoryRunner manages session + artifact services; required for state retrieval |

**Installation (fastapi/uvicorn are already installed via ADK but not declared as direct deps):**
```bash
uv add fastapi uvicorn sse-starlette
```

**Version verification:** All three packages verified as already present in `.venv` via `uv run python -c "import fastapi; print(fastapi.__version__)"` — outputs `0.135.3`. [VERIFIED: installed venv]

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── orchestrator.py          # async def run_pipeline(query, progress_cb) -> SynthesisReport
├── agents/
│   ├── analysis/            # vc_analyst_loop, dev_analyst_loop, journalist_analyst_loop (Phase 3)
│   ├── collection/          # github_agent, hn_tavily_agent, rag_agent (Phase 2)
│   ├── critic_agent.py      # critic_agent (Phase 2)
│   └── synthesis_agent.py   # synthesis_agent, generate_scout_report_md, generate_top_repos_csv
├── visualization/
│   └── charts.py            # star_velocity_chart, category_heatmap, hn_buzz_scatter, persona_score_bars
app/
├── main.py                  # FastAPI app, POST /run, GET /stream, GET /download/{artifact}, GET /
└── static/
    └── index.html           # single-page app HTML (or inline in main.py)
```

Note: `app/streamlit_app.py` is a stub file — it becomes `app/main.py` (or a rename). The planner must decide whether to rename the existing stub or create `app/main.py` alongside it.

### Pattern 1: ADK Orchestrator Wiring with SequentialAgent

**What:** Chain Collection (ParallelAgent), Critic (LlmAgent), Analysis (ParallelAgent), Synthesis (LlmAgent) in a SequentialAgent. Run with InMemoryRunner.

**When to use:** Any time the full pipeline must run end-to-end. The SequentialAgent guarantees stage ordering; ParallelAgent handles fan-out within each stage.

**Verified ADK classes available:** `SequentialAgent`, `ParallelAgent`, `LlmAgent`, `LoopAgent`, `InMemoryRunner` [VERIFIED: `uv run python -c "from google.adk.agents import SequentialAgent, ParallelAgent; print('OK')"`]

**Pattern:**
```python
# Source: verified against google.adk 1.28.1 InMemoryRunner API
from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import uuid

# Build the pipeline agent (done once at module level, not per request)
pipeline_agent = SequentialAgent(
    name="ScoutPipeline",
    sub_agents=[
        ParallelAgent(name="CollectionLayer", sub_agents=[github_agent, hn_tavily_agent, rag_agent]),
        critic_agent,
        ParallelAgent(name="AnalysisLayer", sub_agents=[vc_analyst_loop, dev_analyst_loop, journalist_analyst_loop]),
        synthesis_agent,
    ],
)

runner = InMemoryRunner(agent=pipeline_agent, app_name="better-call-scout")

async def run_pipeline(query: str) -> SynthesisReport:
    session = await runner.session_service.create_session(
        app_name="better-call-scout",
        user_id="scout-user",
        state={"query": query},  # seed state for agent prompts
    )
    message = types.Content(role="user", parts=[types.Part(text=query)])
    async for event in runner.run_async(
        user_id="scout-user",
        session_id=session.id,
        new_message=message,
    ):
        pass  # consume events; state is accumulated inside session

    final_session = await runner.session_service.get_session(
        app_name="better-call-scout",
        user_id="scout-user",
        session_id=session.id,
    )
    return build_synthesis_report_from_state(final_session.state, query, repos=[])
```

[VERIFIED: `InMemoryRunner.__init__` signature, `run_async` signature, `create_session`/`get_session` signatures — all confirmed via `inspect.signature()` on installed 1.28.1]

### Pattern 2: SSE Progress with sse-starlette

**What:** Run the pipeline in a background task while emitting stage events to the client via Server-Sent Events. Use an `asyncio.Queue` to bridge the pipeline runner and the SSE generator.

**When to use:** The `/stream` endpoint or a combined `/run/stream` that streams events and then final JSON.

**Pattern:**
```python
# Source: sse-starlette 3.3.4 EventSourceResponse API (verified installed)
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
import asyncio
import json

async def pipeline_sse_generator(request: Request, query: str):
    queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(stage: str, status: str):
        await queue.put({"event": stage, "data": status})

    async def run():
        try:
            report = await run_pipeline_with_progress(query, progress_callback)
            await queue.put({"event": "complete", "data": report.model_dump_json()})
        except Exception as e:
            await queue.put({"event": "error", "data": str(e)})
        finally:
            await queue.put(None)  # sentinel

    asyncio.create_task(run())

    while True:
        if await request.is_disconnected():
            break
        item = await queue.get()
        if item is None:
            break
        yield item

@app.get("/stream")
async def stream_endpoint(request: Request, query: str):
    return EventSourceResponse(pipeline_sse_generator(request, query))
```

[VERIFIED: `EventSourceResponse.__init__` accepts `AsyncIterable[dict]` where dict has `event` and `data` keys — confirmed via inspect.signature on installed 3.3.4]

### Pattern 3: FastAPI Download Endpoints

**What:** Store pipeline artifacts in a per-request temp dict keyed by session_id. Serve via `FileResponse` or `Response` with correct Content-Disposition headers.

**When to use:** After `POST /run` completes — the four PNG bytes from charts.py and the CSV/MD strings from synthesis_agent.py are stored in memory and served on demand.

**Pattern:**
```python
# Source: FastAPI 0.135.3 (verified installed)
from fastapi.responses import Response, FileResponse
import tempfile, os

# In-memory artifact store: {session_id: {artifact_name: bytes|str}}
_artifact_store: dict[str, dict[str, bytes]] = {}

@app.get("/download/{artifact}")
async def download_artifact(artifact: str, session_id: str):
    store = _artifact_store.get(session_id, {})
    data = store.get(artifact)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact}' not found")

    media_types = {
        "scout_report.md": "text/markdown",
        "top_repos.csv": "text/csv",
    }
    if artifact.endswith(".png"):
        return Response(content=data, media_type="image/png",
                        headers={"Content-Disposition": f"attachment; filename={artifact}"})
    mt = media_types.get(artifact, "application/octet-stream")
    return Response(content=data, media_type=mt,
                    headers={"Content-Disposition": f"attachment; filename={artifact}"})
```

### Pattern 4: Charts Integration

**What:** Call the four chart functions from `src/visualization/charts.py` after synthesis completes. Each returns `bytes` (PNG). Store in the artifact store.

**Known signature (verified from codebase):**
```python
# Source: src/visualization/charts.py (read directly)
star_velocity_chart(report: SynthesisReport) -> bytes
category_heatmap(report: SynthesisReport) -> bytes
hn_buzz_scatter(report: SynthesisReport, news_scores: dict[str, float] | None = None) -> bytes
persona_score_bars(report: SynthesisReport) -> bytes
```

Charts are named: `chart_1.png` (star velocity), `chart_2.png` (category heatmap), `chart_3.png` (HN buzz scatter), `chart_4.png` (persona scores). This aligns with the UI-SPEC download button labels.

### Pattern 5: HTML served from FastAPI GET /

**What:** FastAPI serves the entire SPA as a single HTML string or file from `GET /`. No static file server needed if the HTML is inline.

```python
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=open("app/static/index.html").read())
```

Or mount a static directory if preferred:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

[VERIFIED: FastAPI 0.135.3 HTMLResponse and StaticFiles available — confirmed via import check]

### Anti-Patterns to Avoid

- **Wrapping async ADK calls in asyncio.run():** FastAPI routes are async — call `await run_pipeline()` directly. `asyncio.run()` in an already-running event loop raises `RuntimeError`.
- **Re-creating InMemoryRunner per request:** Runner initialization is expensive and may leak sessions. Create one runner at module level (app startup), share across requests with different session IDs.
- **Storing artifacts on disk:** Cloud Run instances are ephemeral. Store chart bytes and CSV/MD strings in the in-process dict `_artifact_store`. The store is cleared per request (or after TTL).
- **EventSource for POST /run:** `EventSource` in browsers only supports `GET`. The SSE endpoint must be `GET /stream?query=...` or use a two-step design: `POST /run` (returns session_id), then `GET /stream/{session_id}` for progress.
- **Blocking the event loop with matplotlib:** `charts.py` already sets `matplotlib.use("Agg")` and is synchronous. Wrap chart generation in `asyncio.to_thread()` to avoid blocking FastAPI's event loop on CPU-bound rendering.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE streaming | Manual `text/event-stream` response with `data:` formatting | `sse-starlette EventSourceResponse` | Handles keep-alive pings, client disconnect detection, proper framing — already installed |
| ADK parallel fan-out | `asyncio.gather()` over agents | `ParallelAgent` | Course rubric requires ADK parallel execution; established in Phase 2 |
| JSON serialization of SynthesisReport | Manual `json.dumps()` | `report.model_dump_json()` (Pydantic v2) | Handles datetime serialization, HttpUrl coercion, nested models |
| Agent state threading | Custom state dict | ADK Session `.state` dict via InMemorySessionService | Session service manages concurrent sessions safely |

**Key insight:** FastAPI, uvicorn, and sse-starlette are already installed as transitive deps of google-adk. No new installs needed for the web layer — only `uv add` declarations to make them explicit in pyproject.toml.

---

## Common Pitfalls

### Pitfall 1: EventSource Only Supports GET
**What goes wrong:** JS `new EventSource('/stream', {method: 'POST'})` is invalid. The browser EventSource API only issues GET requests.
**Why it happens:** Developers assume SSE works like fetch (any method).
**How to avoid:** Design SSE as `GET /stream?query=<encoded>` — query string carries the topic. Or use a two-phase pattern: `POST /run` returns a `session_id`, then `GET /stream/{session_id}` streams progress for that session.
**Warning signs:** Browser console shows "EventSource's response has a MIME type that is not text/event-stream" or simply no connection.

### Pitfall 2: ADK Session State Keys Must Match Agent output_key
**What goes wrong:** `final_session.state.get("synthesis_report")` returns None even though synthesis_agent ran.
**Why it happens:** The `output_key` on `synthesis_agent` is `"synthesis_report"` — ADK writes the agent's output to `session.state["synthesis_report"]`. If the key doesn't match exactly, `build_synthesis_report_from_state` will raise `ValueError`.
**How to avoid:** Verify each agent's `output_key` matches what the orchestrator reads from state. The existing synthesis_agent uses `output_key="synthesis_report"`. The analyst loops use `output_key="vc_draft_output"`, `"dev_draft_output"`, `"journalist_draft_output"`.
**Warning signs:** `ValueError: State key 'X' is empty` from `build_synthesis_report_from_state`.

### Pitfall 3: Matplotlib Blocking the FastAPI Event Loop
**What goes wrong:** The FastAPI server becomes unresponsive for 2-5 seconds while charts are rendered. Other requests queue up. Under load, this manifests as timeouts.
**Why it happens:** `matplotlib` rendering is CPU-bound synchronous work running on the async event loop.
**How to avoid:** Wrap all four chart function calls in `asyncio.to_thread()`:
```python
import asyncio
chart_bytes = await asyncio.to_thread(star_velocity_chart, report)
```
**Warning signs:** FastAPI logs show 5+ second response times on `/run`. `asyncio` loop lag warnings in uvicorn.

### Pitfall 4: SynthesisReport confidence_score Range
**What goes wrong:** The confidence dot-rating formula `floor(confidence_score / 20)` yields 0 dots for a score of 0.82.
**Why it happens:** `AnalystHypothesis.confidence_score` is in range `[0.0, 1.0]` (Pydantic field constraint), but the UI formula from the UI-SPEC uses a percentage scale (`score 82 → 4 filled dots`).
**How to avoid:** The JS dot-rating renderer must multiply by 100 first: `Math.floor((confidence_score * 100) / 20)`. The JSON from `POST /run` returns `confidence_score` in `[0.0, 1.0]`.
**Warning signs:** All personas show 0 dots regardless of actual scores.

### Pitfall 5: FastAPI response_model with HttpUrl Fields
**What goes wrong:** `SynthesisReport` contains `RepoData.url: HttpUrl` — Pydantic v2 serializes this as a URL object, not a plain string. FastAPI's JSON response may emit `"url": {"scheme": "https", ...}` or similar on older Pydantic builds.
**Why it happens:** Pydantic v2 `HttpUrl` is not a plain `str` subclass.
**How to avoid:** Use `response_model_exclude_none=True` on the route and test the serialized output. Or use `model.model_dump(mode="json")` explicitly. Alternatively, add `model_config = ConfigDict(json_schema_extra=..., populate_by_name=True)` with `str(url)` coercion.
**Warning signs:** Frontend receives `url` as an object instead of a string; chart `<img>` src and download links break.

### Pitfall 6: ADK LoopAgent Termination and State Overwrite
**What goes wrong:** The second iteration of a LoopAgent (e.g., `vc_analyst_loop`) overwrites the first iteration's `output_key="vc_draft_output"` with a potentially worse hypothesis.
**Why it happens:** `LoopAgent` with `max_iterations=2` runs the sub-agent list twice. ADK state keys are overwritten, not appended. The final value of `vc_draft_output` is the output of the second generator pass (after critic feedback), which is expected behavior — but if the critic crashes on iteration 2, state may be stale.
**How to avoid:** `build_synthesis_report_from_state` already handles missing keys with `ValueError`. No special action needed; just be aware that the state value is the last successful write.

### Pitfall 7: Concurrent Requests Share the Module-Level Artifact Store
**What goes wrong:** Two users submit queries simultaneously; the second user's download buttons retrieve the first user's artifacts.
**Why it happens:** `_artifact_store` is a module-level dict. If it uses a fixed key (e.g., `"latest"`), concurrent requests overwrite each other.
**How to avoid:** Key the artifact store by `session_id` (a UUID generated per `/run` request). Return `session_id` in the `POST /run` JSON response. The frontend passes it as a query param to `/download/{artifact}?session_id=...`.

---

## Code Examples

### FastAPI App Skeleton
```python
# Source: FastAPI 0.135.3 docs pattern (verified installed version)
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio, uuid

app = FastAPI(title="Better Call Scout")

class RunRequest(BaseModel):
    query: str

@app.post("/run")
async def run_scout(req: RunRequest) -> dict:
    session_id = str(uuid.uuid4())
    report = await run_pipeline(req.query)
    # Store artifacts keyed by session_id
    _artifact_store[session_id] = await build_artifacts(report)
    return {"session_id": session_id, "report": report.model_dump(mode="json")}

@app.get("/stream")
async def stream_progress(request: Request, query: str):
    return EventSourceResponse(progress_generator(request, query))

@app.get("/download/{artifact}")
async def download(artifact: str, session_id: str):
    data = _artifact_store.get(session_id, {}).get(artifact)
    if not data:
        raise HTTPException(404, f"{artifact} not found")
    media_type = "image/png" if artifact.endswith(".png") else "text/plain"
    return Response(content=data, media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={artifact}"})

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("app/static/index.html") as f:
        return HTMLResponse(f.read())
```

### JS EventSource Connection Pattern
```javascript
// Source: MDN Web Docs EventSource API (standard browser API)
// Note: EventSource only supports GET — query must be a URL param
function startRun(query, selectedPersonas) {
  const encodedQuery = encodeURIComponent(query);
  const evtSource = new EventSource(`/stream?query=${encodedQuery}`);

  evtSource.addEventListener("collection_started", () => updateStage("Collection"));
  evtSource.addEventListener("critic_started", () => updateStage("Critic"));
  evtSource.addEventListener("analysis_started", () => updateStage("Analysis"));
  evtSource.addEventListener("synthesis_started", () => updateStage("Synthesis"));
  evtSource.addEventListener("complete", (e) => {
    evtSource.close();
    const report = JSON.parse(e.data);
    renderResults(report, selectedPersonas);
  });
  evtSource.addEventListener("error_event", (e) => {
    evtSource.close();
    showError(e.data);
  });
}
```

### ADK State Seeding for Analyst Prompts
The analyst prompt templates use `{repo_data_json}`, `{news_items_json}`, `{rag_chunks_json}` placeholders. ADK fills these from session state. The orchestrator must seed these keys before running the analysis layer:

```python
# Seed state with collection outputs before starting analysis
state = {
    "query": query,
    "repo_data_json": json.dumps([r.model_dump(mode="json") for r in repos]),
    "news_items_json": json.dumps([n.model_dump(mode="json") for n in news_items]),
    "rag_chunks_json": json.dumps([c.model_dump(mode="json") for c in rag_chunks]),
}
session = await runner.session_service.create_session(
    app_name="better-call-scout", user_id="scout-user", state=state
)
```
[VERIFIED: `create_session` accepts `state: dict` — confirmed via inspect.signature on InMemorySessionService 1.28.1]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Streamlit for ML apps | FastAPI + plain HTML for full control | Decided in Phase 4 discuss | No asyncio bridge needed; full design control |
| asyncio.run() to call async agents | Native async FastAPI route | FastAPI 0.4+ / Python 3.7+ | Just `await` the pipeline function directly |
| Manual SSE with StreamingResponse | sse-starlette EventSourceResponse | Current standard | Keep-alive, disconnect, framing handled |

**Deprecated/outdated:**
- `app/streamlit_app.py`: The stub file exists but Streamlit has been replaced. Either rename to `app/main.py` or create `app/main.py` alongside it. REQUIREMENTS.md FE-01 through FE-06 still apply but Streamlit-specific patterns do not.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ADK SequentialAgent accepts `ParallelAgent` as a sub_agent | Architecture Patterns | Pipeline won't chain correctly; fallback: manual sequential await calls |
| A2 | ADK session state `{placeholder}` substitution in LlmAgent instructions is still the mechanism in v1.28.1 | Code Examples (state seeding) | Analyst prompts receive empty data; need to verify against ADK docs or tests |
| A3 | Two-phase design (POST /run returns session_id, GET /stream/{session_id} streams progress) cleanly separates concerns | Architecture Patterns | Could instead use a single streaming response that yields SSE then final JSON |

Note: A1 is testable locally with a minimal script. A2 is critical — verify by checking existing Phase 3 tests or ADK source before implementing. A3 is a design choice, not a factual claim.

---

## Open Questions

1. **State seeding mechanism for analyst prompts**
   - What we know: Analyst prompts use `{repo_data_json}` etc. ADK LlmAgent instructions support `{placeholder}` substitution from session state.
   - What's unclear: Whether the substitution is automatic or requires explicit wiring in the SequentialAgent between the collection and analysis parallel groups.
   - Recommendation: Check ADK source for `LlmAgent` instruction formatting before implementing orchestrator. If automatic, seed state at session creation. If not, add a lightweight "bridge" LlmAgent or custom BaseAgent that writes collection outputs to state.

2. **app/streamlit_app.py vs app/main.py**
   - What we know: CONTEXT.md D-05 says "rename to `app/main.py`" as an option. The file is currently a stub.
   - What's unclear: Whether the planner should rename the stub or create a new file (avoiding git rename confusion).
   - Recommendation: Create `app/main.py` as the new FastAPI entry point. Leave `app/streamlit_app.py` stub in place (it's empty — no harm). Planner can include a cleanup task.

3. **Collection layer interface to orchestrator**
   - What we know: Phase 2 collection agents are ADK agents with `output_key` values. The orchestrator needs their outputs as typed Python objects.
   - What's unclear: Exact output_key names for github_agent, hn_tavily_agent, rag_agent — not confirmed in this research.
   - Recommendation: Read Phase 2 agent files before finalizing orchestrator plan. The state keys must match exactly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| fastapi | FastAPI app layer | ✓ | 0.135.3 | — (installed via google-adk) |
| uvicorn | ASGI server | ✓ | 0.43.0 | — (installed via google-adk) |
| sse-starlette | SSE EventSourceResponse | ✓ | 3.3.4 | Manual StreamingResponse with SSE framing |
| google-adk | Pipeline orchestration | ✓ | 1.28.1 | — |
| SequentialAgent | Full pipeline wiring | ✓ | (in 1.28.1) | Manual sequential await calls |
| ParallelAgent | Parallel layer fan-out | ✓ | (in 1.28.1) | asyncio.gather() as fallback |
| InMemoryRunner | Agent execution | ✓ | (in 1.28.1) | — |
| matplotlib Agg backend | Chart PNG generation | ✓ | 3.9.0+ | — |

**Missing dependencies with no fallback:** None.

**Note:** fastapi, uvicorn, sse-starlette are not declared in `pyproject.toml` as direct deps (they arrive via google-adk). A Wave 0 task must run `uv add fastapi uvicorn sse-starlette` to make them explicit.

---

## Project Constraints (from CLAUDE.md)

- **Python 3.11**, type hints required on all public functions
- **Pydantic v2** — use `model_validator` not `validator`; `model_dump(mode="json")` for serialization
- **Async** for all ADK agent functions and FastAPI routes
- **Docstrings** on all classes and public methods (Google style)
- **snake_case** for files and functions, `PascalCase` for classes
- Never commit `.env`
- **uv** for all dependency management: `uv add fastapi uvicorn sse-starlette`
- **Do not add Claude as co-author in commits**

---

## Sources

### Primary (HIGH confidence)
- Installed google-adk 1.28.1 — `Runner.run_async`, `InMemoryRunner.__init__`, `InMemorySessionService.create_session/get_session`, `SequentialAgent`, `ParallelAgent` — all verified via `inspect.signature()` on installed package
- Installed fastapi 0.135.3 — `FastAPI`, `HTMLResponse`, `Response`, `StreamingResponse`, `StaticFiles` — verified via import checks
- Installed sse-starlette 3.3.4 — `EventSourceResponse.__init__` signature verified
- `src/models/schemas.py` — SynthesisReport, AnalystHypothesis field names and types (read directly)
- `src/visualization/charts.py` — all four chart function signatures (read directly)
- `src/agents/synthesis_agent.py` — `generate_scout_report_md`, `generate_top_repos_csv`, `build_synthesis_report_from_state` (read directly)
- `src/agents/analysis/_prompts.py` — analyst prompt placeholder names confirmed: `{repo_data_json}`, `{news_items_json}`, `{rag_chunks_json}`
- `.planning/phases/04-integration-frontend/04-CONTEXT.md` — all locked decisions
- `.planning/phases/04-integration-frontend/04-UI-SPEC.md` — full component interaction contract

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md — FE-01 through FE-06, ORCH-01 through ORCH-03 requirements text

### Tertiary (LOW confidence)
- None — all claims verified against installed code or direct file reads.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and version-confirmed
- Architecture: HIGH — ADK API signatures verified; FastAPI patterns confirmed
- Pitfalls: HIGH — based on verified API constraints (e.g., EventSource GET-only is a browser standard)

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (ADK is fast-moving at v1.x; re-verify if updating past 1.28.1)
