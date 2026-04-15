"""RAG Ingestion Pipeline — Collection Layer (Person 1: Raghav)

Chunk text, embed with MiniLM, store in ChromaDB.
Provides deterministic IDs to prevent duplicate documents on re-ingestion.
"""
import hashlib
import logging
import threading

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

CHROMA_PATH = "./chroma_data"
COLLECTION_NAME = "scout-corpus"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_lock = threading.Lock()


def get_chroma_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection with MiniLM embeddings.

    Uses a module-level singleton to prevent concurrent-thread race conditions
    during ChromaDB's Rust backend initialization.

    Returns:
        A ChromaDB Collection configured with SentenceTransformerEmbeddingFunction
        using the all-MiniLM-L6-v2 model.
    """
    global _client, _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:
            logger.debug("Initializing ChromaDB client at %s", CHROMA_PATH)
            _client = chromadb.PersistentClient(path=CHROMA_PATH)
            embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            _collection = _client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_fn,
            )
            logger.debug("ChromaDB collection %r ready (%d docs)", COLLECTION_NAME, _collection.count())
    return _collection


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


def ingest_documents(documents: list[str], metadatas: list[dict], ids: list[str]) -> int:
    """Add documents to the ChromaDB collection.

    Args:
        documents: List of text strings to embed and store.
        metadatas: List of metadata dicts, one per document.
        ids: List of deterministic document IDs, one per document.

    Returns:
        Number of documents added.
    """
    logger.info("ChromaDB upsert: %d chunks (source=%s)", len(documents), metadatas[0].get("source_type", "?") if metadatas else "?")
    collection = get_chroma_collection()
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("ChromaDB upsert complete: %d chunks stored (total in collection: %d)", len(documents), collection.count())
    return len(documents)


