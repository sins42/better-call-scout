"""Critic Agent (Person 1: Raghav)

Filters raw repo list: removes forks, boilerplate, one-day spikes, spam repos.
Also used in generator-critic loop with analyst agents.
"""
import json
from datetime import datetime, timezone

from google.adk.agents.llm_agent import LlmAgent

from src.models.schemas import RepoData  # noqa: F401 — type reference only


async def heuristic_filter(repos_json: str) -> dict:
    """Apply heuristic rules to filter repositories into pass/reject/borderline buckets.

    Implements decision rules per D-05, D-06, D-07:
    - Always reject (heuristic): is_fork == True (forks never escalated to LLM, per D-07)
    - Always reject (heuristic): commits < 5 OR contributors < 1 (clear fail per D-06 lower bound)
    - Always pass (heuristic): commits > 20 AND contributors > 3 AND age > 30 days (clear pass per D-06 upper bound)
    - Borderline (escalate to LLM): repos with commits between 5-20, contributors between 1-3,
      or age < 30 days (per D-06)

    Args:
        repos_json: JSON string representing a list of repository data dicts.
            Each dict should include: is_fork, commits, contributors, created_at.

    Returns:
        Dictionary with three keys:
            passed (list): Clearly high-quality repos decided by heuristics.
            rejected (list): Clearly low-quality or fork repos.
            borderline (list): Repos requiring LLM judgment.
    """
    repos = json.loads(repos_json)
    passed = []
    rejected = []
    borderline = []

    now = datetime.now(timezone.utc)

    for repo in repos:
        # Always reject forks heuristically (per D-07 — never escalate forks to LLM)
        if repo.get("is_fork", False):
            rejected.append(repo)
            continue

        commits = repo.get("commits", 0)
        contributors = repo.get("contributors", 0)

        # Calculate repo age in days from created_at
        created_at_raw = repo.get("created_at", "")
        age_days = 9999  # default to old if missing
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(
                    created_at_raw.replace("Z", "+00:00")
                )
                age_days = (now - created_at).days
            except (ValueError, TypeError):
                age_days = 9999

        # Clear fail: commits < 5 OR contributors < 1 (per D-06 lower bound)
        if commits < 5 or contributors < 1:
            rejected.append(repo)
            continue

        # Clear pass: commits > 20 AND contributors > 3 AND age > 30 days (per D-06 upper bound)
        if commits > 20 and contributors > 3 and age_days > 30:
            passed.append(repo)
            continue

        # Borderline: everything else (commits 5-20, contributors 1-3, or age < 30 days)
        borderline.append(repo)

    return {"passed": passed, "rejected": rejected, "borderline": borderline}


critic_agent = LlmAgent(
    name="critic_agent",
    model="gemini-2.0-flash",
    instruction="""You are a quality critic for GitHub repositories. Your job is to
    filter a list of repositories, removing low-quality, spam, or irrelevant repos.

    First, use the heuristic_filter tool to automatically pass or reject repos
    based on quantitative signals. The tool will return three lists:
    - passed: Clearly high-quality repos (keep these)
    - rejected: Clearly low-quality repos (discard these)
    - borderline: Repos that need your judgment

    For borderline repos, evaluate each one and decide whether to keep or reject it
    based on: relevance to the query topic, signs of genuine development activity,
    and whether it appears to be a real project vs. a tutorial/boilerplate.

    Return the final filtered list of repos as JSON (passed + your approved borderline repos).""",
    description="Filters raw repository list, removing forks, boilerplate, and spam.",
    tools=[heuristic_filter],
    output_key="filtered_repos",
)
