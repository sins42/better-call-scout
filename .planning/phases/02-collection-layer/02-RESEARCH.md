# Phase 2: Collection Layer - Research

**Researched:** 2026-04-05
**Domain:** Google ADK agents, GitHub REST API, HN Firebase API, Tavily search, ChromaDB RAG pipeline
**Confidence:** HIGH

## Summary

Phase 2 implements four agents (GitHub, HN+Tavily, RAG, Critic) and a RAG ingestion pipeline. Each collection agent is an ADK `LlmAgent` wrapping async Python tool functions registered as `FunctionTool`s. The three collection agents run concurrently via ADK's `ParallelAgent`, and their outputs flow through a Critic Agent that applies heuristic filtering with LLM escalation for borderline repos. The data contracts (`RepoData`, `NewsItem`, `RAGContextChunk`) are already implemented in `src/models/schemas.py` from Phase 1.

The ADK patterns are well-documented: `ParallelAgent` for fan-out, `output_key` for state passing between agents, and `{state_key}` template syntax in downstream agent instructions. The critical implementation challenges are: (1) GitHub's search API rate limit of 30 requests/minute for authenticated users, requiring batched calls; (2) the stargazers endpoint returns paginated data needing multiple calls per repo for velocity calculation; (3) GitHub stats endpoints return 202 on cache miss, requiring retry logic; and (4) Tavily's 1,000/month free tier requiring usage monitoring and HN-only fallback.

**Primary recommendation:** Build each agent as an `LlmAgent` with async Python tool functions, use `output_key` to store results in session state, compose with `ParallelAgent` for concurrent collection, and `SequentialAgent` to chain collection into critic filtering. Keep all API call logic in pure async Python functions -- the LLM's role is to interpret the query and invoke the right tools, not to make API calls directly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Each collection agent is an ADK `Agent` instance wrapping async Python tool functions -- not plain async functions, not full LLM-driven tool-calling. API call logic lives in regular Python async functions registered as `FunctionTool`s.
- **D-02:** The orchestrator runs all three collection agents in parallel using ADK's `ParallelAgent` (declarative fan-out, not `asyncio.gather`).
- **D-03:** GitHub Agent fetches 50-100 repos per query (medium pool -- 1 search page, well within rate limits).
- **D-04:** Minimal API-side filtering at query time. The GitHub Agent fetches broadly; the Critic Agent owns all quality decisions.
- **D-05:** Hybrid filtering -- heuristic rules handle clear passes and clear fails; Gemini (via ADK) reviews borderline repos only.
- **D-06:** Borderline threshold: repos with commits between 5-20, contributors between 1-3, or age < 30 days escalate to LLM review. Repos outside these ranges decided by heuristics alone.
- **D-07:** Heuristic signals: `is_fork`, commit count (last 30d), contributor count, repo age from creation date. Forks are always rejected by heuristic.
- **D-08:** Ingestion runs at container startup -- `src/rag/ingestion.py` is called before Streamlit accepts requests.
- **D-09:** A background thread refreshes the corpus every 24 hours.

