# Architecture

**Analysis Date:** 2026-04-03

## Pattern Overview

**Overall:** Multi-agent pipeline with parallel collection and parallel analysis, mediated by a critic agent and unified by a synthesis agent.

**Key Characteristics:**
- Five distinct pipeline stages: Collection → Critic → Analysis → Synthesis → Frontend
- Two parallel fan-out/fan-in stages managed by Google ADK: Collection Layer (3 agents) and Analysis Layer (3 agents)
- A shared Pydantic data contract (`src/models/schemas.py`) serves as the interface boundary between Collection and Analysis
- A generator-critic refinement loop runs inside the Analysis stage (max 2 iterations per analyst)
- The entire pipeline is invoked from `app/streamlit_app.py` via `src/orchestrator.py`

---

## Pipeline Stages

### Stage 1 — Collection Layer (parallel)

- Purpose: Gather raw data from three independent external sources concurrently
- Location: `src/agents/collection/`
- Contains: Three ADK agents, each with its own data source and retrieval strategy
- Agents:
  - `github_agent.py` — GitHub REST API; searches repos by topic/language/stars, fetches star history, commit activity, contributor stats, issue velocity
  - `hn_tavily_agent.py` — HackerNews Firebase API for top/best stories; Tavily search for founder bios, funding news, job postings
  - `rag_agent.py` — ChromaDB vector retrieval; queries pre-embedded HN stories, RSS feeds, and domain context corpus
- ADK execution: All three run concurrently; results are merged into the shared Pydantic data pool
- Depends on: `src/rag/retrieval.py` (for `rag_agent.py`), GitHub REST API, HN Firebase API, Tavily API
- Feeds: Stage 2 (Critic Agent)

### Stage 2 — Critic Agent (filter gate)

- Purpose: Filter the merged raw data pool; remove forks, boilerplate, one-day spike repos, and spam before passing cleaned data to analysts
- Location: `src/agents/critic_agent.py`
- Also participates in the generator-critic refinement loop in Stage 3
- Depends on: Shared Pydantic data pool (output of Stage 1)
- Feeds: Stage 3 (Analysis Layer)

### Stage 3 — Analysis Layer (parallel + iterative refinement)

- Purpose: Produce three structured hypothesis JSON outputs from three independent analyst perspectives; each hypothesis is refined via a critic loop
- Location: `src/agents/analysis/`
- Agents:
  - `vc_analyst.py` — star velocity ranking, market size signals from RAG, funding mention extraction, competitive landscape scoring
  - `developer_analyst.py` — ecosystem maturity scoring, adoption phase classification, job posting signal, historical benchmarking via RAG
  - `journalist_analyst.py` — narrative hook scoring, HN sentiment/buzz, media coverage density, incumbent comparison via RAG
- All three run concurrently via ADK
- Each analyst follows: **Evidence → Draft → Challenge (Critic) → Refine → Commit** (max 2 iterations)
- Output: Three structured hypothesis JSON objects with confidence score, supporting evidence, counter-evidence, and reasoning
- Depends on: Cleaned data pool from Stage 2; `src/rag/retrieval.py` for contextual lookups
- Feeds: Stage 4 (Synthesis Agent)

### Stage 4 — Synthesis Agent

- Purpose: Merge three structured analyst hypotheses into a single unified report; produce downloadable artifacts
- Location: `src/agents/synthesis_agent.py`
- Artifacts produced:
  - `scout_report.md` — narrative unified report
  - `top_repos.csv` — ranked repository list
  - 4x PNG charts (via `src/visualization/charts.py`)
- Depends on: Three hypothesis JSON objects from Stage 3
- Feeds: Stage 5 (Streamlit Frontend)

### Stage 5 — Streamlit Frontend

- Purpose: Accept user query, display progress, render tabbed results and charts, expose download buttons
- Location: `app/streamlit_app.py`
- Features: Query input, persona multi-select, progress indicators, tabbed results (VC / Developer / Journalist), charts panel, download buttons for all artifacts
- Depends on: `src/orchestrator.py` to invoke the full pipeline; `src/visualization/charts.py` for rendered chart images

---

## Data Flow

### Full Pipeline Flow

