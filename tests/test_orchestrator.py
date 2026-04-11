"""Tests for src/orchestrator.py — structural and offline only (no real LLM calls).

All tests mock the ADK runner so no Vertex AI credentials are required.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.schemas import AnalystHypothesis, RepoData, SynthesisReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_report() -> SynthesisReport:
    """Build a minimal valid SynthesisReport for test use."""
    hypothesis = AnalystHypothesis(
        persona="vc_analyst",
        confidence_score=0.78,
        evidence=["85k stars"],
        counter_evidence=[],
        reasoning="Strong velocity signal.",
        hypothesis_text="LangChain will dominate enterprise LLM tooling.",
    )
    repo = RepoData(
        name="langchain-ai/langchain",
        url="https://github.com/langchain-ai/langchain",
        stars=85000,
        star_velocity=0.42,
        commits=312,
        contributors=148,
        issues=520,
        topics=["llm"],
        language="Python",
    )
    return SynthesisReport(
        query="AI dev tools",
        hypotheses=[hypothesis],
        top_repos=[repo],
    )


# ---------------------------------------------------------------------------
# Test 1: run_pipeline is an async function with the correct signature
# ---------------------------------------------------------------------------

def test_run_pipeline_is_async() -> None:
    """run_pipeline must be an async coroutine function."""
    from src.orchestrator import run_pipeline

    assert inspect.iscoroutinefunction(run_pipeline), (
        "run_pipeline must be defined with 'async def'"
    )


def test_run_pipeline_signature() -> None:
    """run_pipeline must accept (query: str, progress_cb=None)."""
    from src.orchestrator import run_pipeline

    sig = inspect.signature(run_pipeline)
    params = list(sig.parameters.keys())
    assert "query" in params, "run_pipeline must have 'query' parameter"
    assert "progress_cb" in params, "run_pipeline must have 'progress_cb' parameter"

    # progress_cb should default to None
    assert sig.parameters["progress_cb"].default is None, (
        "progress_cb must default to None"
    )


# ---------------------------------------------------------------------------
# Test 2: pipeline_agent is a SequentialAgent with 4 sub-agents
# ---------------------------------------------------------------------------

def test_pipeline_agent_is_sequential_agent() -> None:
    """pipeline_agent must be a SequentialAgent."""
    from google.adk.agents import SequentialAgent

    from src.orchestrator import pipeline_agent

    assert isinstance(pipeline_agent, SequentialAgent), (
        f"pipeline_agent must be a SequentialAgent, got {type(pipeline_agent)}"
    )


def test_pipeline_agent_has_three_sub_agents() -> None:
    """pipeline_agent must have 3 sub-agents.

    ADK 1.x enforces single-parent ownership: agents already owned by
    collection_pipeline (collection_parallel + critic_agent) cannot be re-wrapped.
    The orchestrator uses collection_pipeline as a composite first sub-agent,
    giving 3 sub-agents: collection_pipeline, AnalysisLayer, SynthesisAgent.
    """
    from google.adk.agents import ParallelAgent, SequentialAgent

    from src.orchestrator import pipeline_agent

    assert len(pipeline_agent.sub_agents) == 3, (
        f"pipeline_agent must have 3 sub-agents, got {len(pipeline_agent.sub_agents)}"
    )

    # First sub-agent: collection_pipeline (SequentialAgent: collection_parallel + critic_agent)
    collection_pipeline_agent = pipeline_agent.sub_agents[0]
    assert isinstance(collection_pipeline_agent, SequentialAgent), (
        "First sub-agent must be a SequentialAgent (collection_pipeline)"
    )
    assert collection_pipeline_agent.name == "collection_pipeline"

    # Second sub-agent: AnalysisLayer (ParallelAgent)
    analysis = pipeline_agent.sub_agents[1]
    assert isinstance(analysis, ParallelAgent), (
        "Second sub-agent must be a ParallelAgent (AnalysisLayer)"
    )
    assert analysis.name == "AnalysisLayer"


def test_collection_pipeline_has_parallel_and_critic() -> None:
    """collection_pipeline must contain collection_parallel + critic_agent."""
    from src.orchestrator import pipeline_agent

    collection_pipeline_agent = pipeline_agent.sub_agents[0]
    names = [a.name for a in collection_pipeline_agent.sub_agents]
    assert len(collection_pipeline_agent.sub_agents) == 2, (
        "collection_pipeline must have 2 sub-agents"
    )
    assert names[0] == "collection_parallel", f"Expected collection_parallel, got {names[0]}"
    assert names[1] == "critic_agent", f"Expected critic_agent, got {names[1]}"


def test_collection_parallel_has_three_agents() -> None:
    """collection_parallel must contain github_agent, hn_tavily_agent, rag_agent."""
    from src.orchestrator import pipeline_agent

    collection_pipeline_agent = pipeline_agent.sub_agents[0]
    collection_parallel = collection_pipeline_agent.sub_agents[0]
    names = {a.name for a in collection_parallel.sub_agents}
    assert len(collection_parallel.sub_agents) == 3, (
        "collection_parallel must have 3 sub-agents"
    )
    assert names == {"github_agent", "hn_tavily_agent", "rag_agent"}, (
        f"collection_parallel sub-agent names mismatch: {names}"
    )


def test_analysis_layer_has_three_loops() -> None:
    """AnalysisLayer must contain the three analyst loops."""
    from src.orchestrator import pipeline_agent

    analysis_layer = pipeline_agent.sub_agents[1]
    assert len(analysis_layer.sub_agents) == 3, (
        "AnalysisLayer must have 3 sub-agents"
    )


# ---------------------------------------------------------------------------
# Test 3: generate_artifacts returns dict with all 6 expected keys
# ---------------------------------------------------------------------------

def test_generate_artifacts_returns_all_keys() -> None:
    """generate_artifacts must return dict with 6 expected artifact keys."""
    from src.orchestrator import generate_artifacts

    report = _make_minimal_report()
    # Run async function synchronously
    artifacts = asyncio.get_event_loop().run_until_complete(generate_artifacts(report))

    expected_keys = {
        "scout_report.md",
        "top_repos.csv",
        "chart_1.png",
        "chart_2.png",
        "chart_3.png",
        "chart_4.png",
    }
    assert set(artifacts.keys()) == expected_keys, (
        f"generate_artifacts must return keys {expected_keys}, got {set(artifacts.keys())}"
    )


def test_generate_artifacts_png_are_bytes() -> None:
    """Chart artifacts must be bytes (PNG data)."""
    from src.orchestrator import generate_artifacts

    report = _make_minimal_report()
    artifacts = asyncio.get_event_loop().run_until_complete(generate_artifacts(report))

    for key in ("chart_1.png", "chart_2.png", "chart_3.png", "chart_4.png"):
        assert isinstance(artifacts[key], bytes), (
            f"{key} must be bytes, got {type(artifacts[key])}"
        )
        # PNG files start with the PNG magic bytes
        assert artifacts[key][:4] == b"\x89PNG", (
            f"{key} must be a valid PNG file"
        )


def test_generate_artifacts_text_are_str() -> None:
    """Markdown and CSV artifacts must be str."""
    from src.orchestrator import generate_artifacts

    report = _make_minimal_report()
    artifacts = asyncio.get_event_loop().run_until_complete(generate_artifacts(report))

    assert isinstance(artifacts["scout_report.md"], str)
    assert isinstance(artifacts["top_repos.csv"], str)


# ---------------------------------------------------------------------------
# Test 4: Progress callback fires with stage/status pairs in order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_calls_progress_cb_ordered() -> None:
    """Progress callback must be called with ordered stage/status string pairs."""
    from src.models.schemas import SynthesisReport

    # We patch _runner at the module level to avoid any real ADK calls
    mock_report = _make_minimal_report()

    # Mock event with is_final_response returning True for each stage author
    def make_event(author: str) -> MagicMock:
        event = MagicMock()
        event.author = author
        event.is_final_response = MagicMock(return_value=True)
        return event

    events = [
        make_event("collection_parallel"),
        make_event("critic_agent"),
        make_event("AnalysisLayer"),
        make_event("SynthesisAgent"),
    ]

    # Build a mock async iterator for run_async
    async def mock_run_async(**kwargs):
        for event in events:
            yield event

    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    mock_session.state = {
        "synthesis_report": mock_report.model_dump(mode="json"),
    }

    mock_session_service = AsyncMock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service.get_session = AsyncMock(return_value=mock_session)

    mock_runner = MagicMock()
    mock_runner.session_service = mock_session_service
    mock_runner.run_async = mock_run_async

    calls: list[tuple[str, str]] = []

    async def progress_cb(stage: str, status: str) -> None:
        calls.append((stage, status))

    with patch("src.orchestrator._runner", mock_runner):
        result = await __import__("src.orchestrator", fromlist=["run_pipeline"]).run_pipeline(
            query="test query",
            progress_cb=progress_cb,
        )

    assert isinstance(result, SynthesisReport), (
        f"run_pipeline must return SynthesisReport, got {type(result)}"
    )

    # Verify progress_cb was called (at minimum started + complete for collection and synthesis)
    assert len(calls) >= 2, f"Expected at least 2 progress_cb calls, got {len(calls)}: {calls}"

    # First call must be collection started
    assert calls[0] == ("collection", "started"), (
        f"First progress call must be ('collection', 'started'), got {calls[0]}"
    )

    # Last call must be synthesis complete
    assert calls[-1] == ("synthesis", "complete"), (
        f"Last progress call must be ('synthesis', 'complete'), got {calls[-1]}"
    )


# ---------------------------------------------------------------------------
# Test 5: generate_artifacts is an async function
# ---------------------------------------------------------------------------

def test_generate_artifacts_is_async() -> None:
    """generate_artifacts must be an async coroutine function."""
    from src.orchestrator import generate_artifacts

    assert inspect.iscoroutinefunction(generate_artifacts), (
        "generate_artifacts must be defined with 'async def'"
    )


# ---------------------------------------------------------------------------
# Test 6: Import validation
# ---------------------------------------------------------------------------

def test_orchestrator_exports() -> None:
    """orchestrator module must export run_pipeline, generate_artifacts, pipeline_agent."""
    import src.orchestrator as orch

    assert hasattr(orch, "run_pipeline"), "orchestrator must export run_pipeline"
    assert hasattr(orch, "generate_artifacts"), "orchestrator must export generate_artifacts"
    assert hasattr(orch, "pipeline_agent"), "orchestrator must export pipeline_agent"