### Claude's Discretion
None specified -- all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COLL-01 | GitHub Agent searches repos by topic/language/stars via REST API | GitHub Search API `GET /search/repositories` with `topic:`, `language:`, `stars:` qualifiers; max 100 per page, 30 req/min authenticated |
| COLL-02 | GitHub Agent fetches star history for velocity calculation | `GET /repos/{owner}/{repo}/stargazers` with `Accept: application/vnd.github.star+json` header returns `starred_at` timestamps; paginated at 100/page |
| COLL-03 | GitHub Agent fetches commit activity, contributor stats, issue velocity | `GET /repos/{owner}/{repo}/stats/commit_activity` (weekly commits, last year), `/stats/contributors` (per-author stats), `/issues?state=open` for count |
| COLL-04 | HN + Tavily Agent fetches top/best HN stories via Firebase API | `https://hacker-news.firebaseio.com/v0/topstories.json` and `/beststories.json` return arrays of IDs; `/v0/item/{id}.json` for story details; no rate limit |
| COLL-05 | HN + Tavily Agent fetches founder bios, funding news, job postings via Tavily | `AsyncTavilyClient.search(query, topic="news", max_results=N)` returns `title`, `url`, `content`, `score`, `published_date` |
| COLL-06 | RAG ingestion pipeline: fetch HN stories + RSS, chunk, embed with MiniLM, store in ChromaDB | ChromaDB `PersistentClient` + `SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')`; `collection.add(documents, metadatas, ids)` |
| COLL-07 | RAG Agent queries ChromaDB and returns relevant context chunks | `collection.query(query_texts=[topic], n_results=N)` returns ids, documents, metadatas, distances |
| COLL-08 | All 3 collection agents run in parallel via ADK | `ParallelAgent(sub_agents=[github_agent, hn_tavily_agent, rag_agent])` with `output_key` on each sub-agent |
| COLL-09 | Critic Agent filters raw repo list | `LlmAgent` with heuristic Python tool functions for clear pass/fail + Gemini escalation for borderline repos per D-05/D-06/D-07 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.11**, type hints required on all public functions
- **Pydantic v2** for all data models -- use `model_validator` not `validator`
- **Async** for all ADK agent functions
- **Docstrings** on all classes and public methods (Google style)
- **snake_case** for files and functions, `PascalCase` for classes
- Never commit `.env` -- use `.env.example` for new vars
- Do not add Claude as co-author in commits
- Use `uv add` for dependencies, `uv run pytest` for tests
- Commit messages: `type(scope): description`

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-adk | >=0.1.0 (latest: 1.28.1) | Agent framework -- LlmAgent, ParallelAgent, SequentialAgent, FunctionTool | Project decision; native Gemini/Vertex AI support |
| google-cloud-aiplatform | >=1.60.0 | Vertex AI SDK for Gemini 2.0 Flash inference | Required for Gemini model access via ADK |
| requests | >=2.32.0 | HTTP client for GitHub REST API and HN Firebase API | Already in pyproject.toml; synchronous but wrapped in async via `asyncio.to_thread` |
| tavily-python | >=0.3.0 (latest: 0.7.23) | Tavily search SDK with `AsyncTavilyClient` | Already in pyproject.toml; provides async search natively |
| chromadb | >=0.5.0 (latest: 1.5.5) | Embedded vector store for RAG corpus | Already in pyproject.toml; `PersistentClient` for disk persistence |
| sentence-transformers | >=3.0.0 (latest: 5.3.0) | Local embedding model (all-MiniLM-L6-v2, 384-dim) | Already in pyproject.toml; no API dependency, free |
| pydantic | >=2.7.0 | Data contracts -- `RepoData`, `NewsItem`, `RAGContextChunk` | Already implemented in Phase 1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | >=1.0.0 | Load `.env` vars (GITHUB_TOKEN, TAVILY_API_KEY, GOOGLE_CLOUD_PROJECT) | At module import time |
| asyncio (stdlib) | 3.11 | `asyncio.to_thread()` for wrapping sync `requests` calls | GitHub and HN API calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` + `asyncio.to_thread` | `httpx` (async native) | httpx is cleaner for async but `requests` is already a dependency; avoid adding packages |
| `ParallelAgent` | `asyncio.gather` | Decision D-02 locks in ParallelAgent for course rubric demonstration |

**Installation:**
All dependencies already in `pyproject.toml`. No new packages needed:
```bash
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  agents/
    collection/
      __init__.py
      github_agent.py       # LlmAgent + async tool functions for GitHub REST API
      hn_tavily_agent.py     # LlmAgent + async tool functions for HN Firebase + Tavily
      rag_agent.py           # LlmAgent + async tool function wrapping retrieval.py
    critic_agent.py          # LlmAgent + heuristic filter tools + LLM escalation
  rag/
    ingestion.py             # Fetch HN/RSS -> chunk -> embed -> ChromaDB
    retrieval.py             # Query interface over ChromaDB (reusable by RAG agent + analysts)
  models/
    schemas.py               # Already implemented: RepoData, NewsItem, RAGContextChunk
