# Phase 4: Integration + Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-10
**Phase:** 04-integration-frontend
**Mode:** discuss
**Areas analyzed:** Orchestrator interface, Progress UX, Persona selection scope, Results layout

---

## Areas Discussed

### Orchestrator Interface

| Question | Options Presented | Answer |
|----------|------------------|--------|
| Frontend stack | FastAPI + plain HTML/CSS/JS, Streamlit (original), Gradio | **FastAPI + plain HTML/CSS/JS** (user-initiated — wanted more design freedom than Streamlit) |
| Orchestrator API endpoint | POST /run → JSON SynthesisReport, POST /run → JSON with base64 charts | **POST /run → JSON SynthesisReport** |
| Persona scope at API level | Always run all 3 / filter display only, Pass selected personas / run only those | **Always run all 3, filter display only** |

**Key correction:** User rejected Streamlit (planned in requirements) in favor of FastAPI + plain HTML/CSS/JS for design freedom. All FE-01 through FE-06 requirements still apply — only the implementation technology changed.

---

### Progress UX

| Question | Options Presented | Answer |
|----------|------------------|--------|
| Progress during pipeline run | SSE streaming status, Simple spinner + elapsed timer, Polling endpoint | **SSE streaming status updates** |
| Pipeline failure handling | Show error message + retry button, You decide | **Error message + retry button** |

---

### Persona Selection Scope

| Question | Options Presented | Answer |
|----------|------------------|--------|
| What persona multi-select controls | Which tabs are shown in results, Default all selected / user can deselect | **Which tabs are shown (always run all 3)** |

---

### Results Layout — Visual Style

| Question | Options Presented | Answer |
|----------|------------------|--------|
| Overall visual vibe | Dark/techy, Clean/light/modern, Bold/editorial | **Clean, light, modern** (SaaS aesthetic — white, cards, pill tabs) |
| Persona accent colors | Persona-specific (VC=indigo, Dev=emerald, Journalist=amber), Single brand color, You decide | **Persona-specific accent colors** |
| Page structure | Single scrolling page, Two-column dashboard | **Single scrolling page** |
| Chart display | 2×2 grid, Horizontal scroll strip, You decide | **2×2 responsive grid** |

### Results Layout — Tab Content

| Question | Options Presented | Answer |
|----------|------------------|--------|
| Tab content | Hypothesis + confidence badge + evidence list, Hypothesis text only, You decide | **Hypothesis text + confidence badge + evidence list** |
| Chart placement | Shared panel below tabs, Inside each tab, Separate Charts tab | **Shared panel below all tabs** |
| Download placement | Download bar above charts, Sticky footer, You decide | **Download bar above charts panel** |

---

## Corrections Made

### Streamlit → FastAPI + plain HTML/CSS/JS
- **Original plan:** Streamlit frontend (FE-01 through FE-06 in REQUIREMENTS.md)
- **User correction:** FastAPI + plain HTML/CSS/JS — "I do not want to use Streamlit. I want to build it using something that allows more design freedom"
- **Impact:** FastAPI is natively async (no asyncio bridging needed). Deployment unchanged (uvicorn on port 8080 → Cloud Run). All FE functional requirements still apply.

---

## No Deferred Ideas

Discussion stayed within Phase 4 scope.
