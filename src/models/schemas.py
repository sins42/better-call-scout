"""Shared Pydantic Data Models (Shared: Raghav + Sindhuja)

Contract between Collection and Analysis layers.
Define all shared types here so both layers stay in sync.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class RepoData(BaseModel):
    """Repo data produced by the GitHub Collection Agent.

    Attributes:
        name: Repository full name in "owner/repo" format.
        url: Repository HTML URL.
        stars: Total star count (non-negative).
        star_velocity: 30-day star growth rate normalized as (stars_last_30d / total_stars),
            clamped to [-1.0, 1.0]. Negative values indicate net unfollows.
        commits: Commit count in the last 30 days.
        contributors: Unique contributor count.
        issues: Open issue count.
        topics: GitHub topic tags attached to the repository.
        language: Primary programming language, if available.
    """

    name: str
    url: HttpUrl
    stars: int = Field(ge=0)
    star_velocity: float = Field(
        ge=-1.0,
        le=1.0,
        description="stars_last_30d / total_stars, clamped to [-1.0, 1.0]",
    )
    commits: int = Field(ge=0)
    contributors: int = Field(ge=0)
    issues: int = Field(ge=0)
    topics: list[str] = Field(default_factory=list)
    language: Optional[str] = None

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


class NewsItem(BaseModel):
    """News item produced by the HN+Tavily Collection Agent.

    Attributes:
        title: Article or post title.
        url: Canonical URL of the news item.
        source: Data source identifier, e.g. "hackernews" or "tavily".
        score: Relevance score in [0.0, 1.0].
        content: Article body or excerpt.
        published_at: Publication timestamp; Pydantic coerces ISO 8601 strings.
    """

    title: str
    url: HttpUrl
    source: str
    score: float = Field(ge=0.0, le=1.0)
    content: str
    published_at: datetime

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


class RAGContextChunk(BaseModel):
    """Context chunk returned by the RAG Agent from ChromaDB.

    Attributes:
        text: The retrieved chunk content.
        source: Document identifier, file path, or ChromaDB doc ID (plain string).
        metadata: Arbitrary key-value pairs associated with the chunk.
    """

    text: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "LangChain saw 300% growth in GitHub stars over Q1 2024...",
                "source": "chroma://scout-corpus/doc-42",
                "metadata": {"chunk_index": 2, "token_count": 128},
            }
        }
    )


class AnalystHypothesis(BaseModel):
    """Hypothesis emitted by a single analyst agent after critic refinement.

    Attributes:
        persona: Analyst persona name, e.g. "vc_analyst", "developer_analyst", "journalist".
        confidence_score: Confidence level in [0.0, 1.0].
        evidence: Supporting evidence points.
        counter_evidence: Counter-points or risks.
        reasoning: Step-by-step reasoning narrative.
        hypothesis_text: The final hypothesis statement.
    """

    persona: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    reasoning: str
    hypothesis_text: str

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


class SynthesisReport(BaseModel):
    """Final synthesis report merging all analyst hypotheses, produced by the Synthesis Agent.

    Attributes:
        query: The original user query that triggered the scout run.
        hypotheses: List of analyst hypotheses; at least one is required.
        top_repos: Top repositories identified during the scout run.
        generated_at: UTC timestamp of report generation; defaults to now.
    """

    query: str
    hypotheses: list[AnalystHypothesis] = Field(min_length=1)
    top_repos: list[RepoData] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
