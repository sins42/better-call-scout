# Roadmap: Better Call Scout

## Overview

Better Call Scout is a multi-agent pipeline that transforms a user query into an evidence-backed hypothesis about what's about to boom in tech. The roadmap delivers this in five phases: shared data contracts first (unblocking both teammates), then the collection layer (Person 1) and analysis layer (Person 2) in parallel-capable phases, followed by integration wiring and frontend, and finally deployment with end-to-end validation. Every phase produces a verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4, 5): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Data Contracts** - Define shared Pydantic schemas that unblock both teammates
- [ ] **Phase 2: Collection Layer** - GitHub, HN+Tavily, and RAG agents collect and filter raw data
- [ ] **Phase 3: Analysis Layer** - Three analyst agents generate critic-refined hypotheses with synthesis and visualizations
- [ ] **Phase 4: Integration + Frontend** - ADK orchestrator wires the full pipeline; FastAPI + HTML/CSS/JS frontend surfaces results
- [ ] **Phase 5: Deployment + Polish** - Cloud Run deployment, end-to-end testing, project documentation

## Phase Details

### Phase 1: Data Contracts
**Goal**: Both teammates can import typed Pydantic models and build against a stable interface
**Depends on**: Nothing (first phase)
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04, SCHEMA-05
**Success Criteria** (what must be TRUE):
  1. `from src.models.schemas import RepoData, NewsItem, RAGContextChunk, AnalystHypothesis, SynthesisReport` succeeds without error
  2. Each model can be instantiated with valid sample data and rejects invalid data (Pydantic validation works)
  3. Both teammates (Raghav and Sindhuja) have reviewed and agreed on all field names, types, and constraints
  4. Collection layer agents and analysis layer agents can reference these models as their input/output contracts
**Plans**: TBD
**Owner**: Shared (Raghav + Sindhuja)

Plans:
- [ ] 01-01: Define all five Pydantic v2 models with validation and sample fixtures

### Phase 2: Collection Layer
**Goal**: A user query produces a filtered, structured pool of repo data, news items, and RAG context ready for analyst consumption
**Depends on**: Phase 1
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-04, COLL-05, COLL-06, COLL-07, COLL-08, COLL-09
**Success Criteria** (what must be TRUE):
  1. GitHub Agent returns a list of RepoData objects with star velocity, commit activity, contributor stats, and issue velocity for a given topic query
  2. HN+Tavily Agent returns a list of NewsItem objects with HN stories and Tavily-sourced founder/funding/job data
  3. RAG Agent returns relevant RAGContextChunk objects from a pre-populated ChromaDB corpus for a given topic
  4. All three collection agents can run concurrently (parallel ADK execution verified)
  5. Critic Agent filters the raw repo list, removing forks, boilerplate, one-day spikes, and spam — output is a smaller, cleaner list of RepoData
**Plans**: 2 plans
**Owner**: Person 1 (Raghav)

Plans:
- [x] 02-01-PLAN.md — GitHub Agent + HN/Tavily Agent: search, star velocity, commit activity, HN Firebase, Tavily news tools
- [x] 02-02-PLAN.md — RAG ingestion pipeline + RAG Agent + Critic Agent + ParallelAgent wiring

### Phase 3: Analysis Layer
**Goal**: Three analyst perspectives produce critic-refined, structured hypotheses with supporting visualizations
**Depends on**: Phase 1 (schemas), Phase 2 (cleaned data pool)
**Requirements**: ANAL-01, ANAL-02, ANAL-03, ANAL-04, ANAL-05, ANAL-06, SYNTH-01, SYNTH-02, SYNTH-03, VIZ-01, VIZ-02, VIZ-03, VIZ-04, VIZ-05
**Success Criteria** (what must be TRUE):
  1. VC Analyst Agent emits a valid AnalystHypothesis JSON covering star velocity, market signals, funding mentions, and competitive landscape
  2. Developer Analyst Agent emits a valid AnalystHypothesis JSON covering ecosystem maturity, adoption phase, job signals, and historical benchmarking
  3. Journalist Analyst Agent emits a valid AnalystHypothesis JSON covering narrative hooks, HN sentiment, media density, and incumbent comparison
  4. Each analyst's hypothesis has been through at least one generator-critic refinement cycle (max 2 iterations)
  5. Synthesis Agent merges three hypotheses into a unified SynthesisReport with scout_report.md and top_repos.csv artifacts
  6. Four charts (star velocity line, category heatmap, HN buzz vs stars scatter, persona score bars) render as PNG images
**Plans**: TBD
**Owner**: Person 2 (Sindhuja)

Plans:
- [x] 03-01: Three analyst agents + generator-critic loop
- [x] 03-02: Synthesis Agent + visualizations

### Phase 4: Integration + Frontend
**Goal**: A user can enter a query in a FastAPI + HTML/CSS/JS frontend and receive a complete multi-perspective hypothesis report with charts and downloads
**Depends on**: Phase 2, Phase 3
**Requirements**: ORCH-01, ORCH-02, ORCH-03, FE-01, FE-02, FE-03, FE-04, FE-05, FE-06
**Success Criteria** (what must be TRUE):
  1. ADK orchestrator wires the full pipeline: Collection (parallel) -> Critic -> Analysis (parallel) -> Synthesis
  2. User can enter a topic query in the query input field and select which personas to include
  3. Progress indicators (SSE breadcrumb strip) show pipeline status during execution
  4. Results display in pill tabs (one per persona) with the charts panel rendered inline
  5. User can download scout_report.md, top_repos.csv, and all 4 PNG charts via download buttons
**Plans**: 2 plans
**Owner**: Shared (ORCH) + Person 2 (FE)
**UI hint**: yes

Plans:
- [ ] 04-01-PLAN.md — ADK orchestrator wiring: SequentialAgent pipeline, run_pipeline(), generate_artifacts()
- [ ] 04-02-PLAN.md — FastAPI app (POST /run, GET /stream, GET /download/{artifact}, GET /) + complete HTML/CSS/JS single-page frontend

### Phase 5: Deployment + Polish
**Goal**: The application is live on Cloud Run and passes end-to-end validation from query to downloadable report
**Depends on**: Phase 4
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. Docker image builds successfully and runs the FastAPI app on port 8080
  2. Cloud Run service is deployed with correct env vars (GITHUB_TOKEN, TAVILY_API_KEY, GOOGLE_CLOUD_PROJECT) and min-instances=1
  3. A user can access the public Cloud Run URL, submit a query, and receive a complete report with all artifacts downloadable
  4. README documents the three pipeline steps, agent responsibilities, elective claims, and how to run locally and on Cloud Run
**Plans**: TBD
**Owner**: Person 1 (Raghav) + Shared

Plans:
- [ ] 05-01: Dockerfile, Cloud Run deploy, end-to-end testing, README

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5
Note: Phases 2 and 3 can proceed in parallel after Phase 1 (different owners), but Phase 3 depends on Phase 2 output for integration testing.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Contracts | 0/1 | Not started | - |
| 2. Collection Layer | 1/2 | In Progress|  |
| 3. Analysis Layer | 0/2 | Not started | - |
| 4. Integration + Frontend | 0/2 | Not started | - |
| 5. Deployment + Polish | 0/1 | Not started | - |