1. User submits a query in `app/streamlit_app.py`
2. `app/streamlit_app.py` calls `src/orchestrator.py`
3. Orchestrator fans out to three collection agents in `src/agents/collection/` (parallel via ADK)
4. Collection results are merged into a shared Pydantic data pool (`src/models/schemas.py` types)
5. `src/agents/critic_agent.py` filters the pool, removing low-quality repos
6. Orchestrator fans out to three analyst agents in `src/agents/analysis/` (parallel via ADK)
7. Each analyst queries `src/rag/retrieval.py` for additional context as needed
8. Each analyst enters a generator-critic loop with `src/agents/critic_agent.py` (max 2 iterations)
9. Three structured hypothesis JSON objects are passed to `src/agents/synthesis_agent.py`
10. Synthesis agent merges hypotheses, calls `src/visualization/charts.py` to render 4 charts
11. Artifacts (`scout_report.md`, `top_repos.csv`, 4x PNG) are returned to the Streamlit frontend
12. Streamlit renders tabs, charts, and download buttons

### RAG Sub-flow (parallel to live collection)

1. `src/rag/ingestion.py` fetches HN stories and RSS feeds, chunks them, embeds with `sentence-transformers/all-MiniLM-L6-v2`, stores in ChromaDB (embedded mode, persisted to disk)
2. `src/rag/retrieval.py` exposes a query interface over ChromaDB
3. `src/agents/collection/rag_agent.py` calls `src/rag/retrieval.py` during the collection stage
4. `src/agents/analysis/vc_analyst.py`, `developer_analyst.py`, and `journalist_analyst.py` also call `src/rag/retrieval.py` directly during analysis

### Shared Data Contract

- All inter-layer data passes through Pydantic models defined in `src/models/schemas.py`
- This file is the agreed contract between Raghav (collection) and Sindhuja (analysis); both sides must stay in sync with it

---

## ADK Orchestration

- **Framework:** Google ADK (`google-adk>=0.1.0`)
- **LLM:** Gemini 2.0 Flash via Vertex AI (`google-cloud-aiplatform>=1.60.0`)
- **Top-level agent:** `src/orchestrator.py` — wires the full Collection → Critic → Analysis → Synthesis flow
- **Parallel execution:**
  - Collection layer: `github_agent`, `hn_tavily_agent`, `rag_agent` run concurrently
  - Analysis layer: `vc_analyst`, `developer_analyst`, `journalist_analyst` run concurrently
- **Iterative refinement:** Each analyst in the analysis layer loops with `critic_agent` (max 2 iterations) before committing its hypothesis

---

## Data Visualizations

All four charts are rendered by `src/visualization/charts.py` using matplotlib/seaborn and displayed in `app/streamlit_app.py`. Each is downloadable as PNG.

| Chart | Description |
|---|---|
| Star Velocity Line Chart | Top 10 repos — stars/week over 4-8 weeks |
| Category Heatmap | Tech categories x weeks, color = star velocity |
| HN Buzz vs. GitHub Stars Scatter | X = stars, Y = HN score — identifies gems vs. hype traps |
| Persona Score Bar Chart | Side-by-side VC/Developer/Journalist scores per repo |

---

## Entry Points

**User-facing entry point:**
- `app/streamlit_app.py` — started by the container CMD; Streamlit listens on port 8080

**Pipeline entry point:**
- `src/orchestrator.py` — top-level ADK agent invoked by the Streamlit app; owns the full agent wiring

**RAG pre-population entry point:**
- `src/rag/ingestion.py` — run offline (or at container startup) to populate ChromaDB before queries arrive

**Container entry point:**
- `Dockerfile` CMD: `uv run streamlit run app/streamlit_app.py --server.port=8080 --server.address=0.0.0.0`

---

## Error Handling

**Strategy:** Not yet implemented (stub-only codebase). Intended mitigations from the plan:
- GitHub API rate limits: batch + cache; conditional requests
- Tavily quota exhaustion: fall back to HN-only news
- ChromaDB cold start on Cloud Run: set `min-instances=1`
- Generator-critic loop timeout: hard cap at 2 iterations per analyst

---

## Cross-Cutting Concerns

**Schema contract:** `src/models/schemas.py` — shared Pydantic models; must be agreed upon by both contributors before either layer is implemented

**Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` — local, no API dependency, ~384-dim vectors; managed in `src/rag/ingestion.py`

**Environment configuration:** `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT` — loaded via `python-dotenv`; see `.env.example`

**Deployment:** Google Cloud Run (containerized); image built from `Dockerfile`, pushed to Artifact Registry

---

*Architecture analysis: 2026-04-03*
