---
phase: 02-collection-layer
plan: 02
subsystem: collection
tags: [chromadb, rag, sentence-transformers, miniLM, parallel-agent, sequential-agent, critic-agent, heuristic-filter, adk]

dependency_graph:
  requires:
    - phase: 02-01
      provides: "github_agent, hn_tavily_agent, LlmAgent pattern with output_key"
    - phase: 01-data-contracts
      provides: "RAGContextChunk, RepoData Pydantic schemas"
  provides:
    - "src/rag/ingestion.py: HN fetch, text chunking, MiniLM embedding, ChromaDB storage with deterministic IDs"
    - "src/rag/retrieval.py: query_corpus and async_query_corpus ChromaDB query interface"
    - "src/agents/collection/rag_agent.py: rag_agent LlmAgent wrapping retrieval, output_key=rag_results"
    - "src/agents/critic_agent.py: critic_agent with heuristic_filter (D-05/D-06/D-07) + LLM escalation"
    - "src/agents/collection/__init__.py: collection_parallel (ParallelAgent) + collection_pipeline (SequentialAgent)"
  affects:
    - "04-orchestrator"
    - "03-analysis-layer (reuses query_corpus for analyst agents)"

tech-stack:
  added: []
  patterns:
    - "ChromaDB PersistentClient + SentenceTransformerEmbeddingFunction(all-MiniLM-L6-v2) for embedded vector storage"
    - "Deterministic SHA-256 IDs (first 16 chars) for idempotent document ingestion"
    - "importlib.import_module to avoid package-attribute shadowing of submodules in __init__.py"
    - "Heuristic filter: forks always rejected, commits/contributors/age thresholds for pass/reject/borderline"
    - "ParallelAgent(sub_agents=[...]) -> SequentialAgent([parallel, critic]) pipeline composition"

key-files:
  created:
    - src/rag/ingestion.py
    - src/rag/retrieval.py
    - src/agents/collection/rag_agent.py
    - src/agents/critic_agent.py
    - src/agents/collection/__init__.py
  modified:
    - tests/test_collection.py

key-decisions:
  - "Use importlib.import_module in __init__.py to avoid package-attribute shadowing: `from pkg.sub import name` sets pkg.sub = name (LlmAgent), breaking `import pkg.sub as module` in tests; importlib avoids this"
  - "D-05/D-06/D-07 thresholds encoded directly in heuristic_filter: forks always rejected, commits>20+contributors>3+age>30d pass, commits<5 or contributors<1 reject, everything else borderline"

patterns-established:
  - "RAG retrieval returns {text, source, metadata} dicts matching RAGContextChunk shape without requiring Pydantic instantiation"
  - "Async tool functions that call sync ChromaDB code use asyncio.to_thread (same pattern as GitHub/HN agents)"

requirements-completed: [COLL-06, COLL-07, COLL-08, COLL-09]

duration: ~25min
completed: "2026-04-06"
---

# Phase 02 Plan 02: RAG Pipeline, Critic Agent, and Parallel Collection Summary

**ChromaDB RAG pipeline (MiniLM embeddings, deterministic SHA-256 IDs) + heuristic/LLM Critic Agent + ParallelAgent composition wiring all three collection agents into a SequentialAgent pipeline**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-06T18:05:00Z
- **Completed:** 2026-04-06T18:30:54Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- RAG ingestion pipeline fetches HN top stories concurrently, chunks text, generates deterministic SHA-256 IDs, embeds with all-MiniLM-L6-v2, and stores in ChromaDB (COLL-06)
- RAG retrieval interface (sync + async) returns RAGContextChunk-shaped dicts; reusable by analyst agents in Phase 3 (COLL-07)
- Critic Agent applies D-05/D-06/D-07 heuristic rules: forks always rejected, clear pass/fail by commit+contributor+age thresholds, borderline repos escalated to Gemini for judgment (COLL-09)
- ParallelAgent composition wires all three collection agents for concurrent execution; SequentialAgent chains parallel collection -> critic filtering (COLL-08)
- All 40 collection layer tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: RAG ingestion/retrieval failing tests** - `d2560a3` (test)
2. **Task 1 GREEN: Implement src/rag/ingestion.py and src/rag/retrieval.py** - `7eafd6c` (feat)
3. **Task 2 RED: RAG agent and critic agent failing tests** - `945dc0c` (test)
4. **Task 2 GREEN: Implement rag_agent.py and critic_agent.py** - `b6ee3c2` (feat)
5. **Task 3: Wire ParallelAgent + SequentialAgent, add composition tests** - `82df302` (feat)

