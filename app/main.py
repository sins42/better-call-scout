"""FastAPI Application Entry Point (Person 2: Sindhuja)

Exposes the ADK scout pipeline via REST API and serves the single-page HTML frontend.

Endpoints:
    POST /run         — Run the full pipeline; returns session_id + SynthesisReport JSON
    GET  /stream      — SSE endpoint for pipeline progress (GET only; EventSource limitation)
    GET  /download/{artifact}  — Download artifact by name (session_id query param required)
    GET  /            — Serve the single-page HTML frontend
"""
from __future__ import annotations

import asyncio
from dotenv import load_dotenv
load_dotenv()
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from collections import defaultdict

from src.orchestrator import generate_artifacts, run_pipeline
from src.models.schemas import SynthesisReport
from src.rag.ingestion import get_chroma_collection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting up — Better Call Scout v1.0.0")
    logger.info("Server ready")
    yield
    logger.info("Server shutting down")


app = FastAPI(title="Better Call Scout", version="1.0.0", lifespan=lifespan)

# In-memory artifact store: {session_id: {artifact_name: bytes | str}}
# Keyed by session_id UUID to prevent concurrent request contamination (RESEARCH.md Pitfall 7).
_artifact_store: dict[str, dict[str, bytes | str]] = {}

# Mount static files for any assets (CSS/JS if extracted from HTML in future)
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


class RunRequest(BaseModel):
    """Request body for POST /run."""

    query: str


@app.post("/run")
async def run_scout(req: RunRequest) -> dict:
    """Run the full scout pipeline for the given query.

    Args:
        req: RunRequest with query string. Max length enforced: 500 chars.

    Returns:
        JSON dict with session_id (str) and report (SynthesisReport as JSON dict).
        session_id must be passed as ?session_id= query param to /download endpoints.

    Raises:
        HTTPException 400: If query is empty or exceeds 500 characters.
        HTTPException 500: If pipeline fails.
    """
    # Input validation (ASVS L1 input length — RESEARCH.md T-04-01-01)
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query must not exceed 500 characters")

    session_id = str(uuid.uuid4())
    logger.info("POST /run — request received | session_id=%s query=%r", session_id, query)

    try:
        # Add 120s timeout to prevent event-loop starvation (RESEARCH.md T-04-01-02)
        report: SynthesisReport = await asyncio.wait_for(
            run_pipeline(query),
            timeout=300.0,
        )
    except asyncio.TimeoutError:
        logger.error("Pipeline timed out for session_id=%s", session_id)
        raise HTTPException(status_code=504, detail="Pipeline timed out after 120 seconds")
    except Exception as exc:
        logger.exception("Pipeline failed for session_id=%s", session_id)
        raise HTTPException(status_code=500, detail=str(exc))

    # Generate all artifacts and store keyed by session_id
    logger.info("POST /run — generating artifacts | session_id=%s", session_id)
    artifacts = await generate_artifacts(report)
    _artifact_store[session_id] = artifacts

    logger.info("POST /run — response sent | session_id=%s", session_id)
    # Serialize with mode="json" to coerce HttpUrl → str (RESEARCH.md Pitfall 5)
    return {
        "session_id": session_id,
        "report": report.model_dump(mode="json"),
    }


@app.get("/stream")
async def stream_progress(request: Request, query: str) -> EventSourceResponse:
    """Stream pipeline progress events via Server-Sent Events.

    IMPORTANT: EventSource only supports GET (browser standard).
    Query is passed as URL query param ?query=<encoded>.

    SSE events emitted (event name: data):
        collection_started: "Collection started"
        collection_complete: "Collection complete"
        critic_started: "Critic started"
        critic_complete: "Critic complete"
        analysis_started: "Analysis started"
        analysis_complete: "Analysis complete"
        synthesis_started: "Synthesis started"
        synthesis_complete: JSON string of SynthesisReport (via model_dump_json)
        error_event: error description string

    Args:
        request: FastAPI Request (used for disconnect detection).
        query: The technology topic query (URL-decoded by FastAPI).

    Returns:
        EventSourceResponse streaming SSE events.
    """
    query = query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query must not exceed 500 characters")

    logger.info("GET /stream — SSE connection opened | query=%r", query)

    async def generator() -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def progress_cb(stage: str, status: str) -> None:
            event_name = f"{stage}_{status}"  # e.g. "collection_started"
            await queue.put({"event": event_name, "data": f"{stage.capitalize()} {status}"})

        async def run() -> None:
            try:
                report = await asyncio.wait_for(
                    run_pipeline(query, progress_cb),
                    timeout=300.0,
                )
                # Store artifacts for download after SSE stream completes
                session_id = str(uuid.uuid4())
                logger.info("GET /stream — pipeline complete, generating artifacts | session_id=%s", session_id)
                artifacts = await generate_artifacts(report)
                _artifact_store[session_id] = artifacts
                logger.info("GET /stream — sending complete event | session_id=%s", session_id)
                await queue.put({
                    "event": "complete",
                    "data": report.model_dump_json(),
                })
                # Also emit the session_id so the client can construct download URLs
                await queue.put({"event": "session_id", "data": session_id})
            except asyncio.TimeoutError:
                await queue.put({"event": "error_event", "data": "Pipeline timed out after 120 seconds"})
            except Exception as exc:
                logger.exception("SSE pipeline failed for query=%r", query)
                await queue.put({"event": "error_event", "data": str(exc)})
            finally:
                await queue.put(None)  # sentinel — end of stream

        asyncio.create_task(run())

        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected for query=%r", query)
                break
            item = await queue.get()
            if item is None:
                break
            yield item

    return EventSourceResponse(generator())


