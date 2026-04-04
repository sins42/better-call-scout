# Testing Patterns

**Analysis Date:** 2026-04-03

## Test Framework

**Runner:**
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Async Mode:**
- `asyncio_mode = "auto"` — all async test functions are automatically treated as async tests without requiring `@pytest.mark.asyncio` decorators

**Test Discovery:**
- `testpaths = ["tests"]` — pytest searches only `tests/` at the project root

**Run Commands:**
```bash
pytest                        # Run all tests
pytest tests/test_collection.py   # Run collection layer tests only
pytest tests/test_analysis.py     # Run analysis layer tests only
pytest tests/test_e2e.py          # Run end-to-end tests only
pytest -v                         # Verbose output
pytest --tb=short                 # Short traceback format
```

Coverage is not yet configured — no `pytest-cov` in `pyproject.toml`. Add `pytest-cov` to `[project.optional-dependencies].dev` when coverage reporting is needed:
```bash
pytest --cov=src --cov-report=term-missing
```

## Test File Organization

**Location:** All test files live flat in `tests/` — no subdirectories.

**Package:** `tests/__init__.py` is present, making `tests/` a proper Python package.

**Naming:**
- Test files: `test_<layer_or_scope>.py`
- Test functions: `test_<what_is_being_tested>` (standard pytest convention)
- Test classes (if used): `Test<ComponentName>`

**Current test files:**
```
tests/
├── __init__.py
├── test_collection.py      # Collection layer — owned by Raghav
├── test_analysis.py        # Analysis layer — owned by Sindhuja
└── test_e2e.py             # End-to-end — shared ownership
```

**File-level docstring pattern** (matches source file convention):
```python
"""Collection Layer Tests (Person 1: Raghav)"""
```

Every test file opens with a one-line ownership docstring. Maintain this pattern in all new test files.

## Ownership Model

Tests are split by layer ownership, mirroring the source split:

| File | Owner | Scope |
|---|---|---|
| `tests/test_collection.py` | Raghav (Person 1) | GitHub Agent, HN+Tavily Agent, RAG Agent, Critic Agent, ingestion/retrieval pipeline |
| `tests/test_analysis.py` | Sindhuja (Person 2) | VC Analyst, Developer Analyst, Journalist Analyst, generator-critic loop, Synthesis Agent, charts, Streamlit rendering |
| `tests/test_e2e.py` | Both | Full pipeline: query in → collection → critic → analysis → synthesis → output artifacts |

When adding tests, place them in the file corresponding to the agent/module owner. Cross-layer integration tests belong in `test_e2e.py`.

## Async Test Patterns

Because `asyncio_mode = "auto"` is set globally, write async tests as plain `async def` — no decorator needed:

```python
async def test_github_agent_returns_repos():
    agent = GitHubAgent()
    result = await agent.search_repos(topic="llm", min_stars=100)
    assert len(result) > 0
    assert all(isinstance(r, RepoData) for r in result)
```

For testing ADK agents that involve the ADK runner, wrap in a real or mock ADK session:

```python
async def test_vc_analyst_emits_hypothesis():
    mock_data_pool = build_mock_data_pool()
    agent = VCAnalystAgent()
    hypothesis = await agent.analyze(mock_data_pool)
    assert isinstance(hypothesis, VCHypothesis)
    assert hypothesis.confidence_score >= 0.0
    assert hypothesis.confidence_score <= 1.0
```

**Do not** use `asyncio.run()` inside test functions — pytest-asyncio handles the event loop.

## Mocking Strategy

**Framework:** Use `unittest.mock` from the standard library (`pytest-mock` is not in `pyproject.toml` — add it as a dev dependency if `mocker` fixture style is preferred).

**What to mock:**

