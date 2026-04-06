---
phase: 02-collection-layer
plan: 01
subsystem: collection
tags: [github-agent, hn-tavily-agent, adk, llm-agent, async, tools]
dependency_graph:
  requires: [01-data-contracts/01-01]
  provides: [github_agent, hn_tavily_agent]
  affects: [02-02-parallel-agent, critic-agent]
tech_stack:
  added: []
  patterns: [ADK LlmAgent with FunctionTool, asyncio.to_thread for sync HTTP, asyncio.gather for concurrent fetching, 202-retry for GitHub stats endpoints]
key_files:
  created:
    - src/agents/collection/github_agent.py
    - tests/test_collection.py
  modified:
    - src/agents/collection/hn_tavily_agent.py
decisions:
  - Patch AsyncTavilyClient at module level (src.agents.collection.hn_tavily_agent.AsyncTavilyClient) not at import source (tavily.AsyncTavilyClient) for mock fidelity
  - Star velocity uses first-page sampling (100 most recent stargazers) per research anti-pattern guidance — avoids paginating all stargazers for 50-100 repos
metrics:
  duration: ~20 minutes
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 3
---

# Phase 02 Plan 01: GitHub Agent and HN+Tavily Agent Summary

**One-liner:** ADK LlmAgent collection agents for GitHub repo trending data (star velocity, commits, contributors) and HN+Tavily news with graceful Tavily fallback.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | GitHub Agent with search, star velocity, and repo detail tools | 688105b | src/agents/collection/github_agent.py, tests/test_collection.py |
| 2 | HN+Tavily Agent with HN Firebase and Tavily search tools | 023121a | src/agents/collection/hn_tavily_agent.py, tests/test_collection.py |

## What Was Built

### GitHub Agent (`src/agents/collection/github_agent.py`)

- `search_github_repos(query, language, min_stars)`: Searches GitHub via REST API with `per_page=100` (per D-03), returns repo list with name, url, stars, language, topics, is_fork, created_at
- `fetch_repo_details(owner, repo)`: Fetches star velocity (first-page stargazer sampling, clamped to [-1.0, 1.0]), 30-day commits (last 4 weeks from commit_activity), contributor count, and open issues
- `_github_get_with_retry`: Handles GitHub stats 202 cache-miss responses with configurable retry + sleep
- `github_agent`: ADK `LlmAgent` with `output_key="github_results"`, registered tools: search + details

### HN+Tavily Agent (`src/agents/collection/hn_tavily_agent.py`)

- `fetch_hn_top_stories(limit)`: Fetches HN top story IDs, then concurrently fetches story details via `asyncio.gather`; stories without URL fall back to `https://news.ycombinator.com/item?id={id}`
- `search_tavily_news(query, max_results)`: Wraps `AsyncTavilyClient.search` with HN-only fallback when `TAVILY_API_KEY` is absent or Tavily raises an exception
- `hn_tavily_agent`: ADK `LlmAgent` with `output_key="hn_tavily_results"`, registered tools: HN + Tavily

### Tests (`tests/test_collection.py`)

17 tests covering:
- GitHub search response shape and required keys
- Star velocity clamping to [-1.0, 1.0]
- 202 retry logic (mock returns 202 first, then 200)
- LlmAgent instance assertions (name, output_key)
- HN story concurrent fetch (asyncio.gather source inspection)
- HN URL fallback for Ask HN posts
- Tavily results shape and required keys
- Tavily fallback with missing API key
- Tavily fallback on exception (quota exhaustion)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock patch path for AsyncTavilyClient**
- **Found during:** Task 2 test execution
- **Issue:** Tests patched `tavily.AsyncTavilyClient` but the module imports it at the top level, so the mock didn't intercept calls made through the already-bound name in `hn_tavily_agent`
- **Fix:** Changed patch target to `src.agents.collection.hn_tavily_agent.AsyncTavilyClient` (patch where it's used, not where it's defined)
- **Files modified:** tests/test_collection.py
- **Commit:** 023121a

## Known Stubs

None — both agents are fully implemented with real API logic. Tool functions return structured dicts matching the `RepoData` and `NewsItem` schema fields (not Pydantic objects, as ADK serializes tool returns directly).

## Self-Check

Files created/modified:
- src/agents/collection/github_agent.py — FOUND
- src/agents/collection/hn_tavily_agent.py — FOUND
- tests/test_collection.py — FOUND

Commits:
- 688105b — FOUND
- 023121a — FOUND

Test results: 17/17 passing