```

### Pattern 1: ADK Agent with FunctionTool
**What:** Each collection agent is an `LlmAgent` with async Python functions registered as tools. The LLM interprets the user query and decides which tools to call; the tools execute the actual API logic.
**When to use:** All four agents in this phase.
**Example:**
```python
# Source: https://adk.dev/tools-custom/function-tools/ + https://adk.dev/agents/llm-agents/
from google.adk.agents.llm_agent import LlmAgent

async def search_github_repos(query: str, language: str = "", min_stars: int = 10) -> dict:
    """Search GitHub repositories by topic, language, and minimum stars.

    Args:
        query: Search query string (topic or keyword).
        language: Filter by primary programming language.
        min_stars: Minimum star count threshold.

    Returns:
        Dictionary with 'repos' key containing list of repo data dicts.
    """
    # API call logic here -- runs in asyncio.to_thread for requests
    ...
    return {"repos": repo_list}

github_agent = LlmAgent(
    name="github_agent",
    model="gemini-2.0-flash",
    instruction="""You are a GitHub repository scout. Given a topic query,
    use the search_github_repos tool to find relevant repositories,
    then use fetch_repo_details to get star velocity, commit activity,
    contributor stats, and issue counts for each repo.""",
    description="Searches GitHub for trending repositories on a given topic.",
    tools=[search_github_repos, fetch_repo_details],
    output_key="github_results",
)
```

### Pattern 2: ParallelAgent Fan-Out with output_key
**What:** Three collection agents run concurrently; each stores results in session state via `output_key`. A downstream agent reads these keys.
**When to use:** COLL-08 parallel execution.
**Example:**
```python
# Source: https://adk.dev/agents/workflow-agents/parallel-agents/
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

collection_parallel = ParallelAgent(
    name="collection_parallel",
    sub_agents=[github_agent, hn_tavily_agent, rag_agent],
    description="Runs all three collection agents concurrently.",
)

# Critic reads state keys set by parallel agents
critic_agent = LlmAgent(
    name="critic_agent",
    model="gemini-2.0-flash",
    instruction="""You filter repositories. Read the GitHub results from
    {github_results}. Apply heuristic filtering using the filter tools.
    For borderline repos, evaluate quality and relevance.""",
    tools=[heuristic_filter, ...],
    output_key="filtered_repos",
)

# Full collection pipeline: parallel collect -> critic filter
collection_pipeline = SequentialAgent(
    name="collection_pipeline",
    sub_agents=[collection_parallel, critic_agent],
    description="Collect data in parallel, then filter through critic.",
)
```

### Pattern 3: Async Tool Wrapping Sync HTTP Calls
**What:** GitHub and HN use `requests` (sync). Wrap with `asyncio.to_thread` so they don't block the event loop.
**When to use:** All `requests`-based API calls.
**Example:**
```python
import asyncio
import requests

async def _github_get(url: str, headers: dict) -> dict:
    """Make a GET request to GitHub API in a thread pool."""
    def _do_request():
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    return await asyncio.to_thread(_do_request)
```

### Pattern 4: Critic Hybrid Filtering
**What:** Heuristic rules in Python tool functions handle clear pass/fail. Borderline repos are presented to the LLM for judgment.
**When to use:** COLL-09 critic filtering.
**Example:**
```python
async def heuristic_filter(repos_json: str) -> dict:
    """Apply heuristic rules to filter repositories.

    Rejects: forks, repos with 0 commits in 30d, repos with 0 contributors.
    Passes: repos with >20 commits, >3 contributors, age >30 days.
    Borderline: everything else -- returned for LLM review.

    Args:
        repos_json: JSON string of repository data list.

    Returns:
        Dictionary with 'passed', 'rejected', and 'borderline' lists.
    """
    repos = json.loads(repos_json)
    passed, rejected, borderline = [], [], []
    for repo in repos:
        if repo.get("is_fork", False):
            rejected.append(repo)
        elif repo["commits"] > 20 and repo["contributors"] > 3:
            passed.append(repo)
        elif repo["commits"] < 5 or repo["contributors"] < 1:
            rejected.append(repo)
        else:
            borderline.append(repo)
    return {"passed": passed, "rejected": rejected, "borderline": borderline}
