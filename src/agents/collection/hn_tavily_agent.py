"""HN + Tavily Agent — Collection Layer (Person 1: Raghav)

HN Firebase API for top/best stories.
Tavily search with persona-targeted queries for richer, analyst-specific signals.
"""
import asyncio
import logging
import os

import requests
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from tavily import AsyncTavilyClient

_RETRY_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(initial_delay=2, attempts=3),
    ),
)

logger = logging.getLogger(__name__)

from src.models.schemas import NewsItem  # noqa: F401 — type reference only
from src.rag.ingestion import _generate_doc_id, chunk_text, ingest_documents

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
_DEFAULT_HN_LIMIT = 30


async def fetch_hn_top_stories(limit: int = 30) -> dict:
    """Fetch top HackerNews stories with details via the Firebase API.

    Fetches story IDs from the HN top-stories endpoint, then concurrently
    retrieves individual story details using asyncio.gather. Stories without
    a URL fall back to the HN item URL.

    Args:
        limit: Maximum number of stories to fetch. Defaults to 30.

    Returns:
        Dictionary with 'stories' key containing a list of story dicts.
        Each dict has keys: title, url, score, time, by.
    """

    def _fetch_ids() -> list[int]:
        resp = requests.get(f"{HN_API_BASE}/topstories.json", timeout=30)
        resp.raise_for_status()
        return resp.json()[:limit]

    logger.info("Fetching HN top %d story IDs", limit)
    story_ids = await asyncio.to_thread(_fetch_ids)
    logger.info("Fetching details for %d HN stories", len(story_ids))

    async def _fetch_story(sid: int) -> dict | None:
        def _do_fetch(story_id: int = sid) -> dict:
            for attempt in range(3):
                try:
                    resp = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=30)
                    resp.raise_for_status()
                    return resp.json()
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt == 2:
                        raise
                    import time
                    time.sleep(0.5 * (attempt + 1))

        try:
            story = await asyncio.to_thread(_do_fetch)
        except Exception as e:
            logger.warning("Failed to fetch HN story %d after retries: %s", sid, e)
            return None
        if story and story.get("type") == "story":
            return {
                "title": story.get("title", ""),
                "url": story.get(
                    "url", f"https://news.ycombinator.com/item?id={sid}"
                ),
                "score": story.get("score", 0),
                "time": story.get("time", 0),
                "by": story.get("by", ""),
            }
        return None

    story_results = await asyncio.gather(*[_fetch_story(sid) for sid in story_ids])
    stories = [s for s in story_results if s is not None]
    logger.info("HN fetch complete: %d/%d stories retrieved", len(stories), len(story_ids))
    return {"stories": stories}