- **GitHub REST API** — mock `requests.get` or `httpx.AsyncClient.get` responses; return fixture JSON matching the GitHub Search API schema
- **Tavily API** — mock the `TavilyClient.search()` return value; return a list of fixture result dicts
- **HN Firebase API** — mock HTTP responses; return fixture story dicts
- **ChromaDB** — mock `chromadb.Client` or inject an in-memory ChromaDB instance using `chromadb.Client()` (no persistence path) for integration tests that need real vector ops
- **Vertex AI / Gemini** — mock at the ADK tool call boundary; do not make live LLM calls in unit or integration tests
- **Google ADK runner** — mock `google.adk.Runner` or `google.adk.Agent.run()` to return fixture structured outputs

**What NOT to mock:**

- Pydantic model validation — always test with real model instantiation to catch schema regressions
- `src/models/schemas.py` types — use real model instances in all tests, not raw dicts
- Internal pure functions (star velocity computation, chart generation logic) — test these directly without mocking

**Recommended mock pattern for external HTTP:**

```python
from unittest.mock import AsyncMock, patch

async def test_github_agent_handles_rate_limit():
    with patch("src.agents.collection.github_agent.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=MockResponse(status_code=429, json={})
        )
        agent = GitHubAgent()
        result = await agent.search_repos(topic="ai")
        # assert graceful degradation, not exception
        assert result == [] or isinstance(result, list)
```

**ChromaDB in-memory for tests:**

```python
import chromadb

def make_test_chroma_client():
    """Return an ephemeral in-memory ChromaDB client for testing."""
    return chromadb.Client()  # no persist_directory = in-memory only
```

## Fixtures and Test Data

Test data factories should produce valid Pydantic model instances. Define shared fixtures in `tests/conftest.py` (create this file — it does not exist yet):

```python
# tests/conftest.py
import pytest
from src.models.schemas import RepoData, NewsItem  # example model names

@pytest.fixture
def sample_repo():
    return RepoData(
        name="example/repo",
        stars=1500,
        # ... all required fields
    )

@pytest.fixture
def mock_data_pool(sample_repo):
    return {"repos": [sample_repo], "news": []}
```

**Location for fixtures:** `tests/conftest.py` — shared across all test files automatically by pytest.

**No external fixture files** are present yet. Keep test data inline or in `conftest.py`; avoid committing large JSON fixture files unless the test genuinely requires realistic API response shapes.

## Test Types and Scope

**Unit Tests** (`test_collection.py`, `test_analysis.py`):
- Scope: single agent or module in isolation
- All external I/O mocked
- Test that each agent produces the correct Pydantic output type
- Test error handling paths (API failures, rate limits, empty results)

**Integration Tests** (also in `test_collection.py`, `test_analysis.py`):
- Scope: one layer with real internal components (e.g., real ChromaDB in-memory + real embedding model)
- Mock only the outermost external boundary (HTTP, LLM)
- Verify data flows correctly through ingestion → retrieval, or collection → critic filter

**End-to-End Tests** (`test_e2e.py`):
- Scope: full pipeline from query input to output artifacts
- Use mock/stub versions of all external APIs
- Assert that `scout_report.md` content is non-empty, `top_repos.csv` is parseable, and all 4 chart PNG bytes are non-empty
- Owned jointly — both contributors should review `test_e2e.py` changes

## Error Testing Pattern

```python
async def test_agent_degrades_gracefully_on_api_failure():
    with patch("src.agents.collection.github_agent.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )
        agent = GitHubAgent()
        # Should not raise — should return empty or error-carrying result
        result = await agent.search_repos(topic="ai")
        assert isinstance(result, list)
```

## Coverage Targets

No coverage enforcement is currently configured. Recommended minimum targets once `pytest-cov` is added:

- `src/agents/collection/` — 80%
- `src/agents/analysis/` — 80%
- `src/models/schemas.py` — 100% (all model fields validated)
- `src/rag/` — 70%
- `src/orchestrator.py` — 60% (ADK wiring is harder to unit test)
- `app/streamlit_app.py` — not unit-tested (test via manual Streamlit run or E2E)

---

*Testing analysis: 2026-04-03*