```

### Anti-Patterns to Avoid
- **Making the LLM call APIs directly:** The LLM should invoke Python tool functions, not construct HTTP requests. Tool functions encapsulate all API logic.
- **Sharing mutable state between parallel agents:** ParallelAgent branches are independent. Use `output_key` to write to state, not shared Python objects.
- **Ignoring GitHub 202 responses:** Stats endpoints return 202 when cache is cold. Must retry after a brief delay (1-2 seconds).
- **Paginating stargazers for all repos:** With 50-100 repos, paginating stargazers for each is expensive. Approximate star_velocity from the search result's star count + stats/commit_activity trends instead, or limit stargazer pagination to top repos only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel agent execution | Custom asyncio.gather orchestration | ADK `ParallelAgent` | Decision D-02; course rubric requires ADK demonstration |
| Vector embedding | Custom embedding code | ChromaDB's `SentenceTransformerEmbeddingFunction` | Built-in integration; handles batching and dimension alignment |
| Text chunking | Custom chunker | Simple fixed-size chunking with overlap | HN stories and RSS items are naturally short; complex chunking is overkill |
| Tavily search | Raw HTTP to Tavily API | `AsyncTavilyClient` from `tavily-python` | SDK handles auth, retries, response parsing |
| Environment variable loading | os.environ parsing | `python-dotenv` with `load_dotenv()` | Already in stack; consistent with project convention |

**Key insight:** The ADK framework provides the orchestration primitives (ParallelAgent, SequentialAgent, LlmAgent, FunctionTool). The implementation work is in the tool functions that call external APIs and in the data transformation to Pydantic models.

## Common Pitfalls

### Pitfall 1: GitHub Stats 202 Response
**What goes wrong:** `GET /repos/{owner}/{repo}/stats/commit_activity` returns HTTP 202 with empty body when stats aren't cached. Code treats this as an error or parses empty JSON.
**Why it happens:** GitHub computes stats lazily and triggers a background job on first request.
**How to avoid:** Check for 202 status code. Retry after 1-2 seconds (up to 3 retries). If still 202, fall back to zero values for that repo.
**Warning signs:** Empty or null commit/contributor data for repos you know are active.

### Pitfall 2: GitHub Search API Rate Limit (30 req/min)
**What goes wrong:** Search API has a separate, stricter rate limit than the general API (30/min vs 5,000/hour). Making too many search queries in rapid succession returns 403.
**Why it happens:** The search rate limit is per-minute, not per-hour.
**How to avoid:** Batch searches. Decision D-03 says 50-100 repos per query (1 search page). With `per_page=100`, one search call suffices per query. Detail fetching uses the general API limit.
**Warning signs:** HTTP 403 with `X-RateLimit-Remaining: 0` on search endpoints.

### Pitfall 3: Stargazer Pagination Cost
**What goes wrong:** Fetching all stargazers with timestamps for 50-100 repos is extremely expensive (potentially thousands of API calls).
**Why it happens:** Popular repos have tens of thousands of stargazers; paginated at 100/page.
**How to avoid:** Use a sampling strategy -- fetch only the first and last page of stargazers to estimate 30-day velocity. Or use the `/stats/code_frequency` endpoint as a proxy signal combined with total star count delta.
**Warning signs:** Rate limit exhaustion, extremely slow agent execution.

### Pitfall 4: Tavily Free Tier Exhaustion
**What goes wrong:** 1,000 searches/month. If each pipeline run uses 5-10 Tavily calls, you can exhaust the quota in ~100-200 runs.
**Why it happens:** Each news/funding/job query is a separate API call.
**How to avoid:** Track usage. Implement HN-only fallback when nearing quota. Batch related queries into single calls with broader keywords.
**Warning signs:** HTTP 429 from Tavily; or unexpected empty results.

### Pitfall 5: ChromaDB Collection Name Collision
**What goes wrong:** Multiple ingestion runs create duplicate documents or overwrite the collection.
**Why it happens:** `get_or_create_collection` reuses existing; `create_collection` fails if exists.
**How to avoid:** Use `get_or_create_collection`. Use deterministic IDs (e.g., hash of source URL) so re-ingestion updates rather than duplicates.
**Warning signs:** Duplicate chunks in query results; growing corpus size without new sources.

### Pitfall 6: ADK output_key Contains Raw LLM Text
**What goes wrong:** `output_key` stores the LLM's final text response as a string, not structured data. Downstream agent gets a string, not a list of RepoData.
**Why it happens:** `output_key` saves the agent's text response verbatim.
**How to avoid:** Have the tool functions return structured data (dict/JSON). The LLM summarizes it as text in its response. For structured passing, use tool return values stored in state directly via callbacks, or have the downstream agent parse the JSON from the state string.
**Warning signs:** Downstream agent can't parse the state variable; gets natural language instead of JSON.

## Code Examples

### GitHub Search API Call
```python
# Source: https://docs.github.com/en/rest/search/search
import asyncio
import os
import requests

