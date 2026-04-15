"""Guardrail Agent (Person 1: Raghav)

Lightweight query classifier that blocks non-technical queries before they
enter the expensive scout pipeline. Uses a direct Gemini call (not a full
ADK SequentialAgent) to keep latency minimal.
"""
from __future__ import annotations

import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT = """\
You are a query classifier for a VC/startup technology scout tool.
Your job is to decide whether a user query is about a technology, software tool,
programming language, framework, developer ecosystem, or startup/tech product domain.

Examples of ALLOWED queries:
- "WebAssembly runtimes"
- "LLM inference frameworks"
- "Rust async web frameworks"
- "open source vector databases"
- "edge computing platforms for IoT"
- "developer tools for Kubernetes"

Examples of REJECTED queries (non-technical / out of scope):
- "What is the capital of France?"
- "Give me a chocolate cake recipe"
- "Who won the 2024 US election?"
- "Write me a poem about the ocean"
- "What is the best diet to lose weight?"
- "Help me with my homework"

Respond with exactly one word: ALLOWED or REJECTED.
Do NOT explain your reasoning.

Query: {query}"""


class QueryRejectedError(ValueError):
    """Raised when a query is classified as non-technical by the guardrail."""


async def check_query(query: str) -> None:
    """Classify a query and raise QueryRejectedError if it is non-technical.

    Args:
        query: The user's raw query string (already stripped/truncated).

    Raises:
        QueryRejectedError: If the query is classified as non-technical.
        Exception: Re-raised on unexpected Gemini API failures (pipeline
            should treat these as transient errors, not permanent rejections).
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )

    prompt = _CLASSIFY_PROMPT.format(query=query)

    logger.info("guardrail: classifying query=%r", query)
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=5,
                temperature=0.0,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(initial_delay=1, attempts=2),
                ),
            ),
        )
        verdict = response.text.strip().upper()
    except Exception:
        # On unexpected API failure, log and allow the query through rather than
        # blocking the user on a guardrail outage.
        logger.exception("guardrail: classification failed — allowing query through")
        return

    logger.info("guardrail: verdict=%s query=%r", verdict, query)
    if verdict != "ALLOWED":
        raise QueryRejectedError(
            f"Query '{query}' is not about a technology or startup domain. "
            "Please enter a tech topic (e.g. 'LLM inference frameworks', "
            "'Rust async runtimes', 'open source vector databases')."
        )
