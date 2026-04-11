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

__all__ = ["analysis_layer"]
