---
phase: 01-data-contracts
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/models/schemas.py
  - tests/unit/__init__.py
  - tests/unit/test_schemas.py
autonomous: true
requirements:
  - SCHEMA-01
  - SCHEMA-02
  - SCHEMA-03
  - SCHEMA-04
  - SCHEMA-05

must_haves:
  truths:
    - "from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport succeeds without error"
    - "Each model instantiates correctly with valid sample data"
    - "Each model raises a ValidationError when required fields are missing or have wrong types"
    - "Both teammates can reference field names and types from this file as a stable contract"
  artifacts:
    - path: "src/models/schemas.py"
      provides: "All five Pydantic v2 models with field definitions, validators, and sample fixtures"
      exports:
        - RepoData
        - NewsItem
        - RAGContextChunk
        - AnalystHypothesis
        - SynthesisReport
    - path: "tests/unit/test_schemas.py"
      provides: "Unit tests covering valid instantiation and validation rejection for all five models"
  key_links:
    - from: "src/agents/collection/"
      to: "src/models/schemas.py"
      via: "RepoData, NewsItem, RAGContextChunk imports"
    - from: "src/agents/analysis/"
      to: "src/models/schemas.py"
      via: "AnalystHypothesis, SynthesisReport imports"
---

<objective>
Define all five shared Pydantic v2 models in src/models/schemas.py and verify them with unit tests so both teammates can import stable, typed contracts immediately.

