"""VC Analyst Agent — Analysis Layer (Person 2: Sindhuja)

Decisive, contrarian VC analyst that takes strong positions on breakout potential
based on star velocity, funding signals, market size, and competitive landscape.
"""
from google.adk.agents import LlmAgent, LoopAgent

from src.models.schemas import AnalystHypothesis
from src.agents.analysis._prompts import GEMINI_MODEL, VC_GENERATOR_PROMPT, VC_CRITIC_PROMPT

vc_generator = LlmAgent(
    name="VCAnalystGenerator",
    model=GEMINI_MODEL,
    instruction=VC_GENERATOR_PROMPT,
    output_schema=AnalystHypothesis,
    output_key="vc_draft_output",
)

vc_critic = LlmAgent(
    name="VCCritic",
    model=GEMINI_MODEL,
    instruction=VC_CRITIC_PROMPT,
    output_key="vc_critic_output",
    # No output_schema on critic — free-text challenge is correct here
)

vc_analyst_loop = LoopAgent(
    name="VCAnalystLoop",
    sub_agents=[vc_generator, vc_critic],
    max_iterations=2,
)

__all__ = ["vc_generator", "vc_critic", "vc_analyst_loop"]
