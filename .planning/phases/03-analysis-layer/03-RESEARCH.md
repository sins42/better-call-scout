# Phase 3: Analysis Layer - Research

**Researched:** 2026-04-06
**Domain:** Google ADK multi-agent pipelines, Gemini structured output, matplotlib/seaborn visualization, pytest fixtures
**Confidence:** MEDIUM-HIGH (ADK is actively developed; core patterns verified against official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** VC Analyst is decisive & contrarian — takes strong positions even when evidence is mixed. Produces clear "about to break out" or "overhyped" verdicts. Not balanced; not hedged.
- **D-02:** Developer Analyst is a pragmatic engineer — primary question is "Is this actually production-ready? Would I bet my team on it?" Focuses on DX, community health, and ecosystem maturity over metrics alone.
- **D-03:** Journalist Analyst is a tech media skeptic — asks "What's the real story vs the hype?" Looks for narrative arc, incumbent threats, and what's being undercovered by mainstream tech press.
- **D-04:** The critic is a separate ADK agent with its own system prompt. It acts as a devil's advocate — it does not share the analyst's perspective and is specifically prompted to challenge the hypothesis.
- **D-05:** Always 2 iterations — both rounds run regardless of confidence score. Consistency and reliability over latency optimization. Loop: analyst generates → critic challenges → analyst refines → commit.
- **D-06:** Each analyst runs its own independent generator-critic loop. The loops are not shared across analysts.
- **D-07:** All 3 analysts receive the full data pool — all RepoData, NewsItem, and RAGContextChunk objects. No pre-filtering between collection and analysis layers.
- **D-08:** The Synthesis Agent writes a new narrative layer — reads all 3 AnalystHypothesis objects and produces a new unified hypothesis text. It identifies consensus, surfaces disagreements, and delivers an overall verdict. It does not simply concatenate or pick a winner.
- **D-09:** Overall confidence score in SynthesisReport = weighted average of the 3 analyst confidence_score values.
- **D-10:** Phase 3 is developed against mock data fixtures — hardcoded RepoData, NewsItem, and RAGContextChunk objects built from the schema examples. Phase 3 does not wait for Phase 2 to be functional.

### Claude's Discretion

- Exact Gemini prompt wording for each analyst and the critic
- Visualization library choice (matplotlib vs seaborn vs both)
- Chart styling, color palette, figure sizing
- How mock fixtures are organized (inline vs separate fixtures file)
- Error handling if one analyst fails (whether synthesis proceeds with 2)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 3 scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANAL-01 | VC Analyst Agent scores repos on star velocity, market size signals, funding mentions, competitive landscape | LlmAgent with vc_analyst system prompt + output_schema=AnalystHypothesis |
| ANAL-02 | Developer Analyst Agent scores repos on ecosystem maturity, adoption phase, job posting signals, historical benchmarking | LlmAgent with developer_analyst system prompt + output_schema=AnalystHypothesis |
| ANAL-03 | Journalist Analyst Agent scores repos on narrative hook, HN sentiment/buzz, media coverage density, incumbent comparison | LlmAgent with journalist system prompt + output_schema=AnalystHypothesis |
| ANAL-04 | All 3 analyst agents run in parallel via ADK | ParallelAgent(sub_agents=[vc_analyst_pipeline, dev_analyst_pipeline, journalist_pipeline]) |
| ANAL-05 | Generator-Critic loop per analyst, max 2 iterations | LoopAgent(sub_agents=[analyst_agent, critic_agent], max_iterations=2) per analyst |
| ANAL-06 | Each analyst emits typed hypothesis JSON conforming to SCHEMA-04 | output_schema=AnalystHypothesis on the refiner LlmAgent |
| SYNTH-01 | Synthesis Agent merges 3 hypotheses into unified SynthesisReport | LlmAgent(output_schema=SynthesisReport) reading state keys from parallel outputs |
| SYNTH-02 | Synthesis Agent generates scout_report.md in-memory for download | io.StringIO + Markdown template in synthesis agent post-processing |
| SYNTH-03 | Synthesis Agent generates top_repos.csv in-memory for download | pandas DataFrame.to_csv(io.StringIO()) from SynthesisReport.top_repos |
| VIZ-01 | Star velocity line chart — top 10 repos, stars/week over 4-8 weeks | matplotlib line plot with weekly x-axis, seaborn styling |
| VIZ-02 | Category heatmap — tech categories x weeks, color = star velocity | seaborn.heatmap() with DataFrame pivot |
| VIZ-03 | HN Buzz vs GitHub Stars scatter — X=stars, Y=HN score | matplotlib.pyplot.scatter() or seaborn.scatterplot() |
| VIZ-04 | Persona score bar chart — side-by-side VC/Dev/Journalist confidence scores per repo | seaborn.barplot() or matplotlib grouped bars |
| VIZ-05 | All 4 charts downloadable as PNG | io.BytesIO + fig.savefig(buf, format='png') + buf.getvalue() |
</phase_requirements>

---

## Summary

Phase 3 builds three analyst agents (VC, Developer, Journalist) each running their own generator-critic refinement loop before a Synthesis Agent merges the three hypotheses into a final report. The codebase already has google-adk>=0.1.0, matplotlib 3.10.8, seaborn 0.13.2, and pandas 3.0.2 installed — no new core packages are required.

The primary ADK pattern is: `LlmAgent` (generator) + `LlmAgent` (critic) wrapped in `LoopAgent(max_iterations=2)` for each analyst. These three `LoopAgent` pipelines run inside a `ParallelAgent`. State flows between agents via `output_key` and `{state_key}` template injection in instructions. Structured output is enforced via `output_schema=AnalystHypothesis` on the final analyst LlmAgent in each loop.

The critical constraint: `output_schema` disables tools on the same agent (per ADK docs). Since analyst agents do not use ADK tools (they receive data via the instruction/prompt), this constraint does not apply here. The data is serialized into the instruction text as JSON.

**Primary recommendation:** Use `LoopAgent(max_iterations=2)` per analyst with `output_schema` on the refiner agent; run three LoopAgents in a `ParallelAgent`; pass results to the synthesis `LlmAgent` via session state keys.

---

## Standard Stack

### Core (already installed — verified via uv)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-adk | >=0.1.0 (1.28.1 installed) [VERIFIED: uv] | Agent orchestration framework | Project requirement; all agent definitions must use ADK |
| google-cloud-aiplatform | >=1.60.0 | Vertex AI backend for Gemini | Project requirement |
| pydantic | 2.x | Data models and structured output validation | Project-wide convention (v2 only) |
| matplotlib | 3.10.8 [VERIFIED: installed] | Chart rendering | Already installed; covers all 4 chart types |
| seaborn | 0.13.2 [VERIFIED: installed] | Heatmap and scatter styling | Already installed; seaborn.heatmap is easiest heatmap API |
| pandas | 3.0.2 [VERIFIED: installed] | DataFrame for heatmap pivot, CSV export | Already installed |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0.0 | Test runner | All tests via `uv run pytest` |
| pytest-asyncio | >=0.23.0 | Async test support | All async agent function tests; asyncio_mode="auto" already set |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LoopAgent(max_iterations=2) | SequentialAgent with 4 explicit sub-agents (gen1, critic1, gen2, commit) | SequentialAgent gives more explicit control; LoopAgent is idiomatic for refine loops and handles the fixed-count pattern cleanly |
| output_schema on refiner | Post-process LLM text output with json.loads + Pydantic.model_validate | Fragile; more error handling; output_schema is the idiomatic ADK way |
| matplotlib for heatmap | plotly | plotly adds a dependency; seaborn.heatmap is simpler for static PNG export |

**Installation:** No new packages required — all dependencies already in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure

```
src/agents/analysis/
├── __init__.py                    # already exists (stub)
├── vc_analyst.py                  # already exists (stub) — VC LlmAgents + LoopAgent
├── developer_analyst.py           # already exists (stub) — Dev LlmAgents + LoopAgent
├── journalist_analyst.py          # already exists (stub) — Journalist LlmAgents + LoopAgent
└── _prompts.py                    # NEW — system prompt constants for each persona + critic

src/agents/
├── synthesis_agent.py             # already exists (stub) — Synthesis LlmAgent
└── critic_agent.py                # already exists (stub) — Critic LlmAgent (shared)

src/visualization/
└── charts.py                      # already exists (stub) — 4 chart functions

tests/
├── conftest.py                    # NEW — shared mock fixtures (RepoData, NewsItem, RAGContextChunk)
├── test_analysis.py               # already exists (stub) — analysis layer tests
└── unit/
    └── test_schemas.py            # already exists and passing
```

### Pattern 1: LlmAgent Definition

The canonical ADK agent definition for an analyst:

```python
# Source: https://adk.dev/agents/llm-agents/
from google.adk.agents import LlmAgent
from src.models.schemas import AnalystHypothesis

vc_refiner_agent = LlmAgent(
    name="VCAnalystRefiner",
    model="gemini-2.0-flash",
    instruction="""You are a decisive, contrarian VC analyst.
...
Repo data: {repo_data_json}
Critic feedback: {vc_critic_output}
Previous hypothesis: {vc_draft_output}

Return a refined JSON conforming to the AnalystHypothesis schema.""",
    output_schema=AnalystHypothesis,
    output_key="vc_hypothesis_final",
)
```

Key rules:
- `output_schema` accepts the Pydantic class directly (not an instance). [VERIFIED: adk.dev/agents/llm-agents]
- `output_key` stores the structured output as a dict in session state. [VERIFIED: adk.dev/agents/llm-agents]
- `{state_key}` placeholders in `instruction` are resolved automatically by ADK from session state before the LLM call. [VERIFIED: adk.dev/sessions/state]

### Pattern 2: Generator-Critic LoopAgent (2 fixed iterations, D-05)

```python
# Source: https://adk.dev/agents/workflow-agents/loop-agents/
from google.adk.agents import LlmAgent, LoopAgent

vc_generator = LlmAgent(
    name="VCAnalystGenerator",
    model="gemini-2.0-flash",
    instruction="""You are a decisive, contrarian VC analyst.
Repo data: {repo_data_json}
Previous critique (empty on first pass): {vc_critic_output}
...
Return JSON conforming to AnalystHypothesis.""",
    output_schema=AnalystHypothesis,
    output_key="vc_draft_output",
)

vc_critic = LlmAgent(
    name="VCCritic",
    model="gemini-2.0-flash",
    instruction="""You are an adversarial devil's advocate critic.
Challenge this hypothesis: {vc_draft_output}
List specific counter-evidence and weaknesses. Be adversarial.""",
    output_key="vc_critic_output",
)

vc_analyst_loop = LoopAgent(
    name="VCAnalystLoop",
    sub_agents=[vc_generator, vc_critic],
    max_iterations=2,
)
```

Why `LoopAgent` over `SequentialAgent` with 4 sub-agents: `LoopAgent(max_iterations=2)` runs [generator, critic] twice, naturally encoding the D-05 requirement. `SequentialAgent([gen, critic, gen, critic])` would require duplicating agent definitions or using the same instance twice (which may cause state key collisions). [VERIFIED: adk.dev/agents/workflow-agents/loop-agents]

**Important loop structure note:** With `max_iterations=2`, the sequence runs: gen(iter1) → critic(iter1) → gen(iter2) → critic(iter2). This gives the analyst two chances to refine. The final `output_key="vc_draft_output"` holds the last generator output after both iterations. If only the final analyst output (not the final critic output) is wanted, read `vc_draft_output` from state after the loop completes.

### Pattern 3: Parallel Analyst Execution (ANAL-04)

```python
# Source: https://adk.dev/agents/workflow-agents/parallel-agents/
from google.adk.agents import ParallelAgent

analysis_layer = ParallelAgent(
    name="AnalysisLayer",
    sub_agents=[
        vc_analyst_loop,       # output_key="vc_draft_output"
        dev_analyst_loop,      # output_key="dev_draft_output"
        journalist_loop,       # output_key="journalist_draft_output"
    ],
)
```

Critical constraint: sub-agents in a `ParallelAgent` do NOT share state during execution — each runs in an isolated branch. State written by one sub-agent is NOT visible to sibling sub-agents during the parallel run. After the `ParallelAgent` completes, all output keys are merged back into the shared session state. [VERIFIED: adk.dev/agents/workflow-agents/parallel-agents]

This means: each analyst loop is fully self-contained. The synthesis agent, which runs after the `ParallelAgent`, reads `vc_draft_output`, `dev_draft_output`, and `journalist_draft_output` from the unified session state.

### Pattern 4: Synthesis Agent

```python
from google.adk.agents import LlmAgent
from src.models.schemas import SynthesisReport

synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model="gemini-2.0-flash",
    instruction="""You are the synthesis layer of a VC scout pipeline.
You have three analyst hypotheses:

VC Analyst: {vc_draft_output}
Developer Analyst: {dev_draft_output}
Journalist: {journalist_draft_output}

Write a unified narrative that:
1. Identifies where all 3 analysts agree (high confidence signals)
2. Flags where analysts disagree (lower confidence areas)
3. Delivers an overall verdict

Return JSON conforming to SynthesisReport schema.""",
    output_schema=SynthesisReport,
    output_key="synthesis_report",
)
```

Note: `SynthesisReport` contains `hypotheses: list[AnalystHypothesis]`. The synthesis agent's `output_schema=SynthesisReport` will tell Gemini to produce a JSON with nested hypothesis objects. The instruction must be explicit about the expected structure, as Gemini may struggle with deeply nested schemas. Mitigation: include the full JSON schema in the instruction as a comment/example.

### Pattern 5: Agent Invocation (for tests and standalone runs)

```python
# Source: https://www.leoniemonigatti.com/blog/building-ai-agents-with-google-adk.html (verified pattern)
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="better-call-scout",
    session_service=session_service,
)

session = await session_service.create_session(
    app_name="better-call-scout",
    user_id="dev",
    session_id="test-session-1",
    state={"repo_data_json": serialized_mock_data},  # pre-seed state
)

async for event in runner.run_async(
    user_id="dev",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="analyze")]),
):
    if event.is_final_response():
        result = event.content
```

For Phase 3, the agents primarily read from session state (pre-seeded with mock data) rather than from the user message. The `new_message` is a trigger; the actual data payload is in session state set at session creation or by a preceding agent.

### Pattern 6: Passing Data Into the Pipeline

Since analysts receive the full data pool (D-07), serialize the mock data into session state before running:

```python
import json
from src.models.schemas import RepoData, NewsItem, RAGContextChunk

# Serialize to JSON strings for state injection
state = {
    "repo_data_json": json.dumps([r.model_dump(mode="json") for r in repos]),
    "news_items_json": json.dumps([n.model_dump(mode="json") for n in news]),
    "rag_chunks_json": json.dumps([c.model_dump(mode="json") for c in chunks]),
    "vc_critic_output": "",      # empty on first iteration
    "dev_critic_output": "",
    "journalist_critic_output": "",
}
```

### Pattern 7: In-Memory PNG Export

```python
import io
import matplotlib
matplotlib.use("Agg")  # Must be called before pyplot import — non-interactive, thread-safe
import matplotlib.pyplot as plt
import seaborn as sns

def render_chart_as_png(fig: plt.Figure) -> bytes:
    """Export a matplotlib Figure to PNG bytes.

    Args:
        fig: The matplotlib Figure to export.

    Returns:
        PNG image bytes suitable for st.download_button or HTTP response.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    return buf.getvalue()
```

The `matplotlib.use("Agg")` call must appear at module import time, before any `import matplotlib.pyplot as plt`. In an async environment (ADK is async), the Agg backend avoids GUI thread requirements. [VERIFIED: matplotlib.org/stable/users/explain/figure/backends.html]

**Thread-safety note:** matplotlib is not fully thread-safe. Generate charts in a single async function (not across concurrent coroutines) or use a thread lock if generating multiple charts simultaneously. The simplest approach for Phase 3: generate all 4 charts sequentially in one function, even though the analysis agents run in parallel.

### Anti-Patterns to Avoid

- **Using `plt.show()` in server context:** Call `fig.savefig()` directly; `plt.show()` requires a GUI backend.
- **Sharing agent output_key names across parallel sub-agents:** Each analyst must have unique output_key names (`vc_draft_output`, `dev_draft_output`, `journalist_draft_output`) to avoid state key collisions.
- **Putting tools on agents that use output_schema:** The combination blocks structured output in many ADK versions. Since analysts don't need ADK tools (data is in the prompt), avoid adding tools to analyst LlmAgents.
- **Using `validator` in Pydantic models:** Project convention requires `model_validator`. Existing schemas already use this correctly.
- **Deeply nested schema without examples in the prompt:** Gemini may return malformed JSON for `SynthesisReport` (nested list of `AnalystHypothesis`). Include a minimal JSON example in the synthesis instruction.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured JSON output enforcement | Custom JSON parsing + regex on LLM text | `output_schema=AnalystHypothesis` on LlmAgent | ADK calls `model.model_json_schema()` and passes it as Gemini `response_schema`; handles edge cases automatically |
| Parallel async agent execution | `asyncio.gather()` with raw Gemini API calls | `ParallelAgent(sub_agents=[...])` | ADK handles concurrent execution, state merging, error propagation |
| Fixed-count refinement loop | Manual `for i in range(2)` calling agent functions | `LoopAgent(max_iterations=2)` | Idiomatic ADK; handles state propagation between iterations |
| PNG export | PIL/Pillow image conversion | `fig.savefig(io.BytesIO(), format='png')` | matplotlib's built-in; no additional dependency |
| CSV generation | Manual string building | `pd.DataFrame([r.model_dump() for r in repos]).to_csv(io.StringIO())` | pandas already installed; one-liner |

**Key insight:** ADK's workflow agents (`LoopAgent`, `ParallelAgent`, `SequentialAgent`) are the orchestration layer. Never re-implement orchestration logic in Python — use the ADK primitives.

---

## Common Pitfalls

### Pitfall 1: output_schema + tools conflict

**What goes wrong:** Adding ADK tools to an LlmAgent that also has `output_schema` set causes structured output to be silently ignored — the agent returns free-text instead of JSON.
**Why it happens:** Most Gemini models cannot simultaneously use function calling (tools) and response_schema in the same request.
**How to avoid:** Keep analyst agents tool-free. All input data is serialized into the instruction via `{state_key}` placeholders. The critic agent also has no tools — it only reads and comments on text.
**Warning signs:** Agent returns a text response instead of JSON; Pydantic validation fails at state read time.

### Pitfall 2: LoopAgent state key collision across parallel branches

**What goes wrong:** If VC and Developer analysts both use `output_key="draft_output"`, the ParallelAgent merges state at the end and one overwrites the other.
**Why it happens:** State is a flat dict; parallel branches write to the same session state namespace.
**How to avoid:** Use persona-prefixed output keys: `vc_draft_output`, `vc_critic_output`, `dev_draft_output`, `dev_critic_output`, `journalist_draft_output`, `journalist_critic_output`.
**Warning signs:** Synthesis agent receives the same hypothesis text for 2+ personas.

### Pitfall 3: Matplotlib backend not set before pyplot import

**What goes wrong:** On a headless server (Cloud Run, CI), matplotlib tries to use a GUI backend and raises `cannot connect to X server` or similar errors.
**Why it happens:** Default matplotlib backend selection depends on environment; servers lack display servers.
**How to avoid:** Call `matplotlib.use("Agg")` at the top of `charts.py`, before `import matplotlib.pyplot as plt`. This must be the first matplotlib call.
**Warning signs:** `UserWarning: Matplotlib is currently using agg, which is a non-GUI backend` on local; `RuntimeError` on Cloud Run.

### Pitfall 4: SynthesisReport nested schema confuses Gemini

**What goes wrong:** Gemini produces malformed JSON for `SynthesisReport` because `hypotheses: list[AnalystHypothesis]` is a deeply nested structure.
**Why it happens:** Gemini's `response_schema` with nested Pydantic models can produce incomplete or re-ordered fields.
**How to avoid:** (1) Include a minimal valid JSON example in the synthesis instruction string. (2) Add a fallback: if `model_validate()` fails on the first pass, parse the three hypothesis state keys directly and construct `SynthesisReport` in Python code rather than relying on the LLM to produce the full structure.
**Warning signs:** `pydantic.ValidationError` when reading `synthesis_report` from session state.

### Pitfall 5: mock data not pre-seeded into session state

**What goes wrong:** Analyst agents receive empty `{repo_data_json}` placeholders because the state was not populated before the `runner.run_async()` call.
**Why it happens:** ADK's `{key}` template substitution silently replaces missing keys with empty strings rather than raising an error.
**How to avoid:** Always initialize session with `state={...}` containing all required keys when calling `session_service.create_session()`. Validate that `state["repo_data_json"]` is non-empty before calling the pipeline.
**Warning signs:** Analyst produces a generic response with no mention of specific repos or metrics.

### Pitfall 6: gemini-2.0-flash availability

**What goes wrong:** As of 2026, `gemini-2.0-flash-001` is only available for existing GCP projects. New projects must use `gemini-2.5-flash` or later.
**Why it happens:** Google deprecated broad access to 2.0 Flash in March 2026.
**How to avoid:** The project's GOOGLE_CLOUD_PROJECT env var determines availability. If running against a new GCP project, use `"gemini-2.5-flash"` as the model string. Make the model name configurable via environment variable or a constant in `_prompts.py`.
**Warning signs:** `404 Not Found` or `Model not found` error from Vertex AI.

---

## Code Examples

### Chart 1: Star Velocity Line Chart (VIZ-01)

```python
# Source: matplotlib.org official docs (pattern verified)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io

def star_velocity_line_chart(repos: list[dict], weeks: list[str]) -> bytes:
    """Top-10 repos star velocity over time as a line chart.

    Args:
        repos: List of dicts with 'name' and per-week velocity values keyed by week.
        weeks: List of week label strings (x-axis).

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    for repo in repos[:10]:
        velocities = [repo.get(w, 0) for w in weeks]
        ax.plot(weeks, velocities, marker="o", label=repo["name"])
    ax.set_xlabel("Week")
    ax.set_ylabel("Star Velocity (stars_last_7d / total_stars)")
    ax.set_title("Top 10 Repos: Star Velocity Over Time")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()
```

### Chart 2: Category Heatmap (VIZ-02)

```python
import seaborn as sns
import pandas as pd

def category_heatmap(data: dict[str, dict[str, float]], weeks: list[str]) -> bytes:
    """Heatmap of star velocity by tech category x week.

    Args:
        data: {category: {week: velocity}} nested dict.
        weeks: Week labels for x-axis ordering.

    Returns:
        PNG image bytes.
    """
    df = pd.DataFrame(data, index=weeks).T  # categories as rows, weeks as columns
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(df, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax)
    ax.set_title("Tech Category Star Velocity Heatmap")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()
```

### Chart 3: HN Buzz vs GitHub Stars Scatter (VIZ-03)

```python
def hn_buzz_scatter(repos: list[dict]) -> bytes:
    """Scatter: X=GitHub stars, Y=HN score. Spots gems (high HN, low stars) and hype traps.

    Args:
        repos: List of dicts with 'name', 'stars', 'hn_score'.

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    xs = [r["stars"] for r in repos]
    ys = [r.get("hn_score", 0.0) for r in repos]
    labels = [r["name"].split("/")[-1] for r in repos]
    ax.scatter(xs, ys, alpha=0.7)
    for x, y, label in zip(xs, ys, labels):
        ax.annotate(label, (x, y), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("GitHub Stars")
    ax.set_ylabel("HN Score")
    ax.set_title("HN Buzz vs GitHub Stars")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()
```

### Chart 4: Persona Score Bar Chart (VIZ-04)

```python
def persona_score_bars(repos: list[dict], scores: dict[str, dict[str, float]]) -> bytes:
    """Side-by-side bar chart: VC/Dev/Journalist confidence_score per repo.

    Args:
        repos: List of repo name dicts.
        scores: {repo_name: {persona: confidence_score}}.

    Returns:
        PNG image bytes.
    """
    import numpy as np
    personas = ["vc_analyst", "developer_analyst", "journalist"]
    repo_names = [r["name"].split("/")[-1] for r in repos[:10]]
    x = np.arange(len(repo_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(14, 6))
    for i, persona in enumerate(personas):
        vals = [scores.get(r["name"], {}).get(persona, 0.0) for r in repos[:10]]
        ax.bar(x + i * width, vals, width, label=persona.replace("_", " ").title())
    ax.set_xticks(x + width)
    ax.set_xticklabels(repo_names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Confidence Score")
    ax.set_title("Analyst Confidence Scores by Repo")
    ax.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()
```

### Mock Fixture Pattern (conftest.py)

```python
# Source: pytest official docs — conftest.py auto-discovered by pytest in tests/
import pytest
from datetime import datetime, timezone
from src.models.schemas import RepoData, NewsItem, RAGContextChunk

@pytest.fixture
def mock_repos() -> list[RepoData]:
    """Three representative RepoData objects covering high/medium/low star velocity."""
    return [
        RepoData(
            name="langchain-ai/langchain",
            url="https://github.com/langchain-ai/langchain",
            stars=85000, star_velocity=0.42, commits=312,
            contributors=148, issues=520,
            topics=["llm", "agents", "python"], language="Python",
        ),
        RepoData(
            name="microsoft/autogen",
            url="https://github.com/microsoft/autogen",
            stars=32000, star_velocity=0.18, commits=95,
            contributors=62, issues=210,
            topics=["agents", "llm"], language="Python",
        ),
        RepoData(
            name="run-llama/llama_index",
            url="https://github.com/run-llama/llama_index",
            stars=28000, star_velocity=0.11, commits=188,
            contributors=95, issues=340,
            topics=["rag", "llm"], language="Python",
        ),
    ]

@pytest.fixture
def mock_news() -> list[NewsItem]:
    """Two NewsItem objects covering HN and Tavily sources."""
    return [
        NewsItem(
            title="Show HN: LangChain hits 85k stars",
            url="https://news.ycombinator.com/item?id=12345",
            source="hackernews", score=0.87,
            content="LangChain crossed 85,000 GitHub stars...",
            published_at=datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        NewsItem(
            title="AutoGen raises $20M Series A",
            url="https://techcrunch.com/autogen-series-a",
            source="tavily", score=0.73,
            content="Microsoft-backed AutoGen announced a $20M raise...",
            published_at=datetime(2024, 2, 10, 9, 0, 0, tzinfo=timezone.utc),
        ),
    ]

@pytest.fixture
def mock_rag_chunks() -> list[RAGContextChunk]:
    """Two RAGContextChunk objects representing historical knowledge."""
    return [
        RAGContextChunk(
            text="LangChain saw 300% growth in GitHub stars over Q1 2024.",
            source="chroma://scout-corpus/doc-42",
            metadata={"chunk_index": 2, "token_count": 128},
        ),
        RAGContextChunk(
            text="Agent frameworks are the fastest-growing open-source category in H1 2024.",
            source="chroma://scout-corpus/doc-7",
            metadata={"chunk_index": 0, "token_count": 95},
        ),
    ]
```

### Mock Data Serialization for State Pre-seeding

```python
import json

def build_pipeline_state(
    repos: list[RepoData],
    news: list[NewsItem],
    chunks: list[RAGContextChunk],
) -> dict[str, str]:
    """Serialize mock data pool into session state dict for ADK pipeline.

    Args:
        repos: Collection of RepoData objects.
        news: Collection of NewsItem objects.
        chunks: Collection of RAGContextChunk objects.

    Returns:
        State dict with JSON-serialized data and empty critic placeholders.
    """
    return {
        "repo_data_json": json.dumps([r.model_dump(mode="json") for r in repos]),
        "news_items_json": json.dumps([n.model_dump(mode="json") for n in news]),
        "rag_chunks_json": json.dumps([c.model_dump(mode="json") for c in chunks]),
        "vc_draft_output": "",
        "vc_critic_output": "",
        "dev_draft_output": "",
        "dev_critic_output": "",
        "journalist_draft_output": "",
        "journalist_critic_output": "",
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom asyncio orchestration with raw Gemini SDK | ADK ParallelAgent / LoopAgent / SequentialAgent | Google Cloud NEXT 2025 | No manual async coordination needed |
| pydantic `validator` decorator | pydantic `model_validator` (v2) | Pydantic v2 (2023) | Existing schemas already correct; don't use `@validator` |
| `plt.savefig('file.png')` | `fig.savefig(io.BytesIO(), format='png')` | Always available | In-memory export avoids disk I/O; required for serverless |
| gemini-2.0-flash (deprecated access) | gemini-2.5-flash for new projects | March 2026 | Make model name configurable |

**Deprecated/outdated:**
- `from pydantic import validator`: replaced by `model_validator`. Already avoided in this project.
- `plt.show()` in server context: use `fig.savefig()` to BytesIO instead.
- `google-adk` `Agent` class alias: use `LlmAgent` directly from `google.adk.agents`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `output_schema` limitation (no tools on same agent) has been "lifted" in recent ADK versions per one search result | Pitfall 1 | If lifted, pitfall description is overly cautious but still safe to follow |
| A2 | `LoopAgent` with `max_iterations=2` runs each sub-agent exactly 2 times (gen + critic = 2 full cycles) | Architecture Pattern 2 | If `max_iterations` counts total agent calls (4) vs. cycles (2), loop count needs adjustment |
| A3 | Session state pre-seeded via `create_session(state={...})` is visible to `{key}` placeholders in agent instructions | Architecture Pattern 5 | If state must be injected differently (e.g., via a SequentialAgent preceding the parallel group), the invocation pattern changes |
| A4 | `gemini-2.0-flash` is accessible on the project's GCP account (not a new project) | Architecture Pattern 1 | Use `gemini-2.5-flash` if 404 errors appear |

---

## Open Questions

1. **Does `LoopAgent` count iterations as (generator + critic = 1 cycle) or (each agent call = 1 iteration)?**
   - What we know: ADK docs say "the loop runs at most N iterations"; examples show [gen, critic] as two sub-agents with `max_iterations=5` producing 5 gen+critic cycles.
   - What's unclear: Whether `max_iterations=2` gives 2 gen+critic cycles (desired: D-05) or 1 gen+critic + 1 gen only.
   - Recommendation: Test with `max_iterations=2` and a logging tool in each sub-agent to confirm cycle count. If 1 cycle only, use `max_iterations=2` (which gives 2 gen+critic cycles, matching D-05). If 1 full cycle per iteration, keep `max_iterations=2`.

2. **How to handle synthesis when output_schema=SynthesisReport produces malformed JSON from Gemini?**
   - What we know: Deeply nested Pydantic schemas in `response_schema` can cause Gemini to produce incomplete JSON.
   - What's unclear: How often this occurs with `gemini-2.0-flash` specifically.
   - Recommendation: Build a Python fallback in the synthesis agent file — if `model_validate()` raises, manually construct `SynthesisReport` from the three analyst state keys and a simpler string-only synthesis hypothesis.

3. **What confidence_score weighting to use for SynthesisReport (D-09)?**
   - What we know: D-09 says weighted average of 3 confidence_score values; "simple and transparent."
   - What's unclear: Equal weights (1/3 each) or persona-weighted (e.g., VC has higher weight for market signals)?
   - Recommendation: Use equal weights (1/3 each) unless otherwise specified. Compute in Python post-synthesis: `sum(h.confidence_score for h in report.hypotheses) / len(report.hypotheses)`. Note: SynthesisReport does not currently have an `overall_confidence` field in the schema — this may need to be added or computed separately.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| google-adk | All ADK agents | ✓ (installed) | 1.28.1 [VERIFIED: uv] | — |
| matplotlib | VIZ-01 to VIZ-05 | ✓ | 3.10.8 [VERIFIED] | — |
| seaborn | VIZ-02 (heatmap) | ✓ | 0.13.2 [VERIFIED] | matplotlib-only heatmap |
| pandas | VIZ-02, SYNTH-03 | ✓ | 3.0.2 [VERIFIED] | — |
| pytest-asyncio | async tests | ✓ (in dev deps) | >=0.23.0 | — |
| GOOGLE_CLOUD_PROJECT env var | Vertex AI auth | Unverified | — | Must be set in .env |
| GOOGLE_GENAI_USE_VERTEXAI | Vertex AI mode | Unverified | Must be "TRUE" | Google AI Studio fallback |

**Missing dependencies with no fallback:**
- `GOOGLE_CLOUD_PROJECT` and `GOOGLE_GENAI_USE_VERTEXAI=TRUE` must be set in `.env` before any agent can execute against Vertex AI. Without these, all ADK agent calls fail at auth time.

**Missing dependencies with fallback:**
- seaborn: if removed, the category heatmap can be built with `matplotlib.pyplot.imshow()` on a 2D array — more code but same result.

---

## File Structure Recommendation

Files to create (stubs already exist for most):

| File | Action | Purpose |
|------|--------|---------|
| `src/agents/analysis/_prompts.py` | CREATE NEW | System prompt string constants for all 3 analyst personas and the critic. Centralizes prompt wording, easy to iterate. |
| `src/agents/analysis/vc_analyst.py` | IMPLEMENT STUB | `vc_generator`, `vc_critic`, `vc_analyst_loop = LoopAgent(...)` |
| `src/agents/analysis/developer_analyst.py` | IMPLEMENT STUB | `dev_generator`, `dev_critic`, `dev_analyst_loop = LoopAgent(...)` |
| `src/agents/analysis/journalist_analyst.py` | IMPLEMENT STUB | `journalist_generator`, `journalist_critic`, `journalist_loop = LoopAgent(...)` |
| `src/agents/synthesis_agent.py` | IMPLEMENT STUB | `synthesis_agent = LlmAgent(output_schema=SynthesisReport)` + markdown/CSV export functions |
| `src/visualization/charts.py` | IMPLEMENT STUB | `star_velocity_line_chart()`, `category_heatmap()`, `hn_buzz_scatter()`, `persona_score_bars()` — all return `bytes` |
| `tests/conftest.py` | CREATE NEW | `mock_repos`, `mock_news`, `mock_rag_chunks` fixtures shared across test files |
| `tests/test_analysis.py` | IMPLEMENT STUB | Tests for each analyst agent (mock invocation + Pydantic validation) |

---

## Sources

### Primary (HIGH confidence)
- [adk.dev/agents/llm-agents/](https://adk.dev/agents/llm-agents/) — LlmAgent parameters, output_schema, output_key, instruction templates
- [adk.dev/agents/workflow-agents/parallel-agents/](https://adk.dev/agents/workflow-agents/parallel-agents/) — ParallelAgent constructor, state isolation during parallel execution
- [adk.dev/agents/workflow-agents/sequential-agents/](https://adk.dev/agents/workflow-agents/sequential-agents/) — SequentialAgent, shared InvocationContext, state passing
- [adk.dev/agents/workflow-agents/loop-agents/](https://adk.dev/agents/workflow-agents/loop-agents/) — LoopAgent max_iterations, early exit via escalate
- [adk.dev/agents/models/google-gemini/](https://adk.dev/agents/models/google-gemini/) — Gemini 2.0 Flash model string, Vertex AI auth setup
- [matplotlib.org/stable/users/explain/figure/backends.html](https://matplotlib.org/stable/users/explain/figure/backends.html) — Agg backend, thread safety
- `src/models/schemas.py` — AnalystHypothesis, SynthesisReport field definitions [VERIFIED: codebase]
- `pyproject.toml` — all installed dependencies and versions [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- [leoniemonigatti.com/blog/building-ai-agents-with-google-adk.html](https://www.leoniemonigatti.com/blog/building-ai-agents-with-google-adk.html) — Runner, InMemorySessionService, run_async pattern (verified against official docs structure)
- [saptak.in/writing/2025/05/10/google-adk-masterclass-part4](https://saptak.in/writing/2025/05/10/google-adk-masterclass-part4) — output_schema Pydantic pattern (corroborated by official docs)
- [github.com/google/adk-python issues #3969, #217](https://github.com/google/adk-python/issues/3969) — output_schema + tools limitation; recent reports it may be lifted

### Tertiary (LOW confidence)
- GitHub issue discussion that "output_schema + tools limitation has been lifted" in recent ADK — single source, not in official docs. Treat as unverified.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed via uv; ADK version confirmed
- Architecture (ADK patterns): MEDIUM-HIGH — verified against official adk.dev docs; specific LoopAgent iteration counting needs testing
- Pitfalls: MEDIUM — output_schema/tools conflict verified; LoopAgent state key collision is logical inference from parallel agent behavior
- Visualization: HIGH — matplotlib/seaborn patterns are stable; BytesIO export is well-established

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (ADK is actively developed; check adk.dev for breaking changes if planning beyond this date)