Purpose: Phase 1 unblocks Phases 2 and 3. Without agreed field names and types, both collection and analysis agents cannot be built independently.
Output: src/models/schemas.py with five complete models; tests/unit/test_schemas.py with passing tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@src/models/schemas.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement all five Pydantic v2 models in src/models/schemas.py</name>
  <files>src/models/schemas.py</files>
  <behavior>
    - RepoData accepts valid repo dict with all required fields and optional ones defaulting correctly
    - RepoData rejects a dict where stars is a negative int (ge=0 constraint)
    - RepoData rejects a dict where star_velocity is outside [-1.0, 1.0] (ge=-1.0, le=1.0 constraint)
    - NewsItem accepts valid news dict with all required fields
    - NewsItem rejects a dict where score is outside [0.0, 1.0]
    - NewsItem accepts published_at as a datetime or ISO 8601 string (Pydantic coerces it)
    - RAGContextChunk accepts valid chunk dict; metadata defaults to empty dict when omitted
    - AnalystHypothesis rejects confidence_score outside [0.0, 1.0]
    - AnalystHypothesis accepts empty lists for evidence and counter_evidence
    - SynthesisReport's generated_at defaults to current UTC time when omitted
    - SynthesisReport rejects an empty hypotheses list (min_length=1)
  </behavior>
  <action>
    Replace the existing module docstring in src/models/schemas.py with the full implementation below.

    Use these exact imports at the top:
    ```python
    from __future__ import annotations

    from datetime import datetime, timezone
    from typing import Any, Optional

    from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
    ```

    Define models in this order (dependency order — SynthesisReport references AnalystHypothesis and RepoData):

    ---

    **RepoData** (SCHEMA-01)
    Fields:
    - name: str — repository full name, e.g. "owner/repo"
    - url: HttpUrl — repository HTML URL
    - stars: int — Field(ge=0)
    - star_velocity: float — normalized 30-day star growth rate, Field(ge=-1.0, le=1.0)
    - commits: int — commit count in last 30 days, Field(ge=0)
    - contributors: int — unique contributor count, Field(ge=0)
    - issues: int — open issue count, Field(ge=0)
    - topics: list[str] — GitHub topic tags, Field(default_factory=list)
    - language: Optional[str] — primary language, default None

    model_config with json_schema_extra containing one fixture:
    ```python
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "langchain-ai/langchain",
                "url": "https://github.com/langchain-ai/langchain",
                "stars": 85000,
                "star_velocity": 0.42,
                "commits": 312,
                "contributors": 148,
                "issues": 520,
                "topics": ["llm", "agents", "python"],
                "language": "Python",
            }
        }
    )
    ```

    ---

    **NewsItem** (SCHEMA-02)
    Fields:
    - title: str
    - url: HttpUrl
    - source: str — e.g. "hackernews", "tavily"
    - score: float — relevance score, Field(ge=0.0, le=1.0)
    - content: str — article body or excerpt
    - published_at: datetime — use Pydantic's datetime coercion (accepts ISO strings)

    model_config fixture:
    ```python
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Show HN: We built an open-source RAG framework",
                "url": "https://news.ycombinator.com/item?id=12345",
                "source": "hackernews",
                "score": 0.87,
                "content": "We just open-sourced our RAG pipeline...",
                "published_at": "2024-03-15T10:30:00Z",
            }
        }
    )
    ```

    ---

    **RAGContextChunk** (SCHEMA-03)
    Fields:
    - text: str — the retrieved chunk content
    - source: str — document identifier or URL string (plain str, not HttpUrl — can be a file path or an ID)
    - metadata: dict[str, Any] — arbitrary key-value pairs, Field(default_factory=dict)

    model_config fixture:
    ```python
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "LangChain saw 300% growth in GitHub stars over Q1 2024...",
                "source": "chroma://scout-corpus/doc-42",
                "metadata": {"chunk_index": 2, "token_count": 128},
            }
        }
    )
    ```

    ---

    **AnalystHypothesis** (SCHEMA-04)
    Fields:
    - persona: str — analyst persona name, e.g. "vc_analyst", "developer_analyst", "journalist"
    - confidence_score: float — Field(ge=0.0, le=1.0)
    - evidence: list[str] — supporting evidence points, Field(default_factory=list)
    - counter_evidence: list[str] — counter-points, Field(default_factory=list)
    - reasoning: str — step-by-step reasoning narrative
    - hypothesis_text: str — the final hypothesis statement

    model_config fixture:
    ```python
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "persona": "vc_analyst",
                "confidence_score": 0.78,
                "evidence": ["85k GitHub stars", "Series B announced Feb 2024"],
                "counter_evidence": ["Crowded market", "No enterprise contracts disclosed"],
                "reasoning": "Star velocity is top 1% of tracked repos...",
                "hypothesis_text": "LangChain is poised for enterprise breakout in H2 2024.",
            }
        }
    )
    ```

    ---

    **SynthesisReport** (SCHEMA-05)
    Fields:
    - query: str — the original user query
    - hypotheses: list[AnalystHypothesis] — Field(min_length=1) — at least one hypothesis required
    - top_repos: list[RepoData] — Field(default_factory=list)
    - generated_at: datetime — defaults to UTC now: Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config fixture:
    ```python
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "what AI dev tools are about to break out",
                "hypotheses": [
                    {
                        "persona": "vc_analyst",
                        "confidence_score": 0.78,
                        "evidence": ["85k stars"],
                        "counter_evidence": [],
                        "reasoning": "...",
                        "hypothesis_text": "LangChain will dominate enterprise LLM tooling.",
                    }
                ],
                "top_repos": [],
                "generated_at": "2024-03-15T12:00:00Z",
            }
        }
    )
    ```

    Add `from pydantic import ConfigDict` to the imports.

    Each model class must have a Google-style docstring describing its purpose and the layer that produces/consumes it.
  </action>
  <verify>
    <automated>cd /Users/raghav/Documents/Projects/better-call-scout && uv run python -c "from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport; print('Import OK')"</automated>
  </verify>
  <done>
    All five classes are importable. Each has typed fields matching the spec above. Pydantic ConfigDict with json_schema_extra fixture is present on every model.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write unit tests for all five models in tests/unit/test_schemas.py</name>
  <files>tests/unit/__init__.py, tests/unit/test_schemas.py</files>
  <behavior>
    Follow RED-GREEN-REFACTOR: write tests first, then confirm they pass against the implementation from Task 1.

    Tests to write:

    RepoData:
    - test_repo_data_valid: instantiate with all fields including optionals; assert field values round-trip
    - test_repo_data_rejects_negative_stars: pass stars=-1, expect ValidationError
    - test_repo_data_star_velocity_bounds: pass star_velocity=1.5, expect ValidationError
    - test_repo_data_topics_defaults_empty: omit topics, assert topics == []
    - test_repo_data_language_optional: omit language, assert language is None

    NewsItem:
    - test_news_item_valid: instantiate with all fields; assert score and published_at are correct types
    - test_news_item_score_bounds: pass score=1.1, expect ValidationError
    - test_news_item_published_at_coercion: pass published_at as ISO string "2024-01-01T00:00:00Z", assert isinstance(result.published_at, datetime)

    RAGContextChunk:
    - test_rag_chunk_valid: instantiate with text, source, metadata
    - test_rag_chunk_metadata_defaults: omit metadata, assert metadata == {}

    AnalystHypothesis:
    - test_analyst_hypothesis_valid: full valid instantiation
    - test_analyst_hypothesis_confidence_too_high: pass confidence_score=1.01, expect ValidationError
    - test_analyst_hypothesis_empty_evidence_allowed: pass evidence=[], counter_evidence=[], expect no error

    SynthesisReport:
    - test_synthesis_report_valid: instantiate with one hypothesis and one repo
    - test_synthesis_report_empty_hypotheses_rejected: pass hypotheses=[], expect ValidationError
    - test_synthesis_report_generated_at_defaults: omit generated_at, assert isinstance(result.generated_at, datetime)
    - test_synthesis_report_top_repos_defaults_empty: omit top_repos, assert top_repos == []
  </behavior>
  <action>
    1. Create tests/unit/__init__.py as an empty file.

    2. Create tests/unit/test_schemas.py with the following structure:

    ```python
    """Unit tests for src/models/schemas.py

    Covers valid instantiation and validation rejection for all five models.
    Run with: uv run pytest tests/unit/test_schemas.py -v
    """
    from datetime import datetime

    import pytest
    from pydantic import ValidationError

    from src.models.schemas import (
        AnalystHypothesis,
        NewsItem,
        RAGContextChunk,
        RepoData,
        SynthesisReport,
    )
    ```

    Then implement each test function listed in the behavior block above.

    Use minimal fixtures — inline dicts are fine, no fixtures() needed.
    All tests must be plain `def` functions (not async) — schemas are pure data, no I/O.
    Use `pytest.raises(ValidationError)` for rejection tests.
  </action>
  <verify>
    <automated>cd /Users/raghav/Documents/Projects/better-call-scout && uv run pytest tests/unit/test_schemas.py -v</automated>
  </verify>
  <done>
    All tests pass. pytest reports 0 failures, 0 errors. Every model has at least one valid-instantiation test and at least one rejection test.
  </done>
</task>

</tasks>

<verification>
Run both checks in order. Both must pass before marking the phase complete.

1. Import check:
   `uv run python -c "from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport; print('All imports OK')"`

2. Full test suite:
   `uv run pytest tests/unit/test_schemas.py -v`

Maps to success criteria:
- Criterion 1: covered by the import check command above
- Criterion 2: covered by validation rejection tests in test_schemas.py
- Criterion 3: human checkpoint — both teammates review field names in src/models/schemas.py and agree before Phase 2/3 work begins
- Criterion 4: confirmed structurally — models are the declared return types for collection agents (RepoData, NewsItem, RAGContextChunk) and analysis agents (AnalystHypothesis, SynthesisReport)
</verification>

<success_criteria>
- `from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport` exits 0
- `uv run pytest tests/unit/test_schemas.py -v` shows all green, zero failures
- src/models/schemas.py contains exactly five model classes with Google-style docstrings, typed fields, and json_schema_extra fixtures
- tests/unit/test_schemas.py contains at least 16 test functions covering valid and invalid cases for every model
</success_criteria>

<output>
After completion, create `.planning/phase-1/01-01-SUMMARY.md` following the summary template at @$HOME/.claude/get-shit-done/templates/summary.md.
</output>
