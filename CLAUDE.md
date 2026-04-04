# Better Call Scout — Claude Code Guidelines

## Project Overview

Multi-agent VC/startup scout using Google ADK, Gemini 2.0 Flash (Vertex AI), ChromaDB, Streamlit, deployed on Cloud Run.

**Two teammates:**
- **Person 1 — Raghav (thehyperpineapple):** `src/agents/collection/`, `src/rag/`, `src/agents/critic_agent.py`, `Dockerfile`, deployment
- **Person 2 — Sindhuja (sins42):** `src/agents/analysis/`, `src/agents/synthesis_agent.py`, `src/visualization/`, `app/`
- **Shared:** `src/models/schemas.py`, `src/orchestrator.py`, `tests/test_e2e.py`

## Running the Project

```bash
# Install dependencies
uv sync

# Run Streamlit app locally
uv run streamlit run app/streamlit_app.py

# Run tests
uv run pytest

# Add a dependency
uv add <package>
```

## Environment Setup

Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Required env vars: `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT`

## Architecture

```
Collection Layer (parallel)         Analysis Layer (parallel)
┌──────────────┐                   ┌──────────────────┐
│ GitHub Agent │                   │ VC Analyst       │
│ HN+Tavily    │ → Critic Agent → │ Developer Analyst│ → Synthesis → Streamlit
│ RAG Agent    │   (filter)        │ Journalist       │
└──────────────┘                   └──────────────────┘
```

Data contract: `src/models/schemas.py` — define here first before building either layer.

## Coding Conventions

- **Python 3.11**, type hints required on all public functions
- **Pydantic v2** for all data models — use `model_validator` not `validator`
- **Async** for all ADK agent functions
- **Docstrings** on all classes and public methods (Google style)
- **snake_case** for files and functions, `PascalCase` for classes
- Never commit `.env` — use `.env.example` for new vars

## GSD Workflow

This project uses GSD for structured development. Planning artifacts live in `.planning/`.

```bash
# Check current status
/gsd:progress

# Plan your next phase
/gsd:plan-phase <N>

# Execute a phase
/gsd:execute-phase <N>
```

**Person 1 phases:** 1 (shared), 2 (yours), partial 4 & 5
**Person 2 phases:** 1 (shared), 3 (yours), partial 4

## Git Conventions

- Branch from `master`, merge back via PR
- Commit messages: `type(scope): description` — e.g. `feat(collection): add github star velocity`
- Do **not** commit: `.env`, `chroma_data/`, `.venv/`, `.python-version`
- Do **not** add Claude as co-author in commits
