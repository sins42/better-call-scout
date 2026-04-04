# Codebase Structure

**Analysis Date:** 2026-04-03

## Directory Layout

```
better-call-scout/
├── app/
│   └── streamlit_app.py          # Streamlit UI — query input, tabs, charts, downloads
├── src/
│   ├── __init__.py
│   ├── orchestrator.py           # Top-level ADK agent — wires full pipeline
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── critic_agent.py       # Filter agent + generator-critic loop participant
│   │   ├── synthesis_agent.py    # Merges 3 hypotheses → unified report + artifacts
│   │   ├── collection/           # Stage 1: parallel data collection (3 agents)
│   │   │   ├── __init__.py
│   │   │   ├── github_agent.py
│   │   │   ├── hn_tavily_agent.py
│   │   │   └── rag_agent.py
│   │   └── analysis/             # Stage 3: parallel hypothesis generation (3 agents)
│   │       ├── __init__.py
│   │       ├── vc_analyst.py
│   │       ├── developer_analyst.py
│   │       └── journalist_analyst.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Shared Pydantic models — collection/analysis contract
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingestion.py          # Fetch → chunk → embed → store in ChromaDB
│   │   └── retrieval.py          # Query ChromaDB; used by collection + analysis agents
│   └── visualization/
│       ├── __init__.py
│       └── charts.py             # 4 matplotlib/seaborn charts → PNG
├── tests/
│   ├── __init__.py
│   ├── test_collection.py        # Unit tests for collection layer (Raghav)
│   ├── test_analysis.py          # Unit tests for analysis layer (Sindhuja)
│   └── test_e2e.py               # End-to-end pipeline tests (shared)
├── .env                          # Local secrets — never committed
├── .env.example                  # Required env var names (no values)
├── .gitignore
├── Dockerfile                    # Container image — Cloud Run deployment
├── pyproject.toml                # Project metadata, dependencies, pytest config
├── uv.lock                       # Locked dependency manifest
├── final_plan.md                 # Project plan and architecture diagram
└── README.md
```

---

## Directory Purposes

**`app/`**
- Purpose: Streamlit frontend — the only user-facing entry point
- Contains: Single file `streamlit_app.py`
- Owner: Sindhuja
- Key files: `app/streamlit_app.py`

**`src/agents/collection/`**
- Purpose: Stage 1 of the pipeline — three parallel data collection agents
- Contains: One ADK agent per external data source
- Owner: Raghav
- Key files:
  - `src/agents/collection/github_agent.py` — GitHub REST API integration
  - `src/agents/collection/hn_tavily_agent.py` — HN Firebase API + Tavily web search
  - `src/agents/collection/rag_agent.py` — ChromaDB vector retrieval agent

**`src/agents/analysis/`**
- Purpose: Stage 3 of the pipeline — three parallel analyst agents, each producing a structured hypothesis JSON
- Contains: One ADK agent per analyst persona
- Owner: Sindhuja
- Key files:
  - `src/agents/analysis/vc_analyst.py` — VC lens: star velocity, funding signals, market landscape
  - `src/agents/analysis/developer_analyst.py` — Developer lens: ecosystem maturity, adoption phase, job signals
  - `src/agents/analysis/journalist_analyst.py` — Journalist lens: narrative hooks, HN sentiment, media density

**`src/agents/critic_agent.py`**
- Purpose: Dual-role agent: (1) filter raw repos after Stage 1; (2) challenge analyst drafts in the generator-critic loop during Stage 3
- Owner: Raghav

**`src/agents/synthesis_agent.py`**
- Purpose: Stage 4 — merge three structured analyst hypotheses into `scout_report.md` and `top_repos.csv`
- Owner: Sindhuja

**`src/orchestrator.py`**
- Purpose: Top-level ADK orchestrator — wires Collection → Critic → Analysis → Synthesis; manages parallel ADK execution for both fan-out stages
- Owner: Shared (Raghav + Sindhuja)

**`src/models/`**
- Purpose: Shared Pydantic data models — the typed contract between the collection layer (Raghav) and the analysis layer (Sindhuja)
- Key files: `src/models/schemas.py`
- Owner: Shared — must be agreed upon on Day 1 before either layer is implemented

**`src/rag/`**
- Purpose: ChromaDB-backed RAG system — ingestion pipeline and retrieval interface
- Owner: Raghav
- Key files:
  - `src/rag/ingestion.py` — fetches HN stories and RSS feeds, chunks text, embeds with `all-MiniLM-L6-v2`, persists to ChromaDB
  - `src/rag/retrieval.py` — query interface used by `rag_agent.py` (Stage 1) and all three analyst agents (Stage 3)

