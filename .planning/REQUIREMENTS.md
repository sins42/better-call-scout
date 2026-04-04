# Requirements: Better Call Scout

**Defined:** 2026-04-03
**Core Value:** A single query produces a structured, evidence-backed hypothesis about what's about to boom in tech — with VC, developer, and journalist perspectives in one report.

## v1 Requirements

### Data Schema (Shared — Day 1)

- [ ] **SCHEMA-01**: Pydantic model for repo data (name, url, stars, star_velocity, commits, contributors, issues, topics, language)
- [ ] **SCHEMA-02**: Pydantic model for news item (title, url, source, score, content, published_at)
- [ ] **SCHEMA-03**: Pydantic model for RAG context chunk (text, source, metadata)
- [ ] **SCHEMA-04**: Pydantic model for analyst hypothesis (persona, confidence_score, evidence, counter_evidence, reasoning, hypothesis_text)
- [ ] **SCHEMA-05**: Pydantic model for synthesis report (query, hypotheses, top_repos, generated_at)

### Collection Layer (Person 1: Raghav)

- [ ] **COLL-01**: GitHub Agent searches repos by topic/language/stars via REST API
- [ ] **COLL-02**: GitHub Agent fetches star history (stargazers with timestamps) for velocity calculation
- [ ] **COLL-03**: GitHub Agent fetches commit activity, contributor stats, issue velocity per repo
- [ ] **COLL-04**: HN + Tavily Agent fetches top/best HN stories via Firebase API
- [ ] **COLL-05**: HN + Tavily Agent fetches founder bios, funding news, job postings via Tavily
- [ ] **COLL-06**: RAG ingestion pipeline: fetch HN stories + RSS → chunk → embed with MiniLM → store in ChromaDB
- [ ] **COLL-07**: RAG Agent queries ChromaDB and returns relevant context chunks for a given topic
- [ ] **COLL-08**: All 3 collection agents run in parallel via ADK
- [ ] **COLL-09**: Critic Agent filters raw repo list (removes forks, boilerplate, one-day spikes, spam)

### Analysis Layer (Person 2: Sindhuja)

- [ ] **ANAL-01**: VC Analyst Agent scores repos on star velocity, market size signals, funding mentions, competitive landscape
- [ ] **ANAL-02**: Developer Analyst Agent scores repos on ecosystem maturity, adoption phase, job posting signals, historical benchmarking
- [ ] **ANAL-03**: Journalist Analyst Agent scores repos on narrative hook, HN sentiment/buzz, media coverage density, incumbent comparison
- [ ] **ANAL-04**: All 3 analyst agents run in parallel via ADK
- [ ] **ANAL-05**: Generator-Critic loop wired per analyst (analyst → critic challenge → analyst refine → commit, max 2 iterations)
- [ ] **ANAL-06**: Each analyst emits typed hypothesis JSON conforming to SCHEMA-04

### Synthesis & Output (Person 2: Sindhuja)

- [ ] **SYNTH-01**: Synthesis Agent merges 3 analyst hypotheses into unified report conforming to SCHEMA-05
- [ ] **SYNTH-02**: Synthesis Agent generates scout_report.md in-memory for download
- [ ] **SYNTH-03**: Synthesis Agent generates top_repos.csv in-memory for download

### Visualizations (Person 2: Sindhuja)

- [ ] **VIZ-01**: Star velocity line chart — top 10 repos, stars/week over 4-8 weeks
- [ ] **VIZ-02**: Category heatmap — tech categories × weeks, color = star velocity
- [ ] **VIZ-03**: HN Buzz vs GitHub Stars scatter — X=stars, Y=HN score
- [ ] **VIZ-04**: Persona score bar chart — side-by-side VC/Dev/Journalist scores per repo
- [ ] **VIZ-05**: All 4 charts downloadable as PNG

### Frontend (Person 2: Sindhuja)

- [ ] **FE-01**: Streamlit query input field
- [ ] **FE-02**: Persona multi-select (VC / Developer / Journalist)
- [ ] **FE-03**: Progress indicators during pipeline execution
- [ ] **FE-04**: Tabbed results display (one tab per persona)
- [ ] **FE-05**: Charts panel rendered inline
- [ ] **FE-06**: Download buttons for scout_report.md, top_repos.csv, and 4x PNG charts

### Orchestration (Shared)

- [ ] **ORCH-01**: ADK top-level orchestrator wires Collection → Critic → Analysis → Synthesis flow
- [ ] **ORCH-02**: Collection layer runs in parallel (3 agents concurrent)
- [ ] **ORCH-03**: Analysis layer runs in parallel (3 analyst agents concurrent)

### Deployment (Person 1: Raghav)

- [ ] **DEPLOY-01**: Dockerfile builds and runs Streamlit app on port 8080
- [ ] **DEPLOY-02**: Cloud Run service configured with correct env vars (GITHUB_TOKEN, TAVILY_API_KEY, GOOGLE_CLOUD_PROJECT)
- [ ] **DEPLOY-03**: Image pushed to Artifact Registry and deployed to Cloud Run
- [ ] **DEPLOY-04**: min-instances=1 set to avoid ChromaDB cold start

## v2 Requirements

### Performance & Reliability

- **PERF-01**: GitHub API caching layer to handle rate limits gracefully
- **PERF-02**: Tavily usage monitoring with automatic HN-only fallback
- **PERF-03**: Async timeout per generator-critic iteration to bound latency

### Extended Data Sources

- **EXT-01**: ProductHunt data ingestion into RAG corpus
- **EXT-02**: Kaggle startup dataset ingestion into RAG corpus

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming | Batch pipeline sufficient; streaming adds infra complexity |
| User authentication | No multi-user state needed for course deliverable |
| Persistent run history | Per-session downloads sufficient |
| Production secrets management | .env + Cloud Run env vars sufficient for course scope |
| Mobile UI | Streamlit web-only, no native mobile needed |
| OAuth / SSO | No auth layer needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHEMA-01 through SCHEMA-05 | Phase 1 | Pending |
| COLL-01 through COLL-09 | Phase 2 | Pending |
| ANAL-01 through ANAL-06 | Phase 3 | Pending |
| SYNTH-01 through SYNTH-03 | Phase 3 | Pending |
| VIZ-01 through VIZ-05 | Phase 3 | Pending |
| FE-01 through FE-06 | Phase 4 | Pending |
| ORCH-01 through ORCH-03 | Phase 4 | Pending |
| DEPLOY-01 through DEPLOY-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after initialization*
