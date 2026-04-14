"""Tech News + Tavily Agent — Collection Layer (Person 1: Raghav)

Tech-focused sources: dev.to (developer articles), Reddit (r/programming + friends),
Product Hunt (new tech launches), plus persona-targeted Tavily searches.
"""
import asyncio
import logging
import os
import re
from urllib.parse import urlparse

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

_USER_AGENT = "better-call-scout/0.1 (tech scout research bot)"
_REDDIT_SUBS = "programming+MachineLearning+webdev+devops+rust+golang"


def _slugify(query: str) -> str:
    """Lowercase, strip non-alphanumerics, collapse whitespace to dashes."""
    s = re.sub(r"[^a-z0-9\s-]", "", query.lower()).strip()
    return re.sub(r"\s+", "-", s)


def _ingest_items(items: list[dict], source_type: str) -> None:
    """Chunk items' content and upsert into ChromaDB with source_type metadata."""
    docs, metadatas, ids = [], [], []
    for it in items:
        url = it.get("url", "")
        title = it.get("title", "")
        content = it.get("content") or title
        for i, chunk in enumerate(chunk_text(content)):
            docs.append(chunk)
            metadatas.append({
                "source_url": url,
                "title": title,
                "chunk_index": i,
                "source_type": source_type,
            })
            ids.append(_generate_doc_id(url, i))
    if docs:
        ingest_documents(docs, metadatas, ids)


async def fetch_devto_articles(query: str, limit: int = 30) -> dict:
    """Fetch top dev.to articles for a topic via the public articles API.

    Slugifies the query into a tag filter; falls back to top articles if the
    tag yields no hits. Ingests article descriptions into the vector DB.

    Args:
        query: Topic keyword (e.g. "rust wasm").
        limit: Max articles to return.

    Returns:
        Dict with 'articles' key — list of dicts with title, url, content,
        score (positive_reactions_count), published_date, by.
    """
    tag = _slugify(query).split("-")[0]

    def _fetch(url: str) -> list[dict]:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    logger.info("Fetching dev.to articles | tag=%r", tag)
    try:
        raw = await asyncio.to_thread(
            _fetch,
            f"https://dev.to/api/articles?tag={tag}&per_page={limit}&top=7",
        )
        if not raw:
            raw = await asyncio.to_thread(
                _fetch, f"https://dev.to/api/articles?per_page={limit}&top=7"
            )
    except Exception as e:
        logger.warning("dev.to fetch failed: %s", e)
        return {"articles": []}

    articles = [
        {
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "content": f"[devto] {a.get('description', '') or a.get('title', '')}",
            "score": a.get("positive_reactions_count", 0),
            "published_date": a.get("published_at"),
            "by": (a.get("user") or {}).get("username", ""),
        }
        for a in raw
        if a.get("url")
    ]
    await asyncio.to_thread(_ingest_items, articles, "devto")
    logger.info("dev.to fetch complete: %d articles", len(articles))
    return {"articles": articles}


