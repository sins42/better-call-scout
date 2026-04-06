"""Journalist Analyst Agent — Analysis Layer (Person 2: Sindhuja)

Skeptical tech media analyst that surfaces the real story vs hype, evaluating
HN sentiment, media coverage density, narrative arcs, and incumbent threats.
"""
from google.adk.agents import LlmAgent, LoopAgent

from src.models.schemas import AnalystHypothesis
from src.agents.analysis._prompts import GEMINI_MODEL, JOURNALIST_GENERATOR_PROMPT, JOURNALIST_CRITIC_PROMPT

journalist_generator = LlmAgent(
    name="JournalistGenerator",
    model=GEMINI_MODEL,
    instruction=JOURNALIST_GENERATOR_PROMPT,
    output_schema=AnalystHypothesis,
    output_key="journalist_draft_output",
)

journalist_critic = LlmAgent(
    name="JournalistCritic",
    model=GEMINI_MODEL,
    instruction=JOURNALIST_CRITIC_PROMPT,
    output_key="journalist_critic_output",
)

journalist_loop = LoopAgent(
    name="JournalistLoop",
    sub_agents=[journalist_generator, journalist_critic],
    max_iterations=2,
)

__all__ = ["journalist_generator", "journalist_critic", "journalist_loop"]
