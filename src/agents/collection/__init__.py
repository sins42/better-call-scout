"""Collection Layer — Agent Composition (Person 1: Raghav)

Wires three collection agents into a ParallelAgent for concurrent execution,
followed by the Critic Agent for filtering, via a SequentialAgent pipeline.
"""
import importlib

from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from src.agents.critic_agent import critic_agent

# Load submodules via importlib to keep sys.modules correct and avoid the
# package-attribute shadowing that occurs with `from pkg.sub import name`.
# `import pkg.sub as x` syntax resolves via getattr(parent_pkg, 'sub'), so
# setting a package attribute with the same name as a submodule shadows it.
# Using importlib.import_module + module-private refs avoids this entirely.
_github_mod = importlib.import_module("src.agents.collection.github_agent")
_hn_tavily_mod = importlib.import_module("src.agents.collection.hn_tavily_agent")
_rag_mod = importlib.import_module("src.agents.collection.rag_agent")

# Build ParallelAgent directly from module-private agent references.
# Do NOT assign github_agent/hn_tavily_agent/rag_agent as package attributes here
# — that would shadow the submodules when accessed via dotted import syntax.
collection_parallel = ParallelAgent(
    name="collection_parallel",
    sub_agents=[
        _github_mod.github_agent,
        _hn_tavily_mod.hn_tavily_agent,
        _rag_mod.rag_agent,
    ],
    description="Runs all three collection agents concurrently.",
)

collection_pipeline = SequentialAgent(
    name="collection_pipeline",
    sub_agents=[collection_parallel, critic_agent],
    description="Collect data in parallel, then filter through critic.",
)

# Public accessors via properties would shadow submodules; instead rely on
# __all__ to signal intent. Importers use `from ... import github_agent` which
# triggers a submodule import, returning the correct module object.
# Direct agent access: `from src.agents.collection.github_agent import github_agent`
github_agent = _github_mod.github_agent
rag_agent = _rag_mod.rag_agent

__all__ = [
    "github_agent",
    "hn_tavily_agent",
    "rag_agent",
    "collection_parallel",
    "collection_pipeline",
]