async def fetch_reddit_posts(query: str, limit: int = 30) -> dict:
    """Search Reddit tech subreddits for a query via the public JSON API.

    Uses a multi-subreddit search across r/programming, r/MachineLearning,
    r/webdev, r/devops, r/rust, r/golang sorted by top over the past month.

    Args:
        query: Search query string.
        limit: Max posts to return.

    Returns:
        Dict with 'posts' key — list of dicts with title, url, content
        (selftext), score (ups), published_date, by (author).
    """

    def _fetch() -> dict:
        resp = requests.get(
            f"https://www.reddit.com/r/{_REDDIT_SUBS}/search.json",
            params={
                "q": query,
                "restrict_sr": "true",
                "sort": "top",
                "t": "month",
                "limit": limit,
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    logger.info("Fetching Reddit posts | query=%r", query)
    try:
        raw = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.warning("Reddit fetch failed: %s", e)
        return {"posts": []}

    children = (raw.get("data") or {}).get("children", [])
    posts = []
    for c in children:
        d = c.get("data", {})
        permalink = d.get("permalink", "")
        url = d.get("url") or f"https://www.reddit.com{permalink}"
        selftext = d.get("selftext", "") or d.get("title", "")
        posts.append({
            "title": d.get("title", ""),
            "url": url,
            "content": f"[reddit r/{d.get('subreddit', '')}] {selftext}",
            "score": d.get("ups", 0),
            "published_date": d.get("created_utc"),
            "by": d.get("author", ""),
        })
    await asyncio.to_thread(_ingest_items, posts, "reddit")
    logger.info("Reddit fetch complete: %d posts", len(posts))
    return {"posts": posts}


async def fetch_producthunt_posts(query: str, limit: int = 20) -> dict:
    """Search Product Hunt launches matching a topic via the GraphQL v2 API.

    Requires PRODUCT_HUNT_TOKEN env var (developer token from
    https://api.producthunt.com/v2/oauth/applications). Returns empty list if
    token missing.

    Args:
        query: Topic to search for.
        limit: Max posts to return.

    Returns:
        Dict with 'posts' key — list of dicts with title, url, content,
        score (votesCount), published_date, by (maker).
    """
    token = os.environ.get("PRODUCT_HUNT_TOKEN")
    if not token:
        logger.warning("Product Hunt: PRODUCT_HUNT_TOKEN not set — skipping")
        return {"posts": []}

    gql_query = """
    query ($first: Int!) {
      posts(first: $first, order: RANKING) {
        edges {
          node {
            name
            tagline
            description
            url
            votesCount
            createdAt
            website
          }
        }
      }
    }
    """
    # Product Hunt v2 doesn't expose free-text search in the posts query;
    # we fetch top-ranked recent posts and pass all to the LLM for relevance filtering.

    def _fetch() -> dict:
        resp = requests.post(
            "https://api.producthunt.com/v2/api/graphql",
            json={"query": gql_query, "variables": {"first": 50}},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": _USER_AGENT,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    logger.info("Fetching Product Hunt posts | query=%r", query)
    try:
        raw = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.warning("Product Hunt fetch failed: %s", e)
        return {"posts": []}

    edges = (((raw.get("data") or {}).get("posts") or {}).get("edges")) or []
    posts = []
    for edge in edges:
        node = edge.get("node", {})
        posts.append({
            "title": node.get("name", ""),
            "url": node.get("website") or node.get("url", ""),
            "content": f"[producthunt] {node.get('tagline', '')} — {node.get('description', '')}",
            "score": node.get("votesCount", 0),
            "published_date": node.get("createdAt"),
            "by": "",
        })
        if len(posts) >= limit:
            break
    await asyncio.to_thread(_ingest_items, posts, "producthunt")
    logger.info("Product Hunt fetch complete: %d posts", len(posts))
    return {"posts": posts}


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
        logger.warning("Tavily [%s]: TAVILY_API_KEY not set — skipping", angle)
        return []
    try:
        client = AsyncTavilyClient(api_key)
        logger.info("Tavily [%s]: sending request | query=%r", angle, query)
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
            domain = urlparse(url).netloc.removeprefix("www.")
            results.append({
                "title": title,
                "url": url,
                "content": f"[{angle} | {domain}] {content}",
                "score": r.get("score", 0.0),
                "published_date": r.get("published_date"),
                "angle": angle,
                "domain": domain,
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

1. Call fetch_devto_articles with the query to get developer articles from dev.to.
2. Call fetch_reddit_posts with the query to get discussions from tech subreddits.
3. Call fetch_producthunt_posts with the query to get recent Product Hunt launches.
4. Call search_tavily_vc with the query to get funding, market size, and M&A signals.
5. Call search_tavily_dev with the query to get production adoption, hiring, and benchmark signals.
6. Call search_tavily_journalist with the query to get press coverage, community sentiment, and hype analysis.

Merge all results into a single JSON array of news items.
Each item must have: title, url, content (which includes a source/angle prefix), score, published_date.
Return the merged array as JSON in the output.""",
    description="Fetches dev.to, Reddit, Product Hunt, and persona-targeted Tavily results for a topic.",
    tools=[
        fetch_devto_articles,
        fetch_reddit_posts,
        fetch_producthunt_posts,
        search_tavily_vc,
        search_tavily_dev,
        search_tavily_journalist,
    ],
    output_key="hn_tavily_results",
    generate_content_config=_RETRY_CONFIG,
)
