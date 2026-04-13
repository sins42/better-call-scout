"""RAG Agent — Collection Layer (Person 1: Raghav)

Queries ChromaDB corpus (pre-embedded HN stories, RSS feeds, domain context).
Provides retrieval tool for analyst agents.
"""
import logging

from google.adk.agents.llm_agent import LlmAgent

from src.rag.retrieval import async_query_corpus
from src.models.schemas import RAGContextChunk  # noqa: F401 — type reference only

logger = logging.getLogger(__name__)


async def query_rag_corpus(query: str, n_results: int = 10) -> dict:
    """Query the pre-indexed RAG corpus for relevant context chunks.

    Calls async_query_corpus to retrieve semantically similar content from
    the ChromaDB collection of HN stories and tech news.

    Args:
        query: The search topic or question to retrieve context for.
        n_results: Maximum number of chunks to return. Defaults to 10.

    Returns:
        Dictionary with 'chunks' key containing a list of context chunk dicts.
        Each chunk has keys: text (str), source (str), metadata (dict).
    """
    logger.info("RAG query: %r n_results=%d", query, n_results)
    chunks = await async_query_corpus(query, n_results)
    logger.info("RAG returned %d chunks for query=%r", len(chunks), query)
    return {"chunks": chunks}


rag_agent = LlmAgent(
    name="rag_agent",
    model="gemini-2.0-flash",
    instruction="""You are a knowledge retrieval agent. Given a topic query,
    use the query_rag_corpus tool to find relevant context from the
    pre-indexed corpus of HN stories and tech news.
    Return the retrieved context chunks as JSON.""",
    description="Retrieves relevant context from the pre-indexed RAG corpus.",
    tools=[query_rag_corpus],
    output_key="rag_results",
)
