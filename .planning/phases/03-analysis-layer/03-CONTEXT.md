# Phase 3: Analysis Layer - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Three analyst perspectives (VC, Developer, Journalist) produce critic-refined, structured hypotheses from the cleaned data pool, combined into a unified SynthesisReport with supporting visualizations. Inputs are typed Pydantic objects from Phase 1 schemas. Orchestration wiring and the Streamlit UI are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Analyst Persona Voices

- **D-01:** VC Analyst is **decisive & contrarian** — takes strong positions even when evidence is mixed. Produces clear "about to break out" or "overhyped" verdicts. Not balanced; not hedged.
- **D-02:** Developer Analyst is a **pragmatic engineer** — primary question is "Is this actually production-ready? Would I bet my team on it?" Focuses on DX, community health, and ecosystem maturity over metrics alone.
- **D-03:** Journalist Analyst is a **tech media skeptic** — asks "What's the real story vs the hype?" Looks for narrative arc, incumbent threats, and what's being undercovered by mainstream tech press.

### Generator-Critic Loop

- **D-04:** The critic is a **separate ADK agent** with its own system prompt. It acts as a devil's advocate — it does not share the analyst's perspective and is specifically prompted to challenge the hypothesis.
- **D-05:** **Always 2 iterations** — both rounds run regardless of confidence score. Consistency and reliability over latency optimization. Loop: analyst generates → critic challenges → analyst refines → commit.
- **D-06:** Each analyst runs its own independent generator-critic loop. The loops are not shared across analysts.

### Parallel Data Routing

- **D-07:** All 3 analysts receive the **full data pool** — all `RepoData` objects, `NewsItem` objects, and `RAGContextChunk` objects. Each analyst's persona prompt shapes what signals they focus on. No pre-filtering or routing logic between collection and analysis layers.

### Synthesis Strategy

- **D-08:** The Synthesis Agent writes a **new narrative layer** — it reads all 3 `AnalystHypothesis` objects and produces a new unified hypothesis text. It identifies consensus, surfaces disagreements, and delivers an overall verdict. It does not simply concatenate or pick a winner.
- **D-09:** Overall confidence score in `SynthesisReport` = **weighted average** of the 3 analyst `confidence_score` values. Simple and transparent.

### Development Approach

- **D-10:** Phase 3 is developed against **mock data fixtures** — hardcoded `RepoData`, `NewsItem`, and `RAGContextChunk` objects built from the schema examples in `src/models/schemas.py`. Phase 3 does not wait for Phase 2 to be functional. Wire to real collection output when Phase 2 is ready.

### Claude's Discretion

- Exact Gemini prompt wording for each analyst and the critic
- Visualization library choice (matplotlib vs seaborn vs both)
- Chart styling, color palette, figure sizing
- How mock fixtures are organized (inline vs separate fixtures file)
- Error handling if one analyst fails (whether synthesis proceeds with 2)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data contracts
- `src/models/schemas.py` — All 5 Pydantic models. Analyst agents consume `RepoData`, `NewsItem`, `RAGContextChunk`. Each analyst emits `AnalystHypothesis`. Synthesis emits `SynthesisReport`.

### Requirements
- `.planning/REQUIREMENTS.md` §Analysis Layer — ANAL-01 through ANAL-06 (analyst agents + generator-critic loop)
- `.planning/REQUIREMENTS.md` §Synthesis & Output — SYNTH-01 through SYNTH-03 (synthesis agent + artifacts)
- `.planning/REQUIREMENTS.md` §Visualizations — VIZ-01 through VIZ-05 (4 charts + PNG download)

### Roadmap
- `.planning/ROADMAP.md` §Phase 3 — Success criteria (6 must-be-true conditions), plan breakdown (03-01: agents + loop, 03-02: synthesis + viz)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/models/schemas.py` — `AnalystHypothesis` and `SynthesisReport` are the output contracts. `RepoData`, `NewsItem`, `RAGContextChunk` are the input contracts. Schema examples provide realistic mock fixture values.

### Established Patterns
- Project uses **Google ADK** for all agent definitions — analyst agents and the critic must follow ADK patterns
- **Pydantic v2** throughout — use `model_validator`, not `validator`; use `Field(...)` for constraints
- **Async** for all ADK agent functions (project convention)
- **uv** for dependency management — `uv add` to add new packages, not pip
- Python 3.11, snake_case for files/functions, PascalCase for classes

### Integration Points
- Phase 3 output (`SynthesisReport`) is consumed by Phase 4 orchestrator and Streamlit frontend
- Phase 3 inputs come from Phase 2 collection agents — develop against mock fixtures until Phase 2 is ready
- `src/agents/analysis/` is Sindhuja's directory; `src/agents/synthesis_agent.py` is Sindhuja's file

</code_context>

<specifics>
## Specific Ideas

- Each analyst should feel like a distinct voice, not just a different label on the same output. The persona prompt is the key differentiator.
- The critic should be genuinely adversarial — not a rubber stamp. It should surface counter-evidence the analyst may have downweighted.
- Synthesis narrative should highlight where analysts agree (high confidence) and flag where they diverge (lower confidence, more uncertainty).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 3 scope.

</deferred>

---

*Phase: 03-analysis-layer*
*Context gathered: 2026-04-06*
