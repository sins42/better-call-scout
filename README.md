# Better Call Scout

A multi-agent VC/startup scout that performs the full data analyst lifecycle — collect, explore, and hypothesize — on trending GitHub repositories and tech news. Given a query like *"What Rust frameworks are breaking out in 2025?"*, Better Call Scout retrieves real-world data from multiple sources, runs three specialized analyst agents in parallel, and synthesizes a grounded investment/adoption hypothesis with supporting evidence, charts, and downloadable artifacts.

---

## Table of Contents

1. [Live Demo](#live-demo)
2. [Project Structure](#project-structure)
3. [Setup & Running Locally](#setup--running-locally)
4. [Environment Variables](#environment-variables)
5. [Deployment](#deployment)
6. [The Three Steps](#the-three-steps)
7. [Core Requirements](#core-requirements)
8. [Grab-Bag Electives](#grab-bag-electives)
9. [Architecture](#architecture)
10. [API Reference](#api-reference)
11. [Data Models](#data-models)

---

## Live Demo

**Deployed URL:** _[Cloud Run link here]_

Enter any tech-focused query (e.g. *"What AI inference frameworks are gaining momentum?"*) and the system will collect live data, run three analyst agents in parallel, and return a synthesized hypothesis with charts and downloadable artifacts.

---

## Project Structure

```
better-call-scout/
├── src/
│   ├── agents/
│   │   ├── collection/
│   │   │   ├── __init__.py              # collection_parallel + collection_pipeline wiring
│   │   │   ├── github_agent.py          # search_github_repos, fetch_repo_details tools
│   │   │   ├── hn_tavily_agent.py       # Tavily/dev.to/Reddit/ProductHunt tools + ChromaDB ingestion
│   │   │   └── rag_agent.py             # query_rag_corpus tool
│   │   ├── analysis/
│   │   │   ├── __init__.py              # analysis_layer ParallelAgent wiring
│   │   │   ├── _prompts.py              # All system prompts + RETRY_CONFIG
│   │   │   ├── vc_analyst.py            # VCAnalystGenerator + VCCritic + vc_analyst_loop
│   │   │   ├── developer_analyst.py     # DevGenerator + DevCritic + developer_analyst_loop
│   │   │   └── journalist_analyst.py    # JournalistGenerator + JournalistCritic + loop
│   │   ├── critic_agent.py              # heuristic_filter tool + LLM borderline evaluation
│   │   ├── guardrail_agent.py           # check_query() — topic classifier
│   │   └── synthesis_agent.py           # Synthesis LlmAgent + artifact generator functions
│   ├── models/
│   │   └── schemas.py                   # RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport
│   ├── rag/
│   │   ├── ingestion.py                 # chunk_text, ingest_documents, _generate_doc_id
│   │   └── retrieval.py                 # query_corpus, async_query_corpus
│   ├── visualization/
│   │   └── charts.py                    # star_velocity_chart, category_heatmap, buzz_scatter, persona_score_bars
│   └── orchestrator.py                  # run_pipeline(), generate_artifacts(), pipeline_agent assembly
├── app/
│   ├── main.py                          # FastAPI: POST /run, GET /stream, GET /download, GET /browse
│   └── static/
│       ├── index.html                   # Single-page frontend with SSE progress UI
│       └── browse.html                  # ChromaDB corpus browser
├── tests/
│   └── test_e2e.py
├── chroma_data/                         # Persistent ChromaDB (git-ignored)
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── .env.example
└── README.md
```

---

## Setup & Running Locally

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) package manager
- Google Cloud project with Vertex AI API enabled and authenticated
- GitHub personal access token
- Tavily API key

### Install

```bash
git clone <repo-url>
cd better-call-scout

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
uv sync
```

### Run

```bash
# Start the FastAPI server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload

# Open in browser
open http://localhost:8081
```

### Tests

```bash
uv run pytest
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID for Vertex AI |
| `GOOGLE_CLOUD_LOCATION` | No | GCP region (default: `us-central1`) |
| `GITHUB_TOKEN` | Yes | GitHub personal access token (5k req/hr authenticated vs 60 unauthenticated) |
| `TAVILY_API_KEY` | Yes | Tavily search API key |
| `PRODUCT_HUNT_TOKEN` | No | Product Hunt API token (Product Hunt collection skipped if absent) |
| `GEMINI_MODEL` | No | LLM model override (default: `gemini-2.0-flash`) |

---

## Deployment

The application is containerized and deployed on Google Cloud Run.

```bash
# Build the image
docker build -t better-call-scout .

# Run locally with Docker
docker run -p 8081:8081 --env-file .env better-call-scout
```

Cloud Run deployment requires the environment variables above to be set as Cloud Run environment variables or Secret Manager secrets. The container exposes port `8081`.

---

## The Three Steps

### Step 1: Collect

**What happens:** Three collection agents run in parallel, each retrieving real-world data from distinct external sources. None of this data is hard-coded — every fetch is driven by the user's query at runtime.

| Agent | Source | Data Retrieved | File |
|---|---|---|---|
| **GitHub Agent** | GitHub REST API | Trending repos: stars, star velocity (30-day growth rate), commit activity, contributors, open issues, topics | `src/agents/collection/github_agent.py` |
| **HN+Tavily Agent** | Tavily Search API, dev.to API, Reddit JSON API, Product Hunt GraphQL v2 | Tech news with VC-angle, developer-adoption, and hype/sentiment tagging | `src/agents/collection/hn_tavily_agent.py` |
| **RAG Agent** | ChromaDB (continuously updated from news ingestion) | Semantically similar chunks from previously ingested articles and documentation | `src/agents/collection/rag_agent.py` |

**GitHub Agent tools** (`github_agent.py`):
- `search_github_repos(query, language, min_stars)` — searches GitHub for matching repos
- `fetch_repo_details(owner, repo)` — fetches per-repo stats including **star velocity**: `recent_stars_30d / total_stars`, clamped to `[-1.0, 1.0]`, computed from stargazer timestamps with retry logic for GitHub's async stats endpoints (HTTP 202 cache-miss handling with exponential backoff)

**HN+Tavily Agent tools** (`hn_tavily_agent.py`):
- `fetch_devto_articles(query, limit)` — fetches articles by tag from dev.to, then ingests them into ChromaDB for RAG
- `fetch_reddit_posts(query, limit)` — searches r/programming, r/MachineLearning, r/webdev, r/devops, r/rust, r/golang
- `fetch_producthunt_posts(query, limit)` — Product Hunt GraphQL v2 API
- `search_tavily_vc(query)` — three parallel Tavily searches: funding rounds, market size, M&A activity
- `search_tavily_dev(query)` — three parallel Tavily searches: production adoption, hiring signals, benchmarks
- `search_tavily_journalist(query)` — three parallel Tavily searches: press coverage, community sentiment, hype analysis

News items are tagged with angle prefixes like `[vc_funding]`, `[dev_adoption]`, `[community_sentiment]` so downstream analysts can selectively attend to their relevant signal.

**RAG ingestion** (`src/rag/ingestion.py`):
- `chunk_text(text, chunk_size=500, overlap=50)` — overlapping window chunking
- `ingest_documents(documents, metadatas, ids)` — upserts into ChromaDB collection `"scout-corpus"` using SHA-256 deterministic IDs (`_generate_doc_id(source_url, chunk_index)`) to prevent duplicate ingestion on re-runs

**RAG retrieval** (`src/rag/retrieval.py`):
- `query_corpus(query_text, n_results=10)` — synchronous ChromaDB query with `all-MiniLM-L6-v2` embeddings (384-dim)
- `async_query_corpus(query_text, n_results=10)` — async wrapper via `asyncio.to_thread()`

**Why this is non-trivial:** The GitHub API returns thousands of repos with rich metadata. Tavily runs six search queries per pipeline run across VC, developer, and journalist angles. The ChromaDB corpus grows continuously as news is ingested. The data cannot be usefully loaded entirely into context.

---

### Step 2: Explore & Analyze (EDA)

**What happens:** After collection, a Critic Agent filters the raw repo list, then three analyst agents (VC, Developer, Journalist) each independently explore the data through their own lens using a generator-critic loop. The EDA is dynamic — each agent uses different signals, different news-angle tags, and produces different findings depending on the user's question.

#### Critic Agent — Heuristic Filtering (`src/agents/critic_agent.py`)

Before analysis begins, `heuristic_filter(repos_json)` applies deterministic rules to remove noise:

```
Always reject:  forks (is_fork == True) | commits < 5 | contributors < 1
Always pass:    commits > 20 AND contributors > 3 AND age > 30 days
Borderline:     everything else → escalated to LLM judgment
```

Returns `{passed, rejected, borderline}` dicts. The LLM evaluates borderline repos for relevance and genuine activity (not star-farming or bot activity).

#### Three Analyst Agents — Parallel EDA (`src/agents/analysis/`)

All three run in **parallel** via `ParallelAgent`. Each agent uses a **generator-critic loop** (`LoopAgent`, max 2 iterations):

**VC Analyst** (`vc_analyst.py`)
- Signals examined: star velocity acceleration in top 1%, funding mentions in news, market size estimates, competitive moat indicators
- Attends to news tagged: `[vc_funding]`, `[vc_market]`, `[vc_deals]`
- `VCAnalystGenerator` (LlmAgent) produces a draft `AnalystHypothesis` with structured output; `VCCritic` (LlmAgent) plays devil's advocate, challenging evidence selection and surfacing counter-evidence
- Output key: `vc_draft_output`

**Developer Analyst** (`developer_analyst.py`)
- Signals examined: contributor health trends, issue backlog growth rate, hiring signal density from job postings, benchmark comparisons, language ecosystem maturity
- Attends to news tagged: `[dev_adoption]`, `[dev_hiring]`, `[dev_benchmark]`
- Not swayed by star count alone — ecosystem maturity is the primary signal
- Output key: `dev_draft_output`

**Journalist Analyst** (`journalist_analyst.py`)
- Signals examined: community sentiment on Reddit/forums, media coverage density, narrative arcs (David vs Goliath, incumbent threat), hype cycle stage (early vs late press)
- Attends to news tagged: `[press_coverage]`, `[community_sentiment]`, `[hype_analysis]`
- Skeptical of sensationalism and survivorship bias
- Output key: `journalist_draft_output`

**Loop detail:** Generator reads collected data → forms draft hypothesis → Critic challenges it → Generator refines with counter-evidence addressed. Each iteration surfaces specific numbers and patterns (e.g., *"star velocity 0.73 places this in top 0.5% of repos indexed"*) that feed directly into Step 3.

**System prompts and retry config:** `src/agents/analysis/_prompts.py` — six role prompts (3 generators + 3 critics) plus shared `RETRY_CONFIG` (initial_delay=2s, attempts=3, max_output_tokens=8192) for Gemini 429 RESOURCE_EXHAUSTED handling.

---

### Step 3: Hypothesize

**What happens:** The Synthesis Agent receives the three independent analyst hypotheses, identifies consensus and divergence, and produces a unified report grounded in data from the previous steps, with evidence citations, confidence scores, and artifact exports.

**Synthesis Agent** (`src/agents/synthesis_agent.py`):
- Input: `{vc_draft_output}`, `{dev_draft_output}`, `{journalist_draft_output}` from session state
- Output schema: `SynthesisReport` (structured output)
- Task: synthesize across personas — not concatenation, but genuine integration of where analysts agree, where they differ, and what that means

**Fallback:** `build_synthesis_report_from_state(state, query, repos, personas)` — if Gemini output fails to parse as `SynthesisReport`, constructs a valid report directly from individual state keys rather than failing the run.

**Artifact generation functions:**
- `generate_scout_report_md(report)` (`synthesis_agent.py`) — Markdown report with per-analyst sections, confidence scores, evidence lists, counter-evidence, top repos table, sources
- `generate_top_repos_csv(report)` (`synthesis_agent.py`) — Pandas DataFrame export of all top repos with full metadata

**Visualizations** (`src/visualization/charts.py`) — four charts generated concurrently in a thread pool via `generate_artifacts()` in `src/orchestrator.py`:

| Chart | Type | Signal | Function |
|---|---|---|---|
| Star Velocity Trends | Multi-line | Per-repo velocity across 6-week window | `star_velocity_chart()` |
| Category Heatmap | Heatmap (YlOrRd) | Velocity by tech category over time | `category_heatmap()` |
| Buzz Scatter | Bubble scatter (log x-axis) | GitHub stars vs news buzz, sized by velocity | `buzz_scatter()` |
| Analyst Confidence | Bar chart | Confidence scores across 3 personas | `persona_score_bars()` |

**Evidence grounding:** Every `AnalystHypothesis` carries explicit `evidence: list[str]`, `counter_evidence: list[str]`, `reasoning: str`, and `sources: list[str]` (URLs from collected news items). The synthesis does not introduce information beyond what was collected — all claims trace back to specific data points from Steps 1 and 2.

---

## Core Requirements

| Requirement | Implementation | Location |
|---|---|---|
| **Frontend** | FastAPI + single-page HTML with real-time SSE progress stream and artifact downloads | `app/main.py`, `app/static/index.html` |
| **Agent Framework** | Google ADK — `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent` | `src/agents/`, `src/orchestrator.py` |
| **Tool Calling** | 8 tools across collection agents; heuristic filter tool in Critic Agent | `github_agent.py`, `hn_tavily_agent.py`, `rag_agent.py`, `critic_agent.py` |
| **Non-trivial Dataset** | GitHub REST API (thousands of repos), 6 Tavily searches per run, dev.to, Reddit, Product Hunt, ChromaDB vector corpus (grows per run) | `src/agents/collection/` |
| **Multi-agent Pattern** | Orchestrator-handoff (SequentialAgent), fan-out (ParallelAgent x2), generator-critic loop (LoopAgent x3), agent-as-tool-call (RAG) | `src/orchestrator.py`, `src/agents/` |
| **Deployed** | Dockerized for Google Cloud Run | `Dockerfile` |
| **README** | This document | `README.md` |

### Multi-agent Composition Detail

```
pipeline_agent (SequentialAgent)
├── collection_pipeline (SequentialAgent)
│   ├── collection_parallel (ParallelAgent)           ← fan-out
│   │   ├── github_agent (LlmAgent)
│   │   ├── hn_tavily_agent (LlmAgent)
│   │   └── rag_agent (LlmAgent)
│   └── critic_agent (LlmAgent)                       ← sequential handoff
├── analysis_layer (ParallelAgent)                    ← fan-out
│   ├── vc_analyst_loop (LoopAgent, max_iterations=2) ← generator-critic loop
│   │   ├── VCAnalystGenerator (LlmAgent)
│   │   └── VCCritic (LlmAgent)
│   ├── developer_analyst_loop (LoopAgent)
│   └── journalist_analyst_loop (LoopAgent)
└── synthesis_agent (LlmAgent)                        ← aggregation
```

---

## Grab-Bag Electives

### Elective 1: Structured Output

All key data contracts use Pydantic v2 schemas enforced via LLM structured output mode (`output_schema=` in `LlmAgent`). This ensures reliable parsing at every stage transition:

| Schema | Produced By | File |
|---|---|---|
| `RepoData` | GitHub Agent | `src/models/schemas.py` |
| `NewsItem` | HN+Tavily Agent | `src/models/schemas.py` |
| `RAGContextChunk` | RAG Agent | `src/models/schemas.py` |
| `AnalystHypothesis` | VC/Dev/Journalist generators | `src/models/schemas.py` |
| `SynthesisReport` | Synthesis Agent | `src/models/schemas.py` |

All models use Pydantic v2 `model_validator` (not the deprecated `validator`). Fields use strict types (`HttpUrl`, `float` with clamped ranges, `datetime`). The data contract is defined in `src/models/schemas.py` and shared across all layers.

### Elective 2: Data Visualization

Four matplotlib/seaborn charts are generated at the end of every pipeline run, served as PNG downloads:

- **Chart 1** (`star_velocity_chart()`) — Line chart: star velocity trends for top 10 repos across a 6-week window
- **Chart 2** (`category_heatmap()`) — Heatmap: star velocity by tech category over time (YlOrRd colormap)
- **Chart 3** (`buzz_scatter()`) — Bubble scatter: GitHub stars (log scale) vs news buzz score, bubble size = star velocity, labeled by repo name
- **Chart 4** (`persona_score_bars()`) — Bar chart: analyst confidence scores across VC, Developer, Journalist with 0.5 uncertainty reference line

All charts rendered as PNG bytes via `_fig_to_png(fig)` in `src/visualization/charts.py` and served via `GET /download/chart_{1-4}.png`.

### Elective 3: Artifacts

The pipeline writes persistent outputs per run, all downloadable via `/download/{artifact}?session_id=...`:

| Artifact | Format | Contents | Generated By |
|---|---|---|---|
| `scout_report.md` | Markdown | Full analyst report with hypothesis, evidence, counter-evidence, confidence, sources, top repos table | `generate_scout_report_md()` in `synthesis_agent.py` |
| `top_repos.csv` | CSV | All top repos: name, URL, stars, star_velocity, commits, contributors, topics, language | `generate_top_repos_csv()` in `synthesis_agent.py` |
| `chart_1.png` — `chart_4.png` | PNG | Visualizations described above | `src/visualization/charts.py` |

Artifacts are stored in-memory keyed by session ID (`_artifact_store` in `app/main.py`). The `/download` endpoint uses an allowlist to prevent path traversal.

### Elective 4: Parallel Execution

Three distinct layers of parallelism across the pipeline:

1. **Collection layer** (`collection_parallel: ParallelAgent`) — GitHub Agent, HN+Tavily Agent, and RAG Agent run concurrently; results aggregated before Critic Agent runs
2. **Analysis layer** (`analysis_layer: ParallelAgent`) — All three analyst LoopAgents run concurrently after collection completes
3. **Artifact generation** (`generate_artifacts()` in `src/orchestrator.py`) — All four chart generators run concurrently via `ThreadPoolExecutor`

---

## Architecture

```
User Query
    │
    ▼
Guardrail Agent ──(rejected)──► QueryRejectedError  [guardrail_agent.py]
    │ (allowed)
    ▼
collection_pipeline (SequentialAgent)
    │
    ├── collection_parallel (ParallelAgent) ─────────────────────────────────┐
    │   ├── GitHub Agent      → session["github_results"]  (list[RepoData])  │ parallel
    │   ├── HN+Tavily Agent   → session["hn_tavily_results"] (list[NewsItem])│
    │   └── RAG Agent         → session["rag_results"] (list[RAGContextChunk]│
    │                                                                         ┘
    └── Critic Agent          → session["filtered_repos"]
    │
    ▼
analysis_layer (ParallelAgent) ─────────────────────────────────────────────┐
    ├── vc_analyst_loop (LoopAgent x2)      → session["vc_draft_output"]    │ parallel
    │   ├── VCAnalystGenerator                                               │
    │   └── VCCritic                                                         │
    ├── developer_analyst_loop (LoopAgent x2) → session["dev_draft_output"] │
    └── journalist_analyst_loop (LoopAgent x2) → session["journalist_draft_output"]
                                                                             ┘
    │
    ▼
Synthesis Agent → SynthesisReport  [synthesis_agent.py]
    │
    ├── generate_scout_report_md() → scout_report.md
    ├── generate_top_repos_csv()   → top_repos.csv
    └── generate_artifacts()       → chart_1–4.png  (ThreadPoolExecutor)
    │
    ▼
FastAPI + SSE Frontend  [app/main.py, app/static/index.html]
```

**Session state:** Each pipeline run creates a unique session with a deterministic user ID. ADK substitutes `{placeholder}` values from session state into agent system prompts at runtime. Upstream agent outputs become inputs to downstream agents through this shared state dictionary.

---

## API Reference

### `POST /run`
Execute the full pipeline and return the complete report.

```json
// Request body
{ "query": "What Rust web frameworks are trending in 2025?" }

// Response
{ "session_id": "uuid-string", "report": { ...SynthesisReport } }
```

Errors: `400` invalid query / query rejected by guardrail, `504` timeout (300s), `500` pipeline failure.

### `GET /stream?query=...&personas=vc,dev,journalist`
Server-Sent Events stream with real-time progress. `personas` is optional (defaults to all three).

SSE event types: `collection_started`, `collection_complete`, `critic_started`, `critic_complete`, `analysis_started`, `analysis_complete`, `synthesis_started`, `synthesis_complete`, `session_id` (UUID for downloads), `complete` (final SynthesisReport JSON), `error_event`.

### `GET /download/{artifact}?session_id=...`
Download a generated artifact by name. Valid names: `scout_report.md`, `top_repos.csv`, `chart_1.png`, `chart_2.png`, `chart_3.png`, `chart_4.png`.

Errors: `400` unknown artifact name, `404` artifact not found for session.

### `GET /api/chroma/stats`
Returns ChromaDB corpus statistics: `total_chunks`, `total_documents`, `source_types` (breakdown by source), `documents` (list).

### `GET /browse`
Serves the ChromaDB corpus browser UI (`app/static/browse.html`).

---

## Data Models

All models defined in `src/models/schemas.py` (Pydantic v2):

**`RepoData`** — GitHub repo snapshot
- `name` (str): `"owner/repo"` format
- `url` (HttpUrl)
- `stars` (int)
- `star_velocity` (float): 30-day growth rate normalized to `[-1.0, 1.0]`
- `commits` (int): last 30 days
- `contributors` (int): unique count
- `issues` (int): open count
- `topics` (list[str]): GitHub topic tags
- `language` (Optional[str]): primary language

**`NewsItem`** — News article
- `title`, `url` (HttpUrl), `source` (str: `"hackernews"`, `"tavily"`, `"reddit"`, `"devto"`, `"producthunt"`)
- `score` (float): `[0.0, 1.0]` relevance/votes
- `content` (str): article body with angle tag prefix
- `published_at` (datetime)

**`RAGContextChunk`** — Vector retrieval result
- `text` (str): chunk content
- `source` (str): ChromaDB document ID
- `metadata` (dict): `source_url`, `title`, `chunk_index`, `source_type`

**`AnalystHypothesis`** — Analyst output
- `persona` (str): `"vc_analyst"` | `"developer_analyst"` | `"journalist"`
- `confidence_score` (float): `[0.0, 1.0]`
- `evidence` (list[str]): supporting data points
- `counter_evidence` (list[str]): risks and contradictions
- `reasoning` (str): narrative explanation
- `hypothesis_text` (str): final hypothesis statement
- `sources` (list[str]): URLs cited

**`SynthesisReport`** — Final pipeline output
- `query` (str): original user query
- `hypotheses` (list[AnalystHypothesis]): minimum 1 required
- `top_repos` (list[RepoData]): ranked repositories
- `generated_at` (datetime): UTC timestamp