**`src/visualization/`**
- Purpose: Chart generation — four matplotlib/seaborn figures rendered as PNG
- Owner: Sindhuja
- Key files: `src/visualization/charts.py`
- Charts: Star velocity line chart, category heatmap, HN buzz vs. GitHub stars scatter, persona score bar chart

**`tests/`**
- Purpose: Automated test suite
- Owner split:
  - `tests/test_collection.py` — Raghav (collection layer unit tests)
  - `tests/test_analysis.py` — Sindhuja (analysis layer unit tests)
  - `tests/test_e2e.py` — Shared (full pipeline end-to-end)
- Framework: pytest + pytest-asyncio (configured in `pyproject.toml`)

---

## Key File Locations

**Entry Points:**
- `app/streamlit_app.py` — user-facing UI; container CMD target; port 8080
- `src/orchestrator.py` — pipeline entry point called by Streamlit app

**Configuration:**
- `pyproject.toml` — dependencies, Python version (`>=3.11`), pytest settings
- `.env.example` — documents required env vars: `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT`
- `Dockerfile` — Cloud Run container definition; uses `uv` for dependency installation

**Core Logic:**
- `src/models/schemas.py` — shared data contract (implement first)
- `src/rag/ingestion.py` — offline corpus builder (run before first query)
- `src/rag/retrieval.py` — used by 4 agents across both pipeline stages

**Testing:**
- `tests/test_collection.py` — collection layer
- `tests/test_analysis.py` — analysis layer
- `tests/test_e2e.py` — full pipeline

---

## Naming Conventions

**Files:**
- Snake case throughout: `github_agent.py`, `hn_tavily_agent.py`, `vc_analyst.py`
- Agent files are named `<role>_agent.py` or `<persona>_analyst.py`
- Support modules named by function: `ingestion.py`, `retrieval.py`, `charts.py`, `schemas.py`

**Directories:**
- Plural nouns for grouping directories: `agents/`, `models/`, `tests/`
- Stage sub-directories use functional names: `collection/`, `analysis/`

**Tests:**
- `test_<layer>.py` pattern: `test_collection.py`, `test_analysis.py`, `test_e2e.py`

---

## Ownership Split

| Path | Owner |
|---|---|
| `src/agents/collection/` | Raghav |
| `src/agents/critic_agent.py` | Raghav |
| `src/rag/` | Raghav |
| `Dockerfile` | Raghav |
| `tests/test_collection.py` | Raghav |
| `src/agents/analysis/` | Sindhuja |
| `src/agents/synthesis_agent.py` | Sindhuja |
| `src/visualization/` | Sindhuja |
| `app/streamlit_app.py` | Sindhuja |
| `tests/test_analysis.py` | Sindhuja |
| `src/orchestrator.py` | Shared |
| `src/models/schemas.py` | Shared |
| `tests/test_e2e.py` | Shared |

---

## Where to Add New Code

**New collection agent (additional data source):**
- Implementation: `src/agents/collection/<source>_agent.py`
- Register in: `src/orchestrator.py` parallel collection fan-out
- Tests: `tests/test_collection.py`

**New analyst persona:**
- Implementation: `src/agents/analysis/<persona>_analyst.py`
- Register in: `src/orchestrator.py` parallel analysis fan-out
- Wire critic loop in orchestrator
- Tests: `tests/test_analysis.py`

**New chart:**
- Implementation: `src/visualization/charts.py` (add new function)
- Wire render call in: `src/agents/synthesis_agent.py`
- Expose download in: `app/streamlit_app.py`

**New shared data type:**
- Add to: `src/models/schemas.py`
- Coordinate between Raghav and Sindhuja before committing

**New utility/helper:**
- Shared helpers that cross the collection/analysis boundary: `src/` top level with a descriptive module name
- Layer-specific helpers: co-locate in the relevant sub-package (`src/agents/collection/`, `src/agents/analysis/`, `src/rag/`)

---

## Special Directories

**`.venv/`**
- Purpose: Virtual environment managed by `uv`
- Generated: Yes
- Committed: No (in `.gitignore`)

**`.planning/`**
- Purpose: GSD planning documents — architecture, structure, conventions, concerns
- Generated: Yes (by GSD tools)
- Committed: Yes

---

*Structure analysis: 2026-04-03*
