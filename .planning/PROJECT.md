# Better Call Scout

## What This Is

A multi-agent system using Google ADK that analyzes trending GitHub repos and tech news to hypothesize which tech stacks or industries are about to boom — surfaced through three analyst lenses: VC, Developer, and Journalist. The system collects live data, filters it, runs parallel hypothesis generation with critic refinement, and delivers a downloadable report via a Streamlit UI deployed on Cloud Run.

## Core Value

A single query produces a structured, evidence-backed hypothesis about what's about to boom in tech — with VC, developer, and journalist perspectives in one report.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] GitHub Agent collects repo trends via REST API (star velocity, commits, contributors, issue velocity)
- [ ] HN + Tavily Agent collects tech news, founder signals, and job posting data
- [ ] RAG Agent queries ChromaDB corpus for domain context and historical benchmarking
- [ ] Critic Agent filters raw repos (removes forks, boilerplate, one-day spikes)
- [ ] VC Analyst Agent produces structured hypothesis JSON (star velocity, market signals, funding mentions)
- [ ] Developer Analyst Agent produces structured hypothesis JSON (ecosystem maturity, adoption curve, job signals)
- [ ] Journalist Analyst Agent produces structured hypothesis JSON (narrative hooks, HN sentiment, media density)
- [ ] Generator-Critic loop per analyst (max 2 iterations: Evidence → Draft → Challenge → Refine → Commit)
- [ ] Synthesis Agent merges 3 hypotheses into unified report with confidence scores
- [ ] 4 data visualizations: star velocity line chart, category heatmap, HN buzz vs stars scatter, persona score bars
- [ ] Streamlit frontend: query input, persona multi-select, tabbed results, chart panel, download buttons
- [ ] All artifacts downloadable: scout_report.md, top_repos.csv, 4x PNG charts
- [ ] Deployed on Cloud Run via Docker + Artifact Registry
- [ ] Shared Pydantic data schema contracts between collection and analysis layers

### Out of Scope

- Real-time streaming updates — single-query batch pipeline only
- User accounts / authentication — no multi-user state needed for course project
- Persistent run history — artifacts are downloaded per-session
- Production-grade secrets management — .env / Cloud Run env vars sufficient for course scope
- Mobile UI — Streamlit web only

## Context

Course project with a rubric requiring three pipeline steps (Collect, Explore/Analyze, Hypothesize) and elective coverage including: parallel execution, artifacts, code execution, second data retrieval method (GitHub API + RAG), structured output, data visualization, and iterative refinement.

Two-person team:
- **Person 1 — Raghav (thehyperpineapple):** Collection layer (GitHub, HN+Tavily, RAG agents), Critic Agent, shared Pydantic schemas, Cloud Run deployment
- **Person 2 — Sindhuja (sins42):** Analysis layer (VC, Developer, Journalist agents), Generator-Critic loop, Synthesis Agent, visualizations, Streamlit frontend

Integration point: `src/models/schemas.py` — must be defined before either person builds their layer.

**Stack:** Python 3.11, uv, Google ADK, Gemini 2.0 Flash (Vertex AI), ChromaDB (embedded), sentence-transformers/all-MiniLM-L6-v2, Streamlit, matplotlib/seaborn, pandas, Pydantic v2.

## Constraints

- **LLM:** Gemini 2.0 Flash via Vertex AI — zero cost on course GCP project, native ADK support
- **GitHub API:** 5,000 req/hour PAT limit — batch + cache required
- **Tavily:** 1,000 free searches/month — monitor usage, HN-only fallback
- **ChromaDB:** Embedded mode — persists to disk, containerizes cleanly, no separate infra
- **Embeddings:** Local sentence-transformers — no API dependency, free, ~384-dim vectors
- **Cloud Run:** Free tier — min-instances=1 recommended to avoid ChromaDB cold start
- **Dependencies:** uv for all package management, pyproject.toml as source of truth

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google ADK over LangGraph | Native GCP/Cloud Run integration, built for this deployment target | — Pending |
| ChromaDB embedded mode | Zero infra, persists to disk, clean containerization | — Pending |
| sentence-transformers local | Free, no API dependency, sufficient quality for domain retrieval | — Pending |
| Generator-Critic max 2 iterations | Prevents runaway latency; 2 rounds sufficient for hypothesis refinement | — Pending |
| Streamlit over custom frontend | Fast to build, easy to containerize, sufficient for course deliverable | — Pending |
| Shared schemas first | Both layers blocked on Pydantic contract — highest priority shared task | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-03 after initialization*
