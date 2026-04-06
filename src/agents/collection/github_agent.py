"""GitHub Agent — Collection Layer (Person 1: Raghav)

Searches repos by topic/language/stars via GitHub REST API.
Fetches star history, commit activity, contributor stats, issue velocity.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import requests
from google.adk.agents.llm_agent import LlmAgent

from src.models.schemas import RepoData  # noqa: F401 — type reference only

GITHUB_API_BASE = "https://api.github.com"
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


async def _github_get(url: str, headers: dict) -> dict:
    """Make a GET request to the GitHub API in a thread pool.

    Args:
        url: Full GitHub API URL to fetch.
        headers: HTTP headers including Authorization and Accept.

    Returns:
        Parsed JSON response as a dict (or list cast to dict via caller).

    Raises:
        requests.HTTPError: If the response status is 4xx/5xx.
    """

    def _do_request():
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    return await asyncio.to_thread(_do_request)


async def _github_get_with_retry(
    url: str, headers: dict, max_retries: int = _MAX_RETRIES
) -> dict | None:
    """Make a GET request to a GitHub stats endpoint, retrying on 202 responses.

    GitHub statistics endpoints return HTTP 202 when stats are being computed
    (cache miss). This helper retries until a 200 is received or retries are
    exhausted.

    Args:
        url: Full GitHub API URL for a stats endpoint.
        headers: HTTP headers including Authorization.
        max_retries: Maximum number of retry attempts after a 202 response.

    Returns:
        Parsed JSON response, or None if all retries returned 202.
    """

    def _do_request():
        resp = requests.get(url, headers=headers, timeout=30)
        return resp

    for attempt in range(max_retries + 1):
        resp = await asyncio.to_thread(_do_request)
        if resp.status_code == 202:
            if attempt < max_retries:
                await asyncio.sleep(_RETRY_DELAY)
                continue
            return None
        resp.raise_for_status()
        return resp.json()

    return None


async def search_github_repos(
    query: str, language: str = "", min_stars: int = 10
) -> dict:
    """Search GitHub repositories by topic, language, and minimum stars.

    Fetches up to 100 repositories per query (1 page) sorted by star count.
    Returns basic repo information for downstream detail fetching.

    Args:
        query: Topic or keyword to search for (e.g., "machine learning").
        language: Optional programming language filter (e.g., "python").
        min_stars: Minimum star count threshold. Defaults to 10.

    Returns:
        Dictionary with 'repos' key containing a list of repo info dicts.
        Each dict has keys: name, url, stars, language, topics, is_fork, created_at.
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

    data = await _github_get(url, headers)
    repos = []
    for item in data.get("items", []):
        repos.append(
            {
                "name": item["full_name"],
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "language": item.get("language"),
                "topics": item.get("topics", []),
                "is_fork": item.get("fork", False),
                "created_at": item["created_at"],
            }
        )
    return {"repos": repos}


async def fetch_repo_details(owner: str, repo: str) -> dict:
    """Fetch detailed activity metrics for a single GitHub repository.

    Retrieves star velocity (30-day), commit count (30-day), contributor count,
    and open issue count. Uses retry logic for GitHub statistics endpoints that
    return HTTP 202 on cache miss.

    Args:
        owner: Repository owner username or organization name.
        repo: Repository name.

    Returns:
        Dictionary with keys:
            star_velocity (float): Clamped to [-1.0, 1.0].
            commits (int): Total commits in the last 30 days.
            contributors (int): Number of unique contributors.
            issues (int): Number of open issues.
    """
    auth_headers = {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }

    # --- Star velocity ---
    star_headers = {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.star+json",
    }
    stargazers_url = (
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}/stargazers?per_page=100&page=1"
    )
    stargazers_data = await _github_get(stargazers_url, star_headers)

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_stars = 0
    if isinstance(stargazers_data, list):
        for s in stargazers_data:
            if isinstance(s, dict) and s.get("starred_at"):
                try:
                    starred_at = datetime.fromisoformat(
                        s["starred_at"].replace("Z", "+00:00")
                    )
                    if starred_at > cutoff:
                        recent_stars += 1
                except (ValueError, TypeError):
                    pass

    # Get total stars from repo endpoint
    repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    repo_data = await _github_get(repo_url, auth_headers)
    total_stars = repo_data.get("stargazers_count", 1) if isinstance(repo_data, dict) else 1
    open_issues = repo_data.get("open_issues_count", 0) if isinstance(repo_data, dict) else 0

    velocity = recent_stars / max(total_stars, 1)
    star_velocity = max(-1.0, min(1.0, velocity))

    # --- Commit activity (30-day, last 4 weeks) ---
    commit_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/stats/commit_activity"
    commit_data = await _github_get_with_retry(commit_url, auth_headers)
    commits = 0
    if commit_data and isinstance(commit_data, list):
        for week in commit_data[-4:]:
            commits += week.get("total", 0)

    # --- Contributors ---
    contributors_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/stats/contributors"
    contributors_data = await _github_get_with_retry(contributors_url, auth_headers)
    contributors = len(contributors_data) if contributors_data else 0

    return {
        "star_velocity": star_velocity,
        "commits": commits,
        "contributors": contributors,
        "issues": open_issues,
    }


github_agent = LlmAgent(
    name="github_agent",
    model="gemini-2.0-flash",
    instruction="""You are a GitHub repository scout. Given a topic query,
    use the search_github_repos tool to find relevant repositories,
    then use fetch_repo_details to get star velocity, commit activity,
    contributor stats, and issue counts for each repo.
    Return the complete list of repos with all details as JSON.""",
    description="Searches GitHub for trending repositories on a given topic.",
    tools=[search_github_repos, fetch_repo_details],
    output_key="github_results",
)