async def _tavily_search(query: str, angle: str, max_results: int = 8) -> list[dict]:
    """Run a single Tavily general web search and tag results with an angle label.

    Args:
        query: The search query string.
        angle: Label describing the signal type (e.g. 'vc_funding', 'dev_hiring').
        max_results: Number of results to request from Tavily.

    Returns:
        List of result dicts with keys: title, url, content, score, published_date, angle.
        Returns empty list on API error or missing key.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        client = AsyncTavilyClient(api_key)
        response = await client.search(
            query=query,
            topic="general",
            max_results=max_results,
            search_depth="advanced",
        )
        results = []
        docs, metadatas, ids = [], [], []
        for r in response.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            content = r.get("content", "")
            results.append({
                "title": title,
                "url": url,
                "content": f"[{angle}] {content}",
                "score": r.get("score", 0.0),
                "published_date": r.get("published_date"),
                "angle": angle,
            })
            for i, chunk in enumerate(chunk_text(content or title)):
                docs.append(chunk)
                metadatas.append({"source_url": url, "title": title, "chunk_index": i, "source_type": "tavily"})
                ids.append(_generate_doc_id(url, i))

        if docs:
            await asyncio.to_thread(ingest_documents, docs, metadatas, ids)

        logger.info("Tavily [%s] returned %d results for %r", angle, len(results), query)
        return results
    except Exception as e:
        logger.warning("Tavily [%s] failed for %r: %s", angle, query, e)
        return []


async def search_tavily_vc(query: str) -> dict:
    """Search for VC-relevant signals: funding rounds, market size, and M&A activity.

    Fires three parallel Tavily queries targeting investment and market intelligence.

    Args:
        query: The technology topic to research.

    Returns:
        Dictionary with 'results' key containing merged news item dicts tagged
        with angle labels: 'vc_funding', 'vc_market', 'vc_deals'.
    """
    logger.info("Tavily VC search for %r", query)
    batches = await asyncio.gather(
        _tavily_search(f"{query} funding round Series investment 2024 2025", "vc_funding"),
        _tavily_search(f"{query} market size TAM total addressable market competitors", "vc_market"),
        _tavily_search(f"{query} acquisition partnership enterprise adoption", "vc_deals"),
    )
    results = [item for batch in batches for item in batch]
    return {"results": results}


async def search_tavily_dev(query: str) -> dict:
    """Search for developer-relevant signals: production adoption, hiring, and benchmarks.

    Fires three parallel Tavily queries targeting engineering and ecosystem health signals.

    Args:
        query: The technology topic to research.

    Returns:
        Dictionary with 'results' key containing merged news item dicts tagged
        with angle labels: 'dev_adoption', 'dev_hiring', 'dev_benchmark'.
    """
    logger.info("Tavily Dev search for %r", query)
    batches = await asyncio.gather(
        _tavily_search(f"{query} production case study deployment real world", "dev_adoption"),
        _tavily_search(f"{query} software engineer job posting hiring", "dev_hiring"),
        _tavily_search(f"{query} benchmark performance comparison alternative", "dev_benchmark"),
    )
    results = [item for batch in batches for item in batch]
    return {"results": results}


async def search_tavily_journalist(query: str) -> dict:
    """Search for journalist-relevant signals: press coverage, community sentiment, hype analysis.

    Fires three parallel Tavily queries targeting media and community reaction signals.

    Args:
        query: The technology topic to research.

    Returns:
        Dictionary with 'results' key containing merged news item dicts tagged
        with angle labels: 'press_coverage', 'community_sentiment', 'hype_analysis'.
    """
    logger.info("Tavily Journalist search for %r", query)
    batches = await asyncio.gather(
        _tavily_search(f"{query} site:techcrunch.com OR site:wired.com OR site:theverge.com OR site:venturebeat.com", "press_coverage"),
        _tavily_search(f"{query} community reaction criticism problems issues reddit", "community_sentiment"),
        _tavily_search(f"{query} overhyped hype vs reality honest review", "hype_analysis"),
    )
    results = [item for batch in batches for item in batch]
    return {"results": results}


hn_tavily_agent = LlmAgent(
    name="hn_tavily_agent",
    model="gemini-2.0-flash",
    instruction="""You are a tech intelligence scout. Given a topic query from session state key 'query':

1. Call fetch_hn_top_stories to get trending Hacker News stories.
2. Call search_tavily_vc with the query to get funding, market size, and M&A signals.
3. Call search_tavily_dev with the query to get production adoption, hiring, and benchmark signals.
4. Call search_tavily_journalist with the query to get press coverage, community sentiment, and hype analysis.

Merge all results (HN stories + all Tavily results) into a single JSON array of news items.
Each item must have: title, url, content (which includes an [angle] prefix), score, published_date.
Return the merged array as JSON in the output.""",
    description="Fetches HN stories and persona-targeted Tavily web searches for a given topic.",
    tools=[fetch_hn_top_stories, search_tavily_vc, search_tavily_dev, search_tavily_journalist],
    output_key="hn_tavily_results",
    generate_content_config=_RETRY_CONFIG,
)
