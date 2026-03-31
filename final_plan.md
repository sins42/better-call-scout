# Finalized Plan: Better Call Scout - Venture Capital / Startup Scout

## Project Summary

A multi-agent system using Google ADK that analyzes trending GitHub repos and tech news to hypothesize which tech stacks or industries are about to boom — through three analyst lenses (VC, Developer, Journalist). Deployed on Google Cloud Run.

---

## Finalized Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| **Agent Framework** | Google ADK | Native GCP integration, built for Cloud Run |
| **LLM** | Gemini 2.0 Flash via Vertex AI | Zero cost on course GCP project, native ADK support |
| **GitHub Data** | GitHub REST API (free PAT) | 5,000 req/hour, rich star/commit/contributor data |
| **News/Web Search** | HackerNews Firebase API + Tavily (1,000 free/month) | HN fully open, Tavily extracts full content for LLM |
| **Vector Store** | ChromaDB (embedded mode) | Zero infra, persists to disk, containerizes cleanly |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Free, local, no API dependency, ~384-dim vectors |
| **Visualization** | matplotlib + seaborn | Standard, lightweight, renders in Streamlit |
| **Frontend** | Streamlit | Fast to build, easy to containerize |
| **Deployment** | Cloud Run (containerized) + Artifact Registry | Free tier covers project; minimal GCP surface |
| **Artifact Delivery** | Streamlit `st.download_button` | User downloads CSV, PNG, markdown to their local machine |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     COLLECTION LAYER (parallel)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ GitHub Agent │  │  HN + Tavily │  │    RAG Agent       │     │
│  │ (repo trends,│  │  Agent       │  │  (ChromaDB +       │     │
│  │  star vel.)  │  │  (news,      │  │   HN corpus,       │     │
│  │              │  │   founder    │  │   domain context)  │     │
│  │              │  │   search)    │  │                    │     │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘     │
└─────────┼─────────────────┼───────────────────┼─────────────────┘
          └─────────────────┴───────────────────┘
                            │  shared data pool
                            │  (Pydantic models)
                            ▼
          ┌─────────────────────────────────┐
          │         Critic Agent            │
          │  (filter spam/forks/hype)       │
          └─────────────┬───────────────────┘
                        │  cleaned data
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER (parallel)                    │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │  3a: VC Analyst│  │  3b: Developer │  │ 3c: Journalist   │   │
│  │  Agent         │  │  Agent         │  │ Agent            │   │
│  └────────┬───────┘  └───────┬────────┘  └────────┬─────────┘   │
└───────────┼──────────────────┼────────────────────┼─────────────┘
            │    generator-critic loop (max 2 iter) │
            └──────────────────┴────────────────────┘
                               │  structured hypotheses
                               ▼
          ┌─────────────────────────────────┐
          │       Synthesis Agent           │
          │  (unified report + charts)      │
          └─────────────────┬───────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │       Streamlit Frontend        │
          │  (tabs, charts, downloads)      │
          └─────────────────────────────────┘