@app.get("/download/{artifact}")
async def download_artifact(artifact: str, session_id: str) -> Response:
    """Download a pipeline artifact by name.

    Artifact names: "scout_report.md", "top_repos.csv",
                    "chart_1.png", "chart_2.png", "chart_3.png", "chart_4.png"

    Args:
        artifact: Artifact filename to download.
        session_id: UUID returned by POST /run or SSE session_id event.

    Returns:
        Response with appropriate Content-Type and Content-Disposition headers.

    Raises:
        HTTPException 400: If artifact name is not in the allowed list.
        HTTPException 404: If session_id not found or artifact not in store.
    """
    # Allowlist validation prevents path traversal (ASVS L1)
    allowed = {
        "scout_report.md", "top_repos.csv",
        "chart_1.png", "chart_2.png", "chart_3.png", "chart_4.png",
    }
    if artifact not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown artifact '{artifact}'. Allowed: {sorted(allowed)}",
        )

    store = _artifact_store.get(session_id, {})
    data = store.get(artifact)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{artifact}' not found for session_id '{session_id}'. Run the pipeline first.",
        )

    media_types: dict[str, str] = {
        "scout_report.md": "text/markdown; charset=utf-8",
        "top_repos.csv": "text/csv; charset=utf-8",
    }
    if artifact.endswith(".png"):
        content = data if isinstance(data, bytes) else data.encode()
        return Response(
            content=content,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename={artifact}"},
        )
    mt = media_types.get(artifact, "application/octet-stream")
    content = data.encode() if isinstance(data, str) else data
    return Response(
        content=content,
        media_type=mt,
        headers={"Content-Disposition": f"attachment; filename={artifact}"},
    )


@app.get("/api/chroma/stats")
async def chroma_stats() -> dict:
    """Return aggregated stats about the ChromaDB corpus for the browse page.

    Returns:
        JSON dict with total_chunks, total_documents, source_types breakdown,
        and a list of documents with per-document chunk counts.
    """
    logger.info("GET /api/chroma/stats — request received")
    try:
        collection = get_chroma_collection()
        data = collection.get(include=["metadatas"])
    except Exception as exc:
        logger.exception("GET /api/chroma/stats — ChromaDB error")
        raise HTTPException(status_code=503, detail=f"ChromaDB unavailable: {exc}")

    metadatas = data.get("metadatas", []) or []
    total_chunks = len(metadatas)

    source_types: dict[str, int] = defaultdict(int)
    docs_accum: dict[tuple[str, str], dict] = {}
    for md in metadatas:
        if not isinstance(md, dict):
            continue
        src_type = md.get("source_type", "unknown")
        source_types[src_type] += 1

        url = md.get("source_url", "")
        title = md.get("title", "") or url or "(untitled)"
        key = (url, title)
        entry = docs_accum.get(key)
        if entry is None:
            docs_accum[key] = {
                "title": title,
                "source_url": url,
                "source_type": src_type,
                "chunk_count": 1,
            }
        else:
            entry["chunk_count"] += 1

    documents = sorted(docs_accum.values(), key=lambda d: d["chunk_count"], reverse=True)

    logger.info(
        "GET /api/chroma/stats — response sent | %d chunks, %d documents, %d source types",
        total_chunks, len(documents), len(source_types),
    )
    return {
        "total_chunks": total_chunks,
        "total_documents": len(documents),
        "source_types": dict(source_types),
        "documents": documents,
    }


@app.get("/browse", response_class=HTMLResponse)
async def browse() -> HTMLResponse:
    """Serve the vector DB browse page.

    Returns:
        HTMLResponse reading app/static/browse.html from disk.
    """
    logger.info("GET /browse — request received")
    html_path = _static_dir / "browse.html"
    if not html_path.exists():
        raise HTTPException(status_code=503, detail="Browse page missing")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the single-page HTML frontend.

    Returns:
        HTMLResponse reading app/static/index.html from disk.
    """
    html_path = _static_dir / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=503, detail="Frontend not yet built — index.html missing")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