GITHUB_API_BASE = "https://api.github.com"

async def search_github_repos(query: str, language: str = "", min_stars: int = 10) -> dict:
    """Search GitHub repositories by topic and optional filters.

    Args:
        query: Topic or keyword to search for.
        language: Optional programming language filter.
        min_stars: Minimum star count.

    Returns:
        Dictionary with 'repos' list of basic repo info dicts.
    """
    q_parts = [query]
    if language:
        q_parts.append(f"language:{language}")
    if min_stars > 0:
        q_parts.append(f"stars:>={min_stars}")
    q = "+".join(q_parts)

    headers = {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API_BASE}/search/repositories?q={q}&sort=stars&order=desc&per_page=100"

    def _fetch():
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    data = await asyncio.to_thread(_fetch)
    repos = []
    for item in data.get("items", []):
        repos.append({
            "name": item["full_name"],
            "url": item["html_url"],
            "stars": item["stargazers_count"],
            "language": item.get("language"),
            "topics": item.get("topics", []),
            "is_fork": item.get("fork", False),
            "created_at": item["created_at"],
        })
    return {"repos": repos}
```

### Star Velocity Calculation
```python
# Source: https://docs.github.com/en/rest/activity/starring
from datetime import datetime, timedelta, timezone

async def fetch_star_velocity(owner: str, repo: str) -> dict:
    """Fetch approximate star velocity for a repo (stars gained in last 30 days / total).

    Args:
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Dictionary with star_velocity float clamped to [-1.0, 1.0].
    """
    headers = {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.star+json",  # Required for starred_at timestamps
    }
    # Fetch first page to get recent stars
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/stargazers?per_page=100&page=1"
    data = await asyncio.to_thread(lambda: requests.get(url, headers=headers, timeout=30).json())

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_stars = sum(
        1 for s in data
        if isinstance(s, dict) and datetime.fromisoformat(s.get("starred_at", "").replace("Z", "+00:00")) > cutoff
    )

    # Get total stars from repo endpoint
    repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    headers_basic = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}
    repo_data = await asyncio.to_thread(
        lambda: requests.get(repo_url, headers=headers_basic, timeout=30).json()
    )
    total_stars = repo_data.get("stargazers_count", 1)

    velocity = recent_stars / max(total_stars, 1)
    velocity = max(-1.0, min(1.0, velocity))  # Clamp to [-1.0, 1.0]
    return {"star_velocity": velocity, "stars_last_30d": recent_stars, "total_stars": total_stars}
