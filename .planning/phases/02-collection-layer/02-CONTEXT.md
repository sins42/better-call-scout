# Phase 2: Collection Layer - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A user query triggers three parallel collection agents (GitHub, HN+Tavily, RAG) running concurrently via ADK. The raw repo pool flows through a Critic Agent that filters it using heuristic rules with LLM escalation for borderline cases. Output: a clean, structured pool of `RepoData`, `NewsItem`, and `RAGContextChunk` objects ready for Phase 3 analysts.

New capabilities (scoring, hypothesis generation, visualizations) belong in Phase 3. This phase ends when the filtered data pool is produced.

</domain>

<decisions>
## Implementation Decisions

### ADK Agent Structure
- **D-01:** Each collection agent is an ADK `Agent` instance wrapping async Python tool functions — not plain async functions, not full LLM-driven tool-calling. API call logic (GitHub REST, HN Firebase, Tavily SDK, ChromaDB) lives in regular Python async functions registered as `FunctionTool`s.
- **D-02:** The orchestrator runs all three collection agents in parallel using ADK's `ParallelAgent` (declarative fan-out, not `asyncio.gather`). This satisfies COLL-08 and demonstrates ADK parallel execution for the course rubric.

### GitHub Search Scope
- **D-03:** GitHub Agent fetches 50-100 repos per query (medium pool — 1 search page, well within rate limits).
- **D-04:** Minimal API-side filtering at query time. The GitHub Agent fetches broadly; the Critic Agent owns all quality decisions. Keeps concerns cleanly separated.

### Critic Filtering Approach
- **D-05:** Hybrid filtering — heuristic rules handle clear passes and clear fails; Gemini (via ADK) reviews borderline repos only.
- **D-06:** Borderline threshold defined quantitatively: repos with commits between 5-20, contributors between 1-3, or age < 30 days escalate to LLM review. Repos outside these ranges (clearly good or clearly bad) are decided by heuristics alone.
- **D-07:** Heuristic signals to implement: `is_fork`, commit count (last 30d), contributor count, repo age from creation date. Forks are always rejected by heuristic (never escalated to LLM).

### RAG Ingestion Timing
- **D-08:** Ingestion runs at container startup — `src/rag/ingestion.py` is called before Streamlit accepts requests. Corpus is always fresh on deploy.
- **D-09:** A background thread refreshes the corpus every 24 hours during long-running sessions (`threading.Timer` or `asyncio` background task).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Contracts
- `src/models/schemas.py` — All five Pydantic v2 models. Collection agents produce `RepoData`, `NewsItem`, `RAGContextChunk`. Build to these exactly — field names, types, and constraints are locked.

### Requirements
- `.planning/REQUIREMENTS.md` §Collection Layer — COLL-01 through COLL-09; all must be satisfied by this phase.

### Architecture
- `.planning/codebase/ARCHITECTURE.md` — Full pipeline data flow; Stage 1 (Collection) and Stage 2 (Critic) sections are directly relevant.
- `.planning/codebase/STACK.md` — Confirmed stack: `google-adk`, `requests`, `tavily-python`, `chromadb`, `sentence-transformers`.

### Constraints
- `.planning/PROJECT.md` §Constraints — GitHub rate limit (5,000 req/hour), Tavily quota (1,000/month with HN-only fallback), ChromaDB embedded mode.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/models/schemas.py` — Fully implemented. `RepoData`, `NewsItem`, `RAGContextChunk` are the output contracts for collection agents. Import directly.
- `src/agents/collection/github_agent.py` — Stub with correct docstring; implement here.
- `src/agents/collection/hn_tavily_agent.py` — Stub with correct docstring; implement here.
- `src/agents/collection/rag_agent.py` — Stub with correct docstring; implement here.
- `src/agents/critic_agent.py` — Stub with correct docstring; implement here.
- `src/rag/ingestion.py` — Stub; implement ingestion pipeline here.
- `src/rag/retrieval.py` — Stub; implement ChromaDB query interface here.

### Established Patterns
- Pydantic v2 with `model_validator` (not `validator`) — established in Phase 1.
- Async-first: all ADK agent functions must be `async def`.
- `uv run` for all execution; no direct `python` invocation.

### Integration Points
- `src/orchestrator.py` — Phase 4 will wire the orchestrator; Phase 2 agents must expose a compatible interface. Design agent `run()` signatures with this in mind.
- `src/rag/retrieval.py` — Both the RAG collection agent (Phase 2) and the analyst agents (Phase 3) call this. Design the retrieval interface to be reusable.

</code_context>

<specifics>
## Specific Ideas

- The `ParallelAgent` choice is deliberate for course rubric — makes ADK parallel execution explicit and demonstrable.
- Critic's LLM escalation is scoped tightly (quantitative thresholds) so Gemini calls are bounded and predictable. Forks are always heuristic-rejected.
- RAG refresh at 24h is sufficient for a course demo; HN data doesn't change faster than that for the purposes of hypothesis generation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-collection-layer*
*Context gathered: 2026-04-05*
