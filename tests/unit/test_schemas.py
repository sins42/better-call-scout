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


# ---------------------------------------------------------------------------
# RepoData tests
# ---------------------------------------------------------------------------


def test_repo_data_valid() -> None:
    """Valid RepoData instantiation round-trips field values correctly."""
    repo = RepoData(
        name="langchain-ai/langchain",
        url="https://github.com/langchain-ai/langchain",
        stars=85000,
        star_velocity=0.42,
        commits=312,
        contributors=148,
        issues=520,
        topics=["llm", "agents"],
        language="Python",
    )
    assert repo.stars == 85000
    assert repo.name == "langchain-ai/langchain"


def test_repo_data_rejects_negative_stars() -> None:
    """stars=-1 must raise ValidationError (ge=0 constraint)."""
    with pytest.raises(ValidationError):
        RepoData(
            name="foo/bar",
            url="https://github.com/foo/bar",
            stars=-1,
            star_velocity=0.0,
            commits=0,
            contributors=0,
            issues=0,
        )


def test_repo_data_star_velocity_bounds() -> None:
    """star_velocity=1.5 must raise ValidationError (le=1.0 constraint)."""
    with pytest.raises(ValidationError):
        RepoData(
            name="foo/bar",
            url="https://github.com/foo/bar",
            stars=0,
            star_velocity=1.5,
            commits=0,
            contributors=0,
            issues=0,
        )


def test_repo_data_topics_defaults_empty() -> None:
    """Omitting topics should default to an empty list."""
    repo = RepoData(
        name="foo/bar",
        url="https://github.com/foo/bar",
        stars=0,
        star_velocity=0.0,
        commits=0,
        contributors=0,
        issues=0,
    )
    assert repo.topics == []


def test_repo_data_language_optional() -> None:
    """Omitting language should default to None."""
    repo = RepoData(
        name="foo/bar",
        url="https://github.com/foo/bar",
        stars=0,
        star_velocity=0.0,
        commits=0,
        contributors=0,
        issues=0,
    )
    assert repo.language is None


# ---------------------------------------------------------------------------
# NewsItem tests
# ---------------------------------------------------------------------------


def test_news_item_valid() -> None:
    """Valid NewsItem instantiation; score is float, published_at is datetime."""
    item = NewsItem(
        title="Show HN: Open-source RAG",
        url="https://news.ycombinator.com/item?id=12345",
        source="hackernews",
        score=0.87,
        content="We just open-sourced our RAG pipeline...",
        published_at="2024-03-15T10:30:00Z",
    )
    assert isinstance(item.score, float)
    assert isinstance(item.published_at, datetime)


def test_news_item_score_bounds() -> None:
    """score=1.1 must raise ValidationError (le=1.0 constraint)."""
    with pytest.raises(ValidationError):
        NewsItem(
            title="Test",
            url="https://example.com",
            source="tavily",
            score=1.1,
            content="content",
            published_at="2024-01-01T00:00:00Z",
        )


def test_news_item_published_at_coercion() -> None:
    """published_at as ISO 8601 string is coerced to datetime."""
    item = NewsItem(
        title="Test",
        url="https://example.com",
        source="tavily",
        score=0.5,
        content="content",
        published_at="2024-01-01T00:00:00Z",
    )
    assert isinstance(item.published_at, datetime)


# ---------------------------------------------------------------------------
# RAGContextChunk tests
# ---------------------------------------------------------------------------


def test_rag_chunk_valid() -> None:
    """Valid RAGContextChunk instantiation with text, source, and metadata."""
    chunk = RAGContextChunk(
        text="LangChain saw 300% growth in GitHub stars over Q1 2024...",
        source="chroma://scout-corpus/doc-42",
        metadata={"chunk_index": 2, "token_count": 128},
    )
    assert chunk.text.startswith("LangChain")
    assert chunk.metadata["chunk_index"] == 2


def test_rag_chunk_metadata_defaults() -> None:
    """Omitting metadata should default to an empty dict."""
    chunk = RAGContextChunk(
        text="Some context chunk.",
        source="chroma://scout-corpus/doc-1",
    )
    assert chunk.metadata == {}


# ---------------------------------------------------------------------------
# AnalystHypothesis tests
# ---------------------------------------------------------------------------


def test_analyst_hypothesis_valid() -> None:
    """Full valid AnalystHypothesis instantiation."""
    hypo = AnalystHypothesis(
        persona="vc_analyst",
        confidence_score=0.78,
        evidence=["85k GitHub stars", "Series B announced Feb 2024"],
        counter_evidence=["Crowded market"],
        reasoning="Star velocity is top 1% of tracked repos...",
        hypothesis_text="LangChain is poised for enterprise breakout in H2 2024.",
    )
    assert hypo.persona == "vc_analyst"
    assert hypo.confidence_score == 0.78


def test_analyst_hypothesis_confidence_too_high() -> None:
    """confidence_score=1.01 must raise ValidationError (le=1.0 constraint)."""
    with pytest.raises(ValidationError):
        AnalystHypothesis(
            persona="vc_analyst",
            confidence_score=1.01,
            reasoning="Too confident.",
            hypothesis_text="This will fail.",
        )


def test_analyst_hypothesis_empty_evidence_allowed() -> None:
    """evidence=[] and counter_evidence=[] should not raise an error."""
    hypo = AnalystHypothesis(
        persona="journalist",
        confidence_score=0.5,
        evidence=[],
        counter_evidence=[],
        reasoning="Neutral stance.",
        hypothesis_text="Too early to tell.",
    )
    assert hypo.evidence == []
    assert hypo.counter_evidence == []


# ---------------------------------------------------------------------------
# SynthesisReport tests
# ---------------------------------------------------------------------------


def _make_hypothesis() -> dict:
    """Return a minimal valid AnalystHypothesis dict."""
    return {
        "persona": "vc_analyst",
        "confidence_score": 0.78,
        "reasoning": "Star velocity is top 1% of tracked repos...",
        "hypothesis_text": "LangChain is poised for enterprise breakout.",
    }


def _make_repo() -> dict:
    """Return a minimal valid RepoData dict."""
    return {
        "name": "langchain-ai/langchain",
        "url": "https://github.com/langchain-ai/langchain",
        "stars": 85000,
        "star_velocity": 0.42,
        "commits": 312,
        "contributors": 148,
        "issues": 520,
    }


def test_synthesis_report_valid() -> None:
    """SynthesisReport with one hypothesis and one repo instantiates correctly."""
    report = SynthesisReport(
        query="what AI dev tools are about to break out",
        hypotheses=[_make_hypothesis()],
        top_repos=[_make_repo()],
    )
    assert report.query == "what AI dev tools are about to break out"
    assert len(report.hypotheses) == 1
    assert len(report.top_repos) == 1


def test_synthesis_report_empty_hypotheses_rejected() -> None:
    """hypotheses=[] must raise ValidationError (min_length=1 constraint)."""
    with pytest.raises(ValidationError):
        SynthesisReport(
            query="some query",
            hypotheses=[],
        )


def test_synthesis_report_generated_at_defaults() -> None:
    """Omitting generated_at should produce a datetime default."""
    report = SynthesisReport(
        query="some query",
        hypotheses=[_make_hypothesis()],
    )
    assert isinstance(report.generated_at, datetime)


def test_synthesis_report_top_repos_defaults_empty() -> None:
    """Omitting top_repos should default to an empty list."""
    report = SynthesisReport(
        query="some query",
        hypotheses=[_make_hypothesis()],
    )
    assert report.top_repos == []
