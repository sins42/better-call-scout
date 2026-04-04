# Technology Stack

**Analysis Date:** 2026-04-03

## Languages

**Primary:**
- Python 3.11+ — All application code, agents, RAG pipeline, and Streamlit frontend

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3.11 (enforced via `requires-python = ">=3.11"` in `pyproject.toml` and `FROM python:3.11-slim` in `Dockerfile`)

**Package Manager:**
- `uv` (Astral) — installed via `COPY --from=ghcr.io/astral-sh/uv:latest` in `Dockerfile`
- Lockfile: `uv.lock` present and committed; `--frozen` flag used in Docker build (`uv sync --frozen --no-dev`)

## Frameworks

**Core:**
- `google-adk >= 0.1.0` — Google Agent Development Kit; orchestrates all multi-agent flows, wires collection/analysis/synthesis pipeline (`src/orchestrator.py`)
- `streamlit >= 1.35.0` — Web UI framework; serves the frontend at port 8080 (`app/streamlit_app.py`)
- `pydantic >= 2.7.0` — Data validation and typed schemas shared across agent layers (`src/models/schemas.py`)

**ML / Embeddings:**
- `sentence-transformers >= 3.0.0` — Local MiniLM model used for embedding HN stories and RSS feed chunks during RAG ingestion (`src/rag/ingestion.py`)
- `google-cloud-aiplatform >= 1.60.0` — Vertex AI SDK; provides Gemini model access for all analyst and synthesis agents

**Vector Database:**
- `chromadb >= 0.5.0` — Embedded vector store; holds pre-embedded HN stories, RSS feeds, domain context (`src/rag/ingestion.py`, `src/rag/retrieval.py`, `src/agents/collection/rag_agent.py`)

**Data / Search:**
- `tavily-python >= 0.3.0` — Tavily search SDK; used in HN + Tavily collection agent (`src/agents/collection/hn_tavily_agent.py`)
- `requests >= 2.32.0` — HTTP client for GitHub REST API and HN Firebase API calls (`src/agents/collection/github_agent.py`, `src/agents/collection/hn_tavily_agent.py`)
- `pandas >= 2.2.0` — Tabular data manipulation; used for repo scoring and CSV artifact export (`src/agents/synthesis_agent.py`)

**Visualization:**
- `matplotlib >= 3.9.0` — Chart rendering (`src/visualization/charts.py`)
- `seaborn >= 0.13.0` — Statistical chart styling (`src/visualization/charts.py`)

**Testing:**
- `pytest >= 8.0.0` — Test runner; config in `pyproject.toml` under `[tool.pytest.ini_options]`
- `pytest-asyncio >= 0.23.0` — Async test support; `asyncio_mode = "auto"` is set globally

**Configuration:**
- `python-dotenv >= 1.0.0` — Loads `.env` file into environment at runtime

**Build Backend:**
- `hatchling` — PEP 517 build backend declared in `pyproject.toml`; packages the `src/` directory as a wheel

## Key Dependencies

**Critical:**
- `google-adk >= 0.1.0` — Core orchestration; without this the multi-agent pipeline cannot run
- `google-cloud-aiplatform >= 1.60.0` — Gemini inference; all analyst and synthesis agents require this
- `chromadb >= 0.5.0` — RAG corpus store; collection and retrieval agents depend on it at runtime
- `sentence-transformers >= 3.0.0` — Embedding model for ingestion pipeline; must be available before ChromaDB can be queried

**Infrastructure:**
- `pydantic >= 2.7.0` — Shared contract between collection and analysis layers (`src/models/schemas.py`); changing versions may break serialization
- `streamlit >= 1.35.0` — The only web server; the Dockerfile entrypoint runs `streamlit run`

## Configuration

**Environment:**
- Loaded via `python-dotenv` from a `.env` file (template: `.env.example`)
- Three required keys: `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT`
- No `.env` file is committed; only `.env.example` is present

**Build:**
- `pyproject.toml` — Single source of truth for dependencies, build system, and pytest config
- `uv.lock` — Reproducible dependency resolution lockfile used by Docker build
- `Dockerfile` — Multi-stage-style build: copies lockfile first, runs `uv sync --frozen --no-dev`, then copies application source

## Platform Requirements

**Development:**
- Python 3.11+
- `uv` package manager installed locally
- `.env` file populated from `.env.example`
- GCP project with Vertex AI API enabled

**Production:**
- Docker container targeting `python:3.11-slim`
- Exposes port `8080`
- Intended deployment target: Google Cloud Run (inferred from port 8080 convention and `GOOGLE_CLOUD_PROJECT` env var)
- No persistent volume required at boot; ChromaDB is embedded and populated by ingestion pipeline at runtime

---

*Stack analysis: 2026-04-03*
