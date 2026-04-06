"""RAG Ingestion Pipeline — Collection Layer (Person 1: Raghav)

Fetch HN stories, chunk text, embed with MiniLM, store in ChromaDB.
Provides deterministic IDs to prevent duplicate documents on re-ingestion.
"""
import asyncio
import hashlib

import chromadb
import requests
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = "./chroma_data"
COLLECTION_NAME = "scout-corpus"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
_DEFAULT_STORY_LIMIT = 50


def get_chroma_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection with MiniLM embeddings.

    Returns:
        A ChromaDB Collection configured with SentenceTransformerEmbeddingFunction
        using the all-MiniLM-L6-v2 model.
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into fixed-size chunks with overlap.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum character length per chunk.
        overlap: Number of characters to overlap between consecutive chunks.

    Returns:
        List of non-empty string chunks. Returns empty list for empty input.
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def _generate_doc_id(source_url: str, chunk_index: int) -> str:
    """Generate a deterministic document ID from source URL and chunk index.

    Uses SHA-256 to produce a stable 16-character hex ID. Deterministic IDs
    prevent duplicate documents on re-ingestion (Pitfall 5 from research).

    Args:
        source_url: The source URL of the document.
        chunk_index: Index of the chunk within the document.

    Returns:
        A 16-character hex string ID.
    """
    return hashlib.sha256(f"{source_url}:{chunk_index}".encode()).hexdigest()[:16]


async def fetch_hn_stories_for_ingestion(limit: int = _DEFAULT_STORY_LIMIT) -> list[dict]:
    """Fetch top HN stories for RAG corpus ingestion.

    Fetches story IDs from the HN Firebase API, then concurrently retrieves
    individual story details.

    Args:
        limit: Maximum number of stories to fetch. Defaults to 50.

    Returns:
        List of story dicts with keys: title, url, text, time.
    """

    def _fetch_ids() -> list[int]:
        resp = requests.get(f"{HN_API_BASE}/topstories.json", timeout=30)
        resp.raise_for_status()
        return resp.json()[:limit]

    story_ids = await asyncio.to_thread(_fetch_ids)

    async def _fetch_single_story(sid: int) -> dict | None:
        def _do_fetch():
            resp = requests.get(f"{HN_API_BASE}/item/{sid}.json", timeout=30)
            resp.raise_for_status()
            return resp.json()

        story = await asyncio.to_thread(_do_fetch)
        if not story or story.get("type") != "story":
            return None

        title = story.get("title", "")
        url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
        body_text = story.get("text", "")
        combined_text = f"{title}. {body_text}".strip(". ")

        return {
            "title": title,
            "url": url,
            "text": combined_text or title,
            "time": story.get("time", 0),
        }

    tasks = [_fetch_single_story(sid) for sid in story_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    stories = []
    for r in results:
        if isinstance(r, dict):
            stories.append(r)

    return stories


def ingest_documents(documents: list[str], metadatas: list[dict], ids: list[str]) -> int:
    """Add documents to the ChromaDB collection.

    Args:
        documents: List of text strings to embed and store.
        metadatas: List of metadata dicts, one per document.
        ids: List of deterministic document IDs, one per document.

    Returns:
        Number of documents added.
    """
    collection = get_chroma_collection()
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return len(documents)


async def ingest_hn_stories(limit: int = _DEFAULT_STORY_LIMIT) -> int:
    """Fetch HN stories, chunk, and store in ChromaDB with deterministic IDs.

    Fetches top HN stories, splits each story's text into fixed-size chunks,
    generates deterministic IDs to avoid duplicate ingestion, and stores all
    chunks in the ChromaDB collection.

    Args:
        limit: Maximum number of HN stories to ingest. Defaults to 50.

    Returns:
        Total number of document chunks ingested.
    """
    stories = await fetch_hn_stories_for_ingestion(limit)

    all_documents: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    for story in stories:
        text = story.get("text", story.get("title", ""))
        url = story.get("url", "")
        title = story.get("title", "")

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = _generate_doc_id(url, i)
            all_documents.append(chunk)
            all_metadatas.append(
                {
                    "source_url": url,
                    "title": title,
                    "chunk_index": i,
                    "source_type": "hackernews",
                }
            )
            all_ids.append(doc_id)

    if not all_documents:
        return 0

    return ingest_documents(all_documents, all_metadatas, all_ids)
