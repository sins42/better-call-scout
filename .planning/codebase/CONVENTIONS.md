# Coding Conventions

**Analysis Date:** 2026-04-03

## Module-Level Docstring Format

Every Python file in this project opens with a mandatory module-level docstring. The established pattern, inferred from all stub files, is:

```python
"""<Agent/Module Name> — <Layer Label> (<Owner: Name>)

<Line 1: Primary responsibility — one sentence, comma-separated concerns.>
<Line 2: Secondary responsibility or output format.>
"""
```

Examples from the codebase:

- `src/agents/collection/github_agent.py` — `"""GitHub Agent — Collection Layer (Person 1: Raghav)\n\nSearches repos by topic/language/stars via GitHub REST API.\nFetches star history, commit activity, contributor stats, issue velocity.\n"""`
- `src/agents/analysis/vc_analyst.py` — `"""VC Analyst Agent — Analysis Layer (Person 2: Sindhuja)\n\nStar velocity ranking, market size signals, funding mention extraction,\ncompetitive landscape scoring. Emits structured hypothesis JSON.\n"""`
- `src/models/schemas.py` — `"""Shared Pydantic Data Models (Shared: Raghav + Sindhuja)\n\nContract between Collection and Analysis layers.\nDefine all shared types here so both layers stay in sync.\n"""`

**Rules:**
- Line 1 of the docstring: `<Descriptive Name> — <Layer> (Owner)`
- Blank line, then 1-2 lines of functional description
- Ownership annotation is always present: `(Person 1: Raghav)`, `(Person 2: Sindhuja)`, or `(Shared: Raghav + Sindhuja)`
- Use em-dash ` — ` (not a hyphen) between name and layer label

## Naming Patterns

**Files:**
- `snake_case` for all Python source files
- Agent files are named after the data source or persona they represent: `github_agent.py`, `hn_tavily_agent.py`, `rag_agent.py`, `vc_analyst.py`, `developer_analyst.py`, `journalist_analyst.py`
- Non-agent files use a plain noun: `schemas.py`, `orchestrator.py`, `ingestion.py`, `retrieval.py`, `charts.py`

**Directories:**
- `snake_case` throughout: `src/agents/collection/`, `src/agents/analysis/`, `src/rag/`, `src/visualization/`
- Layer grouping is explicit in directory names — collection agents live in `collection/`, analysis agents in `analysis/`

**Agent Naming Convention:**
- Collection agents: `<source>_agent.py` — e.g., `github_agent.py`, `hn_tavily_agent.py`, `rag_agent.py`
- Analysis agents: `<persona>_analyst.py` — e.g., `vc_analyst.py`, `developer_analyst.py`, `journalist_analyst.py`
- Cross-cutting agents: plain `<role>_agent.py` — e.g., `critic_agent.py`, `synthesis_agent.py`

**Classes:**
- `PascalCase` (standard Python). Pydantic models use `PascalCase` class names.

**Functions and variables:**
- `snake_case` (standard Python)

**Constants / env var names:**
- `SCREAMING_SNAKE_CASE` — e.g., `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT`

## Module Structure

Every source file follows this layout order:

1. Module-level docstring (required)
2. Standard library imports
3. Third-party imports (ADK, Pydantic, requests, etc.)
4. Local imports (`src.*`)
5. Module-level constants
6. Class definitions (Pydantic models, agent classes)
7. Top-level functions

`__init__.py` files are present in all packages (`src/`, `src/agents/`, `src/agents/collection/`, `src/agents/analysis/`, `src/models/`, `src/rag/`, `src/visualization/`, `tests/`) but are currently empty — used for package declaration only.

## Pydantic Model Conventions

- All shared data models belong exclusively in `src/models/schemas.py`
- This file is the **contract** between the Collection and Analysis layers — no duplicated type definitions elsewhere
- Use Pydantic v2 (`pydantic>=2.7.0`)
- Model fields should use Python type annotations with no default where the field is required
- Structured output from analyst agents is described as "structured hypothesis JSON" — implement this as a typed Pydantic model, not a raw dict
- Models are shared and imported by both layers; do not define layer-specific models inside agent files

## Async Patterns

This project uses Google ADK (`google-adk>=0.1.0`) as the agent framework. ADK agents are inherently async. The following patterns apply:

- Agent entry points and tool implementations must be `async def`
- The orchestrator (`src/orchestrator.py`) manages parallel execution of the Collection layer (3 agents) and Analysis layer (3 agents) concurrently via ADK — use `asyncio.gather()` or ADK's parallel execution primitives for these layers
- The generator-critic refinement loop (max 2 iterations per analyst) must be implemented as an async loop
- Do not use blocking I/O calls (`requests.get` without a wrapper, `time.sleep`) inside async agent functions — use `httpx` async client or `asyncio.to_thread()` for blocking SDK calls

## Error Handling Expectations

- Agents should handle external API failures gracefully and propagate structured errors upward (do not swallow exceptions silently)
- GitHub API rate limiting (30 search/min, 5,000 req/hour) must be handled explicitly — catch 403/429 responses and either retry with backoff or return a partial result
- Tavily free-tier exhaustion (1,000 req/month) should degrade gracefully — fall back to HN-only data, not a hard crash
- ChromaDB cold-start latency on Cloud Run is a known risk — initialization should be wrapped so it fails clearly with a descriptive message, not a timeout exception
- All ADK tool functions should raise typed exceptions or return error-carrying Pydantic models rather than returning `None` or bare strings on failure

## Environment Configuration

- All secrets and API keys are loaded from environment variables, never hardcoded
- Required variables (from `.env.example`): `GITHUB_TOKEN`, `TAVILY_API_KEY`, `GOOGLE_CLOUD_PROJECT`
- Use `python-dotenv` (`python-dotenv>=1.0.0`) for local development: `load_dotenv()` called at application startup
- The `.env` file is gitignored; `.env.example` is committed as the authoritative list of required variables

## Import Style

- Use absolute imports from the `src` package root: `from src.models.schemas import RepoData`
- Do not use relative imports (e.g., avoid `from ..models import ...`)
- The `src` package is declared as the wheel target in `pyproject.toml` — all runtime code lives under `src/`

## Output Artifacts

- Analyst agents emit **structured hypothesis JSON** — implement as Pydantic models, not raw dicts
- Synthesis agent produces `scout_report.md` and `top_repos.csv` in-memory (for Streamlit `st.download_button`)
- Visualization charts (`src/visualization/charts.py`) produce matplotlib/seaborn figures as PNG bytes or file objects — do not write to disk in the agent layer

---

*Convention analysis: 2026-04-03*