```

### HN Firebase API Call
```python
# Source: https://github.com/HackerNews/API
import aiohttp  # or use requests + asyncio.to_thread

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

async def fetch_hn_top_stories(limit: int = 30) -> dict:
    """Fetch top HN stories with details.

    Args:
        limit: Maximum number of stories to fetch.

    Returns:
        Dictionary with 'stories' list of story dicts.
    """
    # Fetch story IDs
    def _fetch_ids():
        resp = requests.get(f"{HN_API_BASE}/topstories.json", timeout=30)
        return resp.json()[:limit]

    story_ids = await asyncio.to_thread(_fetch_ids)

    # Fetch individual stories
    stories = []
    for sid in story_ids:
        def _fetch_story(id=sid):
            resp = requests.get(f"{HN_API_BASE}/item/{id}.json", timeout=30)
            return resp.json()
        story = await asyncio.to_thread(_fetch_story)
        if story and story.get("type") == "story":
            stories.append({
                "title": story.get("title", ""),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "score": story.get("score", 0),
                "time": story.get("time", 0),
                "by": story.get("by", ""),
            })
    return {"stories": stories}
```

### Tavily Async Search
```python
# Source: https://docs.tavily.com/sdk/python/reference
from tavily import AsyncTavilyClient

async def search_tavily_news(query: str, max_results: int = 5) -> dict:
    """Search for news, funding, and founder info via Tavily.

    Args:
        query: Search query for news/funding/jobs.
        max_results: Number of results to return (0-20).

    Returns:
        Dictionary with 'results' list of news item dicts.
    """
    client = AsyncTavilyClient(os.environ["TAVILY_API_KEY"])
    response = await client.search(
        query=query,
        topic="news",
        max_results=max_results,
        search_depth="basic",
    )
    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "score": r.get("score", 0.0),
            "published_date": r.get("published_date"),
        })
    return {"results": results}
```

### ChromaDB Ingestion and Retrieval
```python
# Source: https://docs.trychroma.com/docs/embeddings/embedding-functions
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = "./chroma_data"
COLLECTION_NAME = "scout-corpus"

