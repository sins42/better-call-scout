"""Synthesis Agent (Person 2: Sindhuja)

Merges 3 analyst hypotheses into unified report.
Generates scout_report.md and top_repos.csv for download.
"""
import io
import json
import logging
from datetime import datetime, timezone

import pandas as pd
from google.adk.agents import LlmAgent
from src.agents.analysis._prompts import GEMINI_MODEL, RETRY_CONFIG
from src.models.schemas import AnalystHypothesis, RepoData, SynthesisReport

logger = logging.getLogger(__name__)

# Minimal JSON example embedded in the instruction to help Gemini produce
# valid nested structure (mitigates Pitfall 4 — nested schema confusion).
_SYNTHESIS_SCHEMA_EXAMPLE = json.dumps(
    SynthesisReport.model_config["json_schema_extra"]["example"],
    indent=2,
)

_SYNTHESIS_INSTRUCTION = f"""You are the synthesis layer of a VC/startup scout pipeline.

You have received three independent analyst hypotheses:

VC Analyst hypothesis: {{vc_draft_output}}
Developer Analyst hypothesis: {{dev_draft_output}}
Journalist hypothesis: {{journalist_draft_output}}

The original scout query is: {{query}}

Your task (per D-08):
1. Identify where all 3 analysts agree — these are high-confidence signals.
2. Flag where analysts diverge — these are uncertainty zones.
3. Synthesize the top repositories from all hypotheses into a ranked top_repos list.
4. Write a new unified narrative in hypothesis_text that is NOT a concatenation.
   Deliver a clear overall verdict.

Return a JSON object exactly matching this schema. Do not include extra keys.
Example structure:
{_SYNTHESIS_SCHEMA_EXAMPLE}

IMPORTANT: The hypotheses list must contain all 3 analyst hypothesis objects as provided above,
with their persona fields set to "vc_analyst", "developer_analyst", and "journalist" respectively.
The top_repos list must include the top repositories from the data.
"""

synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model=GEMINI_MODEL,
    instruction=_SYNTHESIS_INSTRUCTION,
    output_schema=SynthesisReport,
    output_key="synthesis_report",
    generate_content_config=RETRY_CONFIG,
)


def build_synthesis_report_from_state(
    state: dict,
    query: str,
    repos: list[RepoData],
) -> SynthesisReport:
    """Construct SynthesisReport directly from session state if Gemini output is malformed.

    Args:
        state: ADK session state dict after analysis_layer completes.
        query: The original user scout query.
        repos: List of RepoData objects from the collection layer.

    Returns:
        SynthesisReport with the three analyst hypotheses and top repos.

    Raises:
        ValueError: If any required hypothesis key is missing or invalid in state.
    """
    hypotheses: list[AnalystHypothesis] = []
    for key in ("vc_draft_output", "dev_draft_output", "journalist_draft_output"):
        raw = state.get(key)
        if not raw:
            raise ValueError(f"State key '{key}' is empty — analyst loop may not have completed")
        if isinstance(raw, dict):
            hypothesis = AnalystHypothesis.model_validate(raw)
        elif isinstance(raw, str):
            hypothesis = AnalystHypothesis.model_validate_json(raw)
        else:
            raise ValueError(f"State key '{key}' has unexpected type {type(raw)}")
        hypotheses.append(hypothesis)

    # Sort repos by star_velocity descending, take top 10
    top_repos = sorted(repos, key=lambda r: r.star_velocity, reverse=True)[:10]

    return SynthesisReport(
        query=query,
        hypotheses=hypotheses,
        top_repos=top_repos,
        generated_at=datetime.now(timezone.utc),
    )


def generate_scout_report_md(report: SynthesisReport) -> str:
    """Generate a Markdown scout report from a SynthesisReport.

    Args:
        report: The completed SynthesisReport from the synthesis agent.

    Returns:
        Markdown string suitable for in-memory download as scout_report.md.
    """
    lines: list[str] = [
        f"# Scout Report",
        f"",
        f"**Query:** {report.query}",
        f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"---",
        f"",
        f"## Analyst Perspectives",
        f"",
    ]
    for hypothesis in report.hypotheses:
        lines += [
            f"### {hypothesis.persona.replace('_', ' ').title()}",
            f"",
            f"**Confidence:** {hypothesis.confidence_score:.0%}",
            f"",
            f"**Hypothesis:** {hypothesis.hypothesis_text}",
            f"",
            f"**Reasoning:** {hypothesis.reasoning}",
            f"",
            f"**Supporting Evidence:**",
        ]
        for point in hypothesis.evidence:
            lines.append(f"- {point}")
        lines += ["", "**Counter-Evidence:**"]
        for point in hypothesis.counter_evidence:
            lines.append(f"- {point}")
        lines.append("")

    # Overall confidence = weighted average (equal weights, D-09)
    if report.hypotheses:
        overall = sum(h.confidence_score for h in report.hypotheses) / len(report.hypotheses)
        lines += [
            "---",
            "",
            f"## Overall Confidence Score",
            "",
            f"**{overall:.0%}** (equal-weighted average of {len(report.hypotheses)} analyst scores)",
            "",
        ]

    lines += [
        "---",
        "",
        "## Top Repositories",
        "",
        "| Repo | Stars | Star Velocity | Language |",
        "| ---- | ----- | ------------- | -------- |",
    ]
    for repo in report.top_repos:
        lines.append(
            f"| [{repo.name}]({repo.url}) | {repo.stars:,} | {repo.star_velocity:+.2f} | {repo.language or 'N/A'} |"
        )

    return "\n".join(lines)


def generate_top_repos_csv(report: SynthesisReport) -> str:
    """Generate a CSV string of top repositories from a SynthesisReport.

    Args:
        report: The completed SynthesisReport.

    Returns:
        CSV string suitable for in-memory download as top_repos.csv.
    """
    if not report.top_repos:
        return "name,url,stars,star_velocity,language\n"

    df = pd.DataFrame([
        {
            "name": repo.name,
            "url": str(repo.url),
            "stars": repo.stars,
            "star_velocity": repo.star_velocity,
            "commits": repo.commits,
            "contributors": repo.contributors,
            "issues": repo.issues,
            "language": repo.language or "",
            "topics": ",".join(repo.topics),
        }
        for repo in report.top_repos
    ])
    return df.to_csv(index=False)


__all__ = ["synthesis_agent", "generate_scout_report_md", "generate_top_repos_csv", "build_synthesis_report_from_state"]
