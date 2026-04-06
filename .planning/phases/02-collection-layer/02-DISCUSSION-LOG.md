# Phase 2: Collection Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 02-collection-layer
**Areas discussed:** ADK Agent Structure, GitHub Search Scope, Critic Filtering Approach, RAG Ingestion Timing

---

## ADK Agent Structure

| Option | Description | Selected |
|--------|-------------|----------|
| A — Full ADK agents with LLM-driven tool calling | `Agent` instances where LLM decides which tools to call; full ADK pattern | initial pick |
| B — Plain async functions | No ADK `Agent` class; orchestrator calls `asyncio.gather` directly | |
| C — ADK agents wrapping async tool functions | ADK `Agent` instances with `FunctionTool`s; API logic in regular Python async functions | ✓ (switched) |

**User's choice:** Started with Option A, then switched to Option C after reflection.
**Notes:** Option C keeps API I/O logic testable in plain Python while still satisfying the ADK agent structure requirement.

---

## ADK Agent Structure (follow-up) — Parallel execution mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| ADK `ParallelAgent` | Declarative fan-out; ADK manages concurrency | ✓ |
| `asyncio.gather` over `.run()` calls | Explicit Python fan-out | |

**User's choice:** ADK `ParallelAgent`
**Notes:** Satisfies COLL-08 and makes ADK parallel execution demonstrable for course rubric.

---

## GitHub Search Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Small (20-30 repos) | Fast, well within rate limits, thin pool | |
| Medium (50-100 repos) | 1 search page, good balance | ✓ |
| Large (200+ repos) | Richer pool, multiple paginated requests | |

**User's choice:** Medium (50-100 repos)

---

## GitHub Search Scope (follow-up) — API-side filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Hard filters at query time | Apply star/date/fork filters via API params | |
| Broad fetch, Critic filters everything | Minimal API-side filtering; Critic owns all quality decisions | ✓ |

**User's choice:** Broad fetch, Critic owns filtering
**Notes:** Keeps concerns cleanly separated between collection and filtering stages.

---

## Critic Filtering Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Heuristic rules only | Pure Python logic; fast, deterministic, zero LLM calls | |
| LLM judgment (Gemini) | Vertex AI call per repo batch; flexible but adds latency | |
| Hybrid | Heuristics for clear cases, LLM for borderline repos | ✓ |
| You decide | — | |

**User's choice:** Hybrid

---

## Critic Filtering (follow-up) — What counts as borderline

| Option | Description | Selected |
|--------|-------------|----------|
| Quantitative boundary | Middle-range heuristic scores escalate to LLM | ✓ |
| Topic/name check | Heuristics handle structure, LLM reviews name/description for boilerplate language | |

**User's choice:** Quantitative boundary
**Notes:** Borderline = commits 5-20, contributors 1-3, or age < 30 days. Forks always rejected by heuristic.

---

## RAG Ingestion Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Offline pre-run script | Developer runs manually before deploy | |
| Container startup | Ingestion runs before Streamlit accepts requests | ✓ |
| On first query | Lazy initialization | |
| Scheduled refresh | Background thread refreshes corpus periodically | ✓ |

**User's choice:** Options 2 + 4 (container startup AND scheduled refresh)

---

## RAG Ingestion (follow-up) — Refresh frequency

| Option | Description | Selected |
|--------|-------------|----------|
| Every 24 hours via background thread | `threading.Timer` or `asyncio` background task | ✓ |
| Every 6-12 hours via background thread | More frequent, same mechanism | |
| You decide | — | |

**User's choice:** Every 24 hours via background thread

---

## Claude's Discretion

- Heuristic thresholds for "clear pass" vs. "clear fail" (outside the borderline range) are left to implementation judgment.
- Background thread implementation detail (`threading.Timer` vs. `asyncio` task) left to Claude.

## Deferred Ideas

None surfaced during discussion.
