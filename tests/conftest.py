"""Shared pytest fixtures for Analysis Layer and end-to-end tests.

All fixtures are hardcoded from schema examples in src/models/schemas.py (per D-10).
Do not import from Phase 2 collection agents.
"""
import json
from datetime import datetime, timezone

import pytest

from src.models.schemas import AnalystHypothesis, NewsItem, RAGContextChunk, RepoData


@pytest.fixture
def mock_repos() -> list[RepoData]:
    """Three hardcoded RepoData objects for testing."""
    return [
        RepoData(
            name="langchain-ai/langchain",
            url="https://github.com/langchain-ai/langchain",
            stars=85000,
            star_velocity=0.42,
            commits=312,
            contributors=148,
            issues=520,
            topics=["llm", "agents", "python"],
            language="Python",
        ),
        RepoData(
            name="microsoft/semantic-kernel",
            url="https://github.com/microsoft/semantic-kernel",
            stars=22000,
            star_velocity=0.18,
            commits=98,
            contributors=62,
            issues=210,
            topics=["llm", "dotnet", "ai"],
            language="C#",
        ),
        RepoData(
            name="hwchase17/langchain",
            url="https://github.com/hwchase17/langchain",
            stars=4500,
            star_velocity=-0.05,
            commits=12,
            contributors=8,
            issues=44,
            topics=["llm"],
            language="Python",
        ),
    ]


@pytest.fixture
def mock_news() -> list[NewsItem]:
    """Two hardcoded NewsItem objects for testing."""
    return [
        NewsItem(
            title="Show HN: We built an open-source RAG framework",
            url="https://news.ycombinator.com/item?id=12345",
            source="hackernews",
            score=0.87,
            content="We just open-sourced our RAG pipeline used in production...",
            published_at=datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        NewsItem(
            title="LangChain Series B raises $25M",
            url="https://techcrunch.com/langchain-series-b",
            source="tavily",
            score=0.91,
            content="LangChain announces $25M Series B to expand enterprise offering...",
            published_at=datetime(2024, 2, 1, 8, 0, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def mock_rag_chunks() -> list[RAGContextChunk]:
    """Two hardcoded RAGContextChunk objects for testing."""
    return [
        RAGContextChunk(
            text="LangChain saw 300% growth in GitHub stars over Q1 2024...",
            source="chroma://scout-corpus/doc-42",
            metadata={"chunk_index": 2, "token_count": 128},
        ),
        RAGContextChunk(
            text="Semantic Kernel adoption accelerating in enterprise .NET shops...",
            source="chroma://scout-corpus/doc-17",
            metadata={"chunk_index": 0, "token_count": 95},
        ),
    ]


@pytest.fixture
def mock_session_state(mock_repos, mock_news, mock_rag_chunks) -> dict:
    """Pre-seeded session state dict for all analyst and synthesis agent tests."""
    return {
        "repo_data_json": json.dumps([r.model_dump(mode="json") for r in mock_repos]),
        "news_items_json": json.dumps([n.model_dump(mode="json") for n in mock_news]),
        "rag_chunks_json": json.dumps([c.model_dump(mode="json") for c in mock_rag_chunks]),
        "vc_draft_output": "",
        "vc_critic_output": "",
        "dev_draft_output": "",
        "dev_critic_output": "",
        "journalist_draft_output": "",
        "journalist_critic_output": "",
        "query": "AI dev tools about to break out",
    }


@pytest.fixture
def mock_vc_hypothesis() -> AnalystHypothesis:
    """Hardcoded VC analyst hypothesis fixture."""
    return AnalystHypothesis(
        persona="vc_analyst",
        confidence_score=0.78,
        evidence=["85k GitHub stars", "Series B announced Feb 2024", "star_velocity=0.42 (top 1%)"],
        counter_evidence=["Crowded LLM tooling market", "No enterprise contracts disclosed"],
        reasoning="Star velocity is top 1% of tracked repos. Funding signal confirms institutional validation.",
        hypothesis_text="LangChain is about to break out into enterprise. Series B + velocity = strong buy signal.",
    )


@pytest.fixture
def mock_dev_hypothesis() -> AnalystHypothesis:
    """Hardcoded developer analyst hypothesis fixture."""
    return AnalystHypothesis(
        persona="developer_analyst",
        confidence_score=0.65,
        evidence=["148 active contributors", "312 commits/month", "Python ecosystem strength"],
        counter_evidence=["520 open issues signals maintenance debt", "Rapid API changes hurt DX"],
        reasoning="Contributor count and commit velocity are healthy. Issue backlog is a concern.",
        hypothesis_text="LangChain is production-ready but carries maintenance risk from rapid iteration.",
    )


@pytest.fixture
def mock_journalist_hypothesis() -> AnalystHypothesis:
    """Hardcoded journalist hypothesis fixture."""
    return AnalystHypothesis(
        persona="journalist",
        confidence_score=0.55,
        evidence=["HN score 0.87 on RAG launch", "TechCrunch Series B coverage"],
        counter_evidence=[
            "Mainstream press may be late — story already peaked on HN",
            "Microsoft Semantic Kernel underreported",
        ],
        reasoning="HN community validated RAG use case early. Traditional media catching up. Real story is enterprise race.",
        hypothesis_text="The real story isn't LangChain — it's why Microsoft's Semantic Kernel is being ignored by the press.",
    )


from src.models.schemas import SynthesisReport


@pytest.fixture
def mock_synthesis_report(mock_repos, mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis) -> SynthesisReport:
    """Complete SynthesisReport built from mock fixtures for visualization tests."""
    return SynthesisReport(
        query="AI dev tools about to break out",
        hypotheses=[mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis],
        top_repos=mock_repos,
    )