def get_chroma_collection():
    """Get or create the ChromaDB collection with MiniLM embeddings."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

def ingest_documents(documents: list[str], metadatas: list[dict], ids: list[str]):
    """Add documents to the ChromaDB collection."""
    collection = get_chroma_collection()
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

def query_corpus(query_text: str, n_results: int = 10) -> list[dict]:
    """Query the ChromaDB collection for relevant chunks."""
    collection = get_chroma_collection()
    results = collection.query(query_texts=[query_text], n_results=n_results)
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        chunks.append({
            "text": doc,
            "source": results["ids"][0][i],
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
        })
    return chunks
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ADK 0.x (early alpha) | ADK 1.x (stable) | 2025-2026 | Production-ready ParallelAgent, SequentialAgent, LoopAgent; stable API |
| ChromaDB 0.4.x | ChromaDB 1.5.x | 2025 | New API surface; `PersistentClient` is the standard; embedding functions unchanged |
| `tavily-python` 0.3.x | 0.7.x | 2025 | `AsyncTavilyClient` fully stable; new `crawl`, `map`, `extract` methods available |

**Deprecated/outdated:**
- `chromadb.Client()` (ephemeral) -- use `PersistentClient` for disk persistence
- Pydantic v1 `validator` decorator -- use `model_validator` / `field_validator` (already enforced by CLAUDE.md)

## Open Questions

1. **Star velocity approximation strategy**
   - What we know: Full stargazer pagination is too expensive for 50-100 repos. First page (100 most recent stargazers) gives recent activity but not a precise 30-day count.
   - What's unclear: Whether first-page sampling is accurate enough for the velocity formula.
   - Recommendation: Use first-page sampling for the initial implementation. If the first page's oldest `starred_at` is within 30 days, all 100 are recent; if not, proportionally estimate. This is good enough for a course project.

2. **ADK version compatibility**
   - What we know: `pyproject.toml` pins `>=0.1.0` but latest is 1.28.1. The API surface (LlmAgent, ParallelAgent, FunctionTool) is stable from 0.1.0 onwards.
   - What's unclear: Whether any breaking changes exist between 0.1.0 and 1.x for the specific features we use.
   - Recommendation: Keep the `>=0.1.0` pin for now; it will resolve to the latest. If issues arise, pin to a specific 1.x version.

3. **HN story fetching concurrency**
   - What we know: Fetching 30 individual HN stories sequentially is slow (30 HTTP requests).
   - What's unclear: Whether `asyncio.gather` on `asyncio.to_thread` calls is safe inside an ADK tool function.
   - Recommendation: Use `asyncio.gather` within the tool function to fetch HN stories concurrently. This is internal to the tool, not agent orchestration, so it doesn't conflict with ADK's ParallelAgent.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All code | Yes | 3.11.14 | -- |
| uv | Package management | Yes | 0.9.27 | -- |
| gcloud CLI | Vertex AI auth | Yes | 558.0.0 | -- |
| .env file | API keys | Yes | -- | -- |
| GITHUB_TOKEN | GitHub Agent | Assumed (in .env) | -- | Agent fails gracefully |
| TAVILY_API_KEY | HN+Tavily Agent | Assumed (in .env) | -- | HN-only fallback |
| GOOGLE_CLOUD_PROJECT | Gemini via Vertex AI | Assumed (in .env) | -- | Agent fails |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:**
- If TAVILY_API_KEY is missing or quota exhausted: fall back to HN Firebase API only (no funding/founder/job data).

## Sources

### Primary (HIGH confidence)
- [ADK Function Tools docs](https://adk.dev/tools-custom/function-tools/) -- FunctionTool creation, best practices
- [ADK Parallel Agents docs](https://adk.dev/agents/workflow-agents/parallel-agents/) -- ParallelAgent usage, full Python example with output_key
- [ADK LLM Agents docs](https://adk.dev/agents/llm-agents/) -- LlmAgent constructor, output_key, state variable substitution
- [ADK Multi-Agent Systems docs](https://adk.dev/agents/multi-agents/) -- State management, data passing patterns
- [GitHub REST API - Search](https://docs.github.com/en/rest/search/search) -- Search repos endpoint, rate limits (30/min)
- [GitHub REST API - Starring](https://docs.github.com/en/rest/activity/starring) -- Stargazers with timestamps
- [GitHub REST API - Statistics](https://docs.github.com/en/rest/metrics/statistics) -- Commit activity, contributors, 202 caching behavior
- [HackerNews API](https://github.com/HackerNews/API) -- Firebase endpoints, no rate limit
- [Tavily Python SDK Reference](https://docs.tavily.com/sdk/python/reference) -- AsyncTavilyClient, search parameters
- [ChromaDB Embedding Functions](https://docs.trychroma.com/docs/embeddings/embedding-functions) -- SentenceTransformerEmbeddingFunction

### Secondary (MEDIUM confidence)
- PyPI version checks (google-adk 1.28.1, tavily-python 0.7.23, chromadb 1.5.5, sentence-transformers 5.3.0) -- verified via `pip index versions`

### Tertiary (LOW confidence)
- None -- all findings verified with official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in pyproject.toml; versions verified against PyPI
- Architecture: HIGH -- ADK patterns verified against official docs; ParallelAgent + output_key + SequentialAgent is the documented approach
- API integration: HIGH -- all external API endpoints verified against official documentation
- Pitfalls: HIGH -- GitHub 202 caching, search rate limits, stargazer pagination costs all documented in official GitHub API docs

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable APIs, 30-day window)

**Reference documentation saved to:** `.reference/google-adk/` (gitignored)