## Files Created/Modified

- `src/rag/ingestion.py` — HN fetch, chunk_text, _generate_doc_id, ingest_documents, ingest_hn_stories
- `src/rag/retrieval.py` — query_corpus (sync), async_query_corpus (async wrapper)
- `src/agents/collection/rag_agent.py` — query_rag_corpus tool + rag_agent LlmAgent (output_key=rag_results)
- `src/agents/critic_agent.py` — heuristic_filter tool + critic_agent LlmAgent (output_key=filtered_repos)
- `src/agents/collection/__init__.py` — collection_parallel (ParallelAgent) + collection_pipeline (SequentialAgent)
- `tests/test_collection.py` — 23 new tests for RAG ingestion, retrieval, RAG agent, critic agent, composition

## Decisions Made

**importlib.import_module pattern for __init__.py:** When `__init__.py` uses `from pkg.sub import name`, Python sets `pkg.sub` attribute to the LlmAgent object. Subsequent `import pkg.sub as module` resolves via `getattr(pkg, 'sub')`, returning the LlmAgent, breaking the pre-existing test that does `import src.agents.collection.hn_tavily_agent as module` and then inspects `module.fetch_hn_top_stories`. Fix: use `importlib.import_module` to get the submodule, extract agent instances as private `_xxx_mod.agent`, and build `collection_parallel` from those references without setting the agent as a package attribute.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed package-attribute shadowing of submodule in __init__.py**
- **Found during:** Task 3 (ParallelAgent composition)
- **Issue:** `from src.agents.collection.hn_tavily_agent import hn_tavily_agent` in `__init__.py` caused `import src.agents.collection.hn_tavily_agent as module` to return the LlmAgent (not the module), breaking the pre-existing test `test_fetch_hn_top_stories_concurrent_fetch` which calls `inspect.getsource(module.fetch_hn_top_stories)`
- **Fix:** Replaced `from pkg.sub import name` imports with `importlib.import_module("pkg.sub")` calls. Agent instances accessed as `_mod.agent_name` to build ParallelAgent without setting package-level names that shadow submodules.
- **Files modified:** src/agents/collection/__init__.py
- **Verification:** All 40 tests pass including `test_fetch_hn_top_stories_concurrent_fetch`
- **Committed in:** 82df302

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix preserves correctness of pre-existing tests while satisfying the plan's __init__.py composition requirements. No scope creep.

## Known Stubs

None — all implemented functions return real data:
- `ingest_hn_stories()` fetches live HN API data (mocked in tests)
- `query_corpus()` queries real ChromaDB collection (mocked in tests)
- `heuristic_filter()` applies real threshold logic
- All agents are real LlmAgent instances with correct names/output_keys

## Issues Encountered

Python module system: `import pkg.sub as mod` resolves via `getattr(pkg, 'sub')`, not `sys.modules['pkg.sub']` — this is a Python quirk that affects any `__init__.py` that wants to both export a name identical to a submodule name AND preserve submodule access via dotted import syntax.

## Self-Check

Files created/modified:
- src/rag/ingestion.py — FOUND
- src/rag/retrieval.py — FOUND
- src/agents/collection/rag_agent.py — FOUND
- src/agents/critic_agent.py — FOUND
- src/agents/collection/__init__.py — FOUND
- tests/test_collection.py — FOUND

Commits:
- d2560a3 — FOUND (test RED for Task 1)
- 7eafd6c — FOUND (feat GREEN for Task 1)
- 945dc0c — FOUND (test RED for Task 2)
- b6ee3c2 — FOUND (feat GREEN for Task 2)
- 82df302 — FOUND (feat Task 3)

Test results: 40/40 passing

## Next Phase Readiness

- `collection_pipeline` exported and ready for orchestrator import in Phase 4
- `query_corpus` and `async_query_corpus` in `src/rag/retrieval.py` reusable by Phase 3 analyst agents
- Corpus ingestion (`ingest_hn_stories`) ready to be called at container startup per D-08

---
*Phase: 02-collection-layer*
*Completed: 2026-04-06*