```

---

## The Three Steps (Rubric Mapping)

### Step 1: Collect
- **GitHub Agent** — searches repos by topic/language/stars, fetches star history, commit activity, contributor stats, issue velocity
- **HN + Tavily Agent** — HN Firebase API for top stories + Tavily for founder bios, funding news, job postings
- **RAG Agent** — queries ChromaDB corpus (pre-embedded HN stories, RSS feeds, ProductHunt, Kaggle startup data)
- All three run in parallel via ADK; results merged into shared Pydantic data pool

### Step 2: Explore and Analyze (EDA)
- **Critic Agent** filters raw repos — removes forks, boilerplate, one-day spikes
- **3a VC Analyst** — star velocity ranking, market signals, funding mentions, competitive landscape
- **3b Developer** — ecosystem maturity, adoption curve, job posting signals, historical benchmarking
- **3c Journalist** — narrative hooks, HN sentiment, media coverage density, incumbent comparison
- Each analyst emits structured JSON output schema

### Step 3: Hypothesize
- Each analyst follows **Evidence → Draft → Challenge → Refine → Commit** loop with Critic Agent (max 2 iterations)
- **Synthesis Agent** merges 3 structured hypotheses into unified report
- Output: hypothesis with confidence score, supporting evidence, counter-evidence, reasoning
- Artifacts: `scout_report.md`, `top_repos.csv`, 4 PNG charts — all downloadable via Streamlit

---

## Data Visualizations

| Chart | What it shows | Supports |
|---|---|---|
| **Star Velocity Line Chart** | Top 10 repos — stars/week over 4-8 weeks | 3a VC, 3b Dev |
| **Category Heatmap** | Tech categories x weeks, color = star velocity | All personas |
| **HN Buzz vs. GitHub Stars Scatter** | X = stars, Y = HN score — spots gems and hype traps | 3c Journalist, Critic |
| **Persona Score Bar Chart** | Side-by-side 3a/3b/3c scores per repo | All personas |

All charts rendered in Streamlit UI and downloadable as PNG.

---

## Electives Coverage

| Elective | Implementation |
|---|---|
| **Parallel Execution** | Collection layer (3 agents) + Analysis layer (3 agents) run concurrently via ADK |
| **Artifacts** | `scout_report.md`, `top_repos.csv`, 4x PNG charts — downloadable |
| **Code Execution** | pandas for star velocity computation + matplotlib for chart generation |
| **Second Data Retrieval Method** | GitHub API (REST search) + RAG (ChromaDB vector retrieval) |
| **Structured Output** | Each analyst emits typed JSON hypothesis schema |
| **Data Visualization** | 4 charts: star velocity, category heatmap, buzz vs. stars, persona scores |
| **Iterative Refinement** | Generator-Critic hypothesis loop per analyst (max 2 iterations) |

---

## Work Split

### Person 1 — Data & Collection Pipeline [Raghav](https://github.com/thehyperpineapple)

**Owns:** Everything that fetches, stores, and serves raw data to the analysis layer. Plus deployment.

| Task | Details | Est. Time |
|---|---|---|
| **GitHub Agent** | Search repos by topic/language/stars, fetch star history (stargazers w/ timestamps), commit activity, contributor stats, issue velocity via GitHub REST API | 1.5 days |
| **HN + Tavily Agent** | HN Firebase API for top/best stories + Tavily search for founder bios, funding news, job postings | 1 day |
| **RAG Agent + Ingestion Pipeline** | Fetch HN stories + RSS feeds → chunk → embed with MiniLM → store in ChromaDB. Build retrieval tool for analyst agents. | 1.5 days |
| **Shared Data Schema** | Define Pydantic models for the contract between Collection and Analysis layers — repo data, news items, RAG context | 0.5 day |
| **Critic Agent** | Filter raw repo list: remove forks, boilerplate, one-day spikes, spam repos | 0.5 day |
| **Cloud Run Deployment** | Dockerfile, Artifact Registry push, Cloud Run service config, env vars for API keys (GitHub PAT, Tavily, Vertex AI) | 1 day |
| **Integration testing** | End-to-end: query in → all 3 collectors return data → Critic filters | 0.5 day |

**Total: ~6.5 days**

---

### Person 2 — Analysis, Hypothesis & Frontend [Sindhuja](https://github.com/sins42)

**Owns:** Everything that consumes the shared data pool and turns it into hypotheses, visualizations, and user-facing output.

| Task | Details | Est. Time |
|---|---|---|
| **3a VC Analyst Agent** | Star velocity ranking, market size signals from RAG, funding mention extraction, competitive landscape scoring. Emits structured hypothesis JSON. | 1 day |
| **3b Developer Agent** | Ecosystem maturity scoring, adoption phase classification, job posting signal, historical benchmarking via RAG. Emits structured hypothesis JSON. | 1 day |
| **3c Journalist Agent** | Narrative hook scoring, HN sentiment/buzz, media coverage density, incumbent comparison via RAG. Emits structured hypothesis JSON. | 1 day |
| **Generator-Critic Loop** | Wire each analyst → Critic challenge → analyst refine → commit. Max 2 iterations per analyst. | 0.5 day |
| **Synthesis Agent** | Merge 3 hypotheses into unified report. Generate `scout_report.md` and `top_repos.csv` in-memory for download. | 0.5 day |
| **4 Data Visualizations** | Star velocity line chart, category heatmap, buzz vs. stars scatter, persona score bars. matplotlib/seaborn, rendered in Streamlit + downloadable as PNG. | 1 day |
| **Streamlit Frontend** | Query input, persona multi-select, progress indicators, tabbed results (3a/3b/3c), charts panel, download buttons for all artifacts. | 1 day |
| **Integration testing** | Mock data pool → analysts → critic loop → synthesis → UI renders correctly | 0.5 day |

**Total: ~6.5 days**

---

### Shared Responsibilities

| Task | Details | When |
|---|---|---|
| **Shared data schema** | Agree on Pydantic models for the data contract between layers | Day 1 |
| **ADK Orchestrator** | Top-level agent that wires Collection → Analysis → Synthesis flow | Day 5-6 |
| **README.md** | Document all 3 steps, agent responsibilities, elective claims, how to run | Day 9-10 |
| **End-to-end testing** | Full pipeline: user query → deployed Cloud Run → report output | Day 10 |

---

## Timeline (Mar 30 → Apr 12 = 13 days)

```
Day 1-2  (Mar 30-31):  Schema agreement + both start building independently
Day 3-5  (Apr 1-3):    Person 1: collectors + critic done
                        Person 2: 3 analyst agents done
Day 6-7  (Apr 4-5):    Person 1: RAG pipeline + deployment setup
                        Person 2: critic loop + synthesis agent
Day 8    (Apr 6):      Integration — wire both layers via ADK orchestrator
Day 9    (Apr 7):      Person 2: Streamlit UI + visualizations
                        Person 1: Cloud Run deploy + env config
Day 10   (Apr 8):      End-to-end testing on Cloud Run
Day 11   (Apr 9):      Bug fixes, README, polish
Day 12-13 (Apr 10-12): Buffer for unexpected issues
```

---

## API Keys & Environment Variables

| Variable | Source | Who Sets Up |
|---|---|---|
| `GITHUB_TOKEN` | GitHub Settings → Personal Access Tokens | Person 1 |
| `TAVILY_API_KEY` | tavily.com (free tier, 1,000/month) | Person 1 |
| `GOOGLE_CLOUD_PROJECT` | Course-provided GCP project | Both |
| Vertex AI (Gemini) | Enabled via GCP console, uses service account | Person 1 (deployment) |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| GitHub API rate limits (30 search/min) | Slow collection for broad queries | Batch + cache results; use conditional requests |
| Tavily free tier runs out (1,000/month) | No web search mid-demo | Monitor usage; fall back to HN-only for news |
| ChromaDB cold start on Cloud Run | First query slow (~10s to load embeddings) | Set min-instances=1 on Cloud Run, or accept cold start |
| Generator-Critic loop takes too long | UI feels slow | Set timeout per iteration; 2 iteration max already in design |
| ADK is newer, less community examples | Debugging harder | Both people read ADK docs Day 1; fallback to LangGraph if blocked by Day 3 |
