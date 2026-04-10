"""HN + Tavily Agent — Collection Layer (Person 1: Raghav)

HN Firebase API for top/best stories.
Tavily search for founder bios, funding news, job postings.
"""
import asyncio
import os

import requests
from google.adk.agents.llm_agent import LlmAgent
from tavily import AsyncTavilyClient

from src.models.schemas import NewsItem  # noqa: F401 — type reference only

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
_DEFAULT_HN_LIMIT = 30
_DEFAULT_TAVILY_RESULTS = 5


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

    story_ids = await asyncio.to_thread(_fetch_ids)

    async def _fetch_story(sid: int) -> dict | None:
        def _do_fetch(story_id: int = sid) -> dict:
            resp = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=30)
            resp.raise_for_status()
            return resp.json()

        story = await asyncio.to_thread(_do_fetch)
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
    return {"stories": stories}


async def search_tavily_news(query: str, max_results: int = 5) -> dict:
    """Search for news, funding, and founder information via Tavily.

    Gracefully degrades to an empty result set when TAVILY_API_KEY is absent
    or quota is exhausted, allowing the pipeline to continue with HN-only data.

    Args:
        query: Search query for news, funding rounds, or job postings.
        max_results: Number of results to return (1-20). Defaults to 5.

    Returns:
        Dictionary with 'results' key containing a list of news item dicts.
        Each dict has keys: title, url, content, score, published_date.
        Returns {"results": [], "fallback": True} when API key is missing.
        Returns {"results": [], "fallback": True, "error": str} on API errors.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"results": [], "fallback": True}

    try:
        client = AsyncTavilyClient(api_key)
        response = await client.search(
            query=query,
            topic="news",
            max_results=max_results,
            search_depth="basic",
        )
        results = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                    "published_date": r.get("published_date"),
                }
            )
        return {"results": results}
    except Exception as e:
        return {"results": [], "fallback": True, "error": str(e)}


hn_tavily_agent = LlmAgent(
    name="hn_tavily_agent",
    model="gemini-2.0-flash",
    instruction="""You are a tech news scout. Given a topic query,
    use fetch_hn_top_stories to get trending HackerNews stories,
    then use search_tavily_news to find founder bios, funding news,
    and job postings related to the topic.
    Return all collected news items as JSON.""",
    description="Fetches HN stories and Tavily news for a given topic.",
    tools=[fetch_hn_top_stories, search_tavily_news],
    output_key="hn_tavily_results",
)
