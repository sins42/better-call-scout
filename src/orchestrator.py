"""ADK Orchestrator (Shared: Raghav + Sindhuja)

Top-level agent that wires Collection -> Critic -> Analysis -> Synthesis flow.
Manages parallel execution of collection and analysis layers via Google ADK.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from dotenv import load_dotenv
load_dotenv()
from collections.abc import Awaitable, Callable
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Import pre-built composite agents.
# ADK 1.x enforces single-parent ownership: an agent can only be a sub-agent of
# one parent at a time. collection_pipeline already owns collection_parallel +
# critic_agent, and analysis_layer already owns the three analyst loops.
# We must reuse these existing composites rather than re-wrapping the leaf agents.
from src.agents.guardrail_agent import QueryRejectedError, check_query
from src.agents.collection import collection_pipeline  # collection_parallel + critic_agent
from src.agents.analysis import analysis_layer  # vc/dev/journalist analyst loops (ParallelAgent)
from src.agents.synthesis_agent import (
    build_synthesis_report_from_state,
    generate_scout_report_md,
    generate_top_repos_csv,
    synthesis_agent,
)
from src.models.schemas import RepoData, SynthesisReport
from src.visualization.charts import (
    category_heatmap,
    buzz_scatter,
    persona_score_bars,
    star_velocity_chart,
)

logger = logging.getLogger(__name__)

# ProgressCallback type: async callable receiving (stage: str, status: str)
ProgressCallback = Callable[[str, str], Awaitable[None]] | None

# Build the pipeline agent once at module level (NOT per request — InMemoryRunner
# initialization is expensive and per-request leaks sessions).
#
# Structure: collection_pipeline (CollectionLayer + CriticAgent) → AnalysisLayer → SynthesisAgent
# ADK enforces single-parent ownership so collection_pipeline is used as-is rather
# than decomposing it into separate CollectionLayer + critic_agent sub-agents.
pipeline_agent = SequentialAgent(
    name="ScoutPipeline",
    sub_agents=[collection_pipeline, analysis_layer, synthesis_agent],
)

_runner = InMemoryRunner(agent=pipeline_agent, app_name="better-call-scout")


async def run_pipeline(
    query: str,
    progress_cb: ProgressCallback = None,
) -> SynthesisReport:
    """Run the full scout pipeline end-to-end for a given query.

    Args:
        query: The user's technology topic query (e.g. "WebAssembly runtimes").
        progress_cb: Optional async callback receiving (stage, status) strings.
            Called at the start and completion of each pipeline stage.
            Stages: "collection", "critic", "analysis", "synthesis".

    Returns:
        SynthesisReport merging all three analyst hypotheses.

    Raises:
        ValueError: If any required analyst output key is missing from session state.
        Exception: Re-raised from ADK runner on pipeline failure.
    """
    # Enforce max query length (T-04-01-01: strip whitespace and cap at 500 chars)
    query = query.strip()
    if len(query) > 500:
        query = query[:500]

    # Guardrail: reject non-technical queries before launching the expensive pipeline.
    await check_query(query)

    # Use a unique user_id per request so sessions don't cross-contaminate (T-04-01-02).
    user_id = f"scout-{uuid.uuid4().hex[:8]}"

    async def _emit(stage: str, status: str) -> None:
        if progress_cb:
            await progress_cb(stage, status)

    logger.info("Pipeline started | user_id=%s query=%r", user_id, query)
    await _emit("collection", "started")
    logger.info("Stage: collection — started")

    # Seed session state with the query. Collection agents read "query" from state.
    # Analyst prompts read {repo_data_json}, {news_items_json}, {rag_chunks_json}.
    # These are seeded as empty lists — collection agents overwrite their output_key
    # values (github_results, hn_tavily_results, rag_results) in state during run.
    session = await _runner.session_service.create_session(
        app_name="better-call-scout",
        user_id=user_id,
        state={
            "query": query,
            "repo_data_json": json.dumps([]),
            "news_items_json": json.dumps([]),
            "rag_chunks_json": json.dumps([]),
            # Seed analyst loop state so first-iteration prompts don't raise KeyError
            "vc_draft_output": "",
            "vc_critic_output": "",
            "dev_draft_output": "",
            "dev_critic_output": "",
            "journalist_draft_output": "",
            "journalist_critic_output": "",
        },
    )

    message = types.Content(role="user", parts=[types.Part(text=query)])

    # Consume ADK events and emit progress at key stage transitions.
    # ADK event.author indicates which agent produced the event.
    # collection_pipeline wraps collection_parallel + critic_agent, so we track
    # progress at the sub-agent level: collection_parallel = collection done,
    # critic_agent = critic done, AnalysisLayer = analysis done, SynthesisAgent = synthesis done.
    _stage_map: dict[str, tuple[str, str]] = {
        "collection_parallel": ("collection", "complete"),
        "critic_agent": ("critic", "complete"),
        "AnalysisLayer": ("analysis", "complete"),
        "SynthesisAgent": ("synthesis", "complete"),
    }
    _started_stages: set[str] = {"collection"}  # collection already emitted above

    stage_start_map: dict[str, str] = {
        "critic_agent": "critic",
        "AnalysisLayer": "analysis",
        "SynthesisAgent": "synthesis",
    }

    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        author = getattr(event, "author", None)
        if author in stage_start_map and author not in _started_stages:
            stage = stage_start_map[author]
            logger.info("Stage: %s — started (agent=%s)", stage, author)
            await _emit(stage, "started")
            _started_stages.add(author)
        if author in _stage_map:
            stage, status = _stage_map[author]
            is_final = getattr(event, "is_final_response", None)
            if is_final is not None and (
                callable(is_final) and is_final() or not callable(is_final) and is_final
            ):
                logger.info("Stage: %s — %s (agent=%s)", stage, status, author)
                await _emit(stage, status)

    await _emit("synthesis", "complete")
    logger.info("Pipeline complete | query=%r", query)

    # Retrieve final session state and extract typed SynthesisReport.
    final_session = await _runner.session_service.get_session(
        app_name="better-call-scout",
        user_id=user_id,
        session_id=session.id,
    )

    # Prefer synthesis_agent structured output; fall back to manual assembly.
    synthesis_raw = final_session.state.get("synthesis_report")
    if synthesis_raw:
        try:
            if isinstance(synthesis_raw, dict):
                report = SynthesisReport.model_validate(synthesis_raw)
            elif isinstance(synthesis_raw, str):
                report = SynthesisReport.model_validate_json(synthesis_raw)
            else:
                report = synthesis_raw  # already a SynthesisReport instance
        except Exception as exc:
            logger.warning("synthesis_report parse failed (%s) — falling back to state assembly", exc)
            synthesis_raw = None  # trigger fallback below
    if not synthesis_raw:
        # Fallback: assemble from individual analyst output keys.
        repos_raw = final_session.state.get("github_results", "[]")
        if isinstance(repos_raw, str):
            repos_list = json.loads(repos_raw)
        else:
            repos_list = repos_raw if isinstance(repos_raw, list) else []
        repos = [RepoData.model_validate(r) for r in repos_list if isinstance(r, dict)]
        report = build_synthesis_report_from_state(final_session.state, query, repos)

    return report


async def generate_artifacts(report: SynthesisReport) -> dict[str, bytes | str]:
    """Generate all downloadable artifacts from a completed SynthesisReport.

    Runs chart generation in a thread pool to avoid blocking the async event loop
    (matplotlib is CPU-bound synchronous work — per RESEARCH.md Pitfall 3).

    Args:
        report: The completed SynthesisReport from run_pipeline.

    Returns:
        Dict mapping artifact name to bytes (PNG) or str (Markdown/CSV):
            "scout_report.md" -> str
            "top_repos.csv" -> str
            "chart_1.png" -> bytes  (star velocity)
            "chart_2.png" -> bytes  (category heatmap)
            "chart_3.png" -> bytes  (news buzz scatter)
            "chart_4.png" -> bytes  (persona scores)
    """
    logger.info("Generating artifacts: charts + report markdown + CSV")
    # Run all four chart functions in thread pool concurrently.
    chart_1, chart_2, chart_3, chart_4 = await asyncio.gather(
        asyncio.to_thread(star_velocity_chart, report),
        asyncio.to_thread(category_heatmap, report),
        asyncio.to_thread(buzz_scatter, report),
        asyncio.to_thread(persona_score_bars, report),
    )
    logger.info("Artifact generation complete")

    return {
        "scout_report.md": generate_scout_report_md(report),
        "top_repos.csv": generate_top_repos_csv(report),
        "chart_1.png": chart_1,
        "chart_2.png": chart_2,
        "chart_3.png": chart_3,
        "chart_4.png": chart_4,
    }


__all__ = ["run_pipeline", "generate_artifacts", "pipeline_agent", "QueryRejectedError"]
