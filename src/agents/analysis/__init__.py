"""Analysis Layer — three parallel analyst pipelines.

Each analyst runs its own generator-critic LoopAgent (max_iterations=2, per D-05).
All three run in parallel via ParallelAgent (ANAL-04).
"""
from google.adk.agents import ParallelAgent

from src.agents.analysis.vc_analyst import vc_analyst_loop
from src.agents.analysis.developer_analyst import dev_analyst_loop
from src.agents.analysis.journalist_analyst import journalist_loop

analysis_layer = ParallelAgent(
    name="AnalysisLayer",
    sub_agents=[vc_analyst_loop, dev_analyst_loop, journalist_loop],
)

# Mapping from short key to the state keys written by each analyst loop.
# Used by the orchestrator to seed initial state and by the fallback assembler.
PERSONA_STATE_KEYS: dict[str, tuple[str, str]] = {
    "vc":         ("vc_draft_output",         "vc_critic_output"),
    "dev":        ("dev_draft_output",         "dev_critic_output"),
    "journalist": ("journalist_draft_output",  "journalist_critic_output"),
}

# Maps short persona key → the persona string stored in AnalystHypothesis.persona
PERSONA_HYPOTHESIS_NAME: dict[str, str] = {
    "vc":         "vc_analyst",
    "dev":        "developer_analyst",
    "journalist": "journalist",
}

__all__ = [
    "analysis_layer",
    "vc_analyst_loop",
    "dev_analyst_loop",
    "journalist_loop",
    "PERSONA_STATE_KEYS",
    "PERSONA_HYPOTHESIS_NAME",
]
