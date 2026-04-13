"""Developer Analyst Agent — Analysis Layer (Person 2: Sindhuja)

Pragmatic engineer analyst that evaluates production-readiness based on ecosystem
maturity, adoption curve, contributor health, and job market signals.
"""
from google.adk.agents import LlmAgent, LoopAgent

from src.models.schemas import AnalystHypothesis
from src.agents.analysis._prompts import GEMINI_MODEL, RETRY_CONFIG, DEV_GENERATOR_PROMPT, DEV_CRITIC_PROMPT

dev_generator = LlmAgent(
    name="DevAnalystGenerator",
    model=GEMINI_MODEL,
    instruction=DEV_GENERATOR_PROMPT,
    output_schema=AnalystHypothesis,
    output_key="dev_draft_output",
    generate_content_config=RETRY_CONFIG,
)

dev_critic = LlmAgent(
    name="DevCritic",
    model=GEMINI_MODEL,
    instruction=DEV_CRITIC_PROMPT,
    output_key="dev_critic_output",
    generate_content_config=RETRY_CONFIG,
)

dev_analyst_loop = LoopAgent(
    name="DevAnalystLoop",
    sub_agents=[dev_generator, dev_critic],
    max_iterations=2,
)

__all__ = ["dev_generator", "dev_critic", "dev_analyst_loop"]
