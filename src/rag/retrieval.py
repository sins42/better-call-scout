"""RAG Retrieval — Collection Layer (Person 1: Raghav)

Query ChromaDB for relevant context given a search topic.
Used by analyst agents during the analysis layer.
"""
import asyncio

from src.rag.ingestion import get_chroma_collection


def query_corpus(query_text: str, n_results: int = 10) -> list[dict]:
    """Query the ChromaDB collection for relevant chunks.

    Transforms ChromaDB query results into a list of dicts matching the
    RAGContextChunk shape (text, source, metadata). Handles empty collections
    gracefully by returning an empty list.

    Args:
        query_text: The search query to embed and match against the corpus.
        n_results: Maximum number of results to return. Defaults to 10.

    Returns:
        List of dicts with keys:
            text (str): The retrieved chunk content.
            source (str): ChromaDB document ID.
            metadata (dict): Associated metadata (source_url, title, etc.).
    """
    collection = get_chroma_collection()
    results = collection.query(query_texts=[query_text], n_results=n_results)

    docs = results.get("documents", [[]])[0]
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    chunks = []
    for i, doc in enumerate(docs):
        chunks.append(
            {
                "text": doc,
                "source": ids[i] if i < len(ids) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
        )

    return chunks


async def async_query_corpus(query_text: str, n_results: int = 10) -> list[dict]:
    """Asynchronously query the ChromaDB corpus for relevant chunks.

    Wraps the synchronous query_corpus in asyncio.to_thread so it can be
    called from async ADK tool functions without blocking the event loop.

    Args:
        query_text: The search query to embed and match against the corpus.
        n_results: Maximum number of results to return. Defaults to 10.

    Returns:
        List of dicts with keys: text, source, metadata (same as query_corpus).
    """
    return await asyncio.to_thread(query_corpus, query_text, n_results)
