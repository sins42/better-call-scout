"""Tests for Analysis Layer agent structure and mock data fixtures."""
import json
import pytest
from src.models.schemas import AnalystHypothesis, RepoData
from src.agents.analysis import analysis_layer
from src.agents.analysis.vc_analyst import vc_analyst_loop, vc_generator, vc_critic
from src.agents.analysis.developer_analyst import dev_analyst_loop, dev_generator, dev_critic
from src.agents.analysis.journalist_analyst import journalist_loop, journalist_generator, journalist_critic


def test_analysis_layer_has_three_sub_agents():
    """ParallelAgent must contain exactly 3 sub-agents (ANAL-04)."""
    assert len(analysis_layer.sub_agents) == 3


def test_vc_loop_max_iterations():
    """VCAnalystLoop must have max_iterations=2 (D-05)."""
    assert vc_analyst_loop.max_iterations == 2


def test_dev_loop_max_iterations():
    assert dev_analyst_loop.max_iterations == 2


def test_journalist_loop_max_iterations():
    assert journalist_loop.max_iterations == 2


def test_generator_output_keys_are_unique():
    """Each generator must write to a distinct state key to avoid collision (Pitfall 2)."""
    keys = {
        vc_generator.output_key,
        dev_generator.output_key,
        journalist_generator.output_key,
    }
    assert len(keys) == 3, "Generator output_key values must be unique across all analysts"


def test_critic_output_keys_are_unique():
    keys = {
        vc_critic.output_key,
        dev_critic.output_key,
        journalist_critic.output_key,
    }
    assert len(keys) == 3, "Critic output_key values must be unique across all analysts"


def test_generators_have_output_schema():
    """All generator LlmAgents must have output_schema=AnalystHypothesis (ANAL-06)."""
    for generator in [vc_generator, dev_generator, journalist_generator]:
        assert generator.output_schema is AnalystHypothesis, (
            f"{generator.name} must have output_schema=AnalystHypothesis"
        )


def test_generators_have_no_tools():
    """Generator agents must not have tools — output_schema + tools is incompatible in ADK."""
    for generator in [vc_generator, dev_generator, journalist_generator]:
        tools = getattr(generator, "tools", None) or []
        assert len(tools) == 0, f"{generator.name} must not have tools"


def test_mock_session_state_has_all_keys(mock_session_state):
    """Session state fixture must contain all 9 expected state keys."""
    required_keys = {
        "repo_data_json", "news_items_json", "rag_chunks_json",
        "vc_draft_output", "vc_critic_output",
        "dev_draft_output", "dev_critic_output",
        "journalist_draft_output", "journalist_critic_output",
    }
    assert required_keys.issubset(set(mock_session_state.keys()))


def test_mock_repos_are_valid(mock_repos):
    """RepoData fixtures must all pass Pydantic validation."""
    assert len(mock_repos) == 3
    for repo in mock_repos:
        assert isinstance(repo, RepoData)
        assert -1.0 <= repo.star_velocity <= 1.0


def test_mock_session_state_repo_json_is_parseable(mock_session_state):
    """Serialized repo_data_json must be valid JSON and re-parse to dicts."""
    parsed = json.loads(mock_session_state["repo_data_json"])
    assert isinstance(parsed, list)
    assert len(parsed) == 3
    assert all("name" in r for r in parsed)


def test_analyst_hypothesis_persona_values(mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis):
    """Each mock hypothesis must have the correct persona string."""
    assert mock_vc_hypothesis.persona == "vc_analyst"
    assert mock_dev_hypothesis.persona == "developer_analyst"
    assert mock_journalist_hypothesis.persona == "journalist"


def test_vc_prompt_covers_required_domains():
    """VC generator prompt must instruct analysis of funding, star velocity, market signals (SC-1)."""
    from src.agents.analysis._prompts import VC_GENERATOR_PROMPT
    assert "funding" in VC_GENERATOR_PROMPT.lower()
    assert "star_velocity" in VC_GENERATOR_PROMPT or "star velocity" in VC_GENERATOR_PROMPT.lower()
    assert "market" in VC_GENERATOR_PROMPT.lower()


def test_dev_prompt_covers_required_domains():
    """Dev generator prompt must instruct analysis of ecosystem maturity, adoption, job signals (SC-2)."""
    from src.agents.analysis._prompts import DEV_GENERATOR_PROMPT
    assert "ecosystem" in DEV_GENERATOR_PROMPT.lower()
    assert "contributor" in DEV_GENERATOR_PROMPT.lower() or "community" in DEV_GENERATOR_PROMPT.lower()


def test_journalist_prompt_covers_required_domains():
    """Journalist generator prompt must instruct analysis of HN sentiment, narrative, incumbents (SC-3)."""
    from src.agents.analysis._prompts import JOURNALIST_GENERATOR_PROMPT
    assert "sentiment" in JOURNALIST_GENERATOR_PROMPT.lower() or "hn" in JOURNALIST_GENERATOR_PROMPT.lower()
    assert "narrative" in JOURNALIST_GENERATOR_PROMPT.lower() or "story" in JOURNALIST_GENERATOR_PROMPT.lower()


# ---- Synthesis Agent tests ----

from src.agents.synthesis_agent import (
    synthesis_agent,
    generate_scout_report_md,
    generate_top_repos_csv,
    build_synthesis_report_from_state,
)
from src.models.schemas import SynthesisReport


def test_synthesis_agent_has_output_schema():
    """synthesis_agent must have output_schema=SynthesisReport (SYNTH-01)."""
    assert synthesis_agent.output_schema is SynthesisReport


def test_synthesis_agent_output_key():
    assert synthesis_agent.output_key == "synthesis_report"


def test_synthesis_agent_has_no_tools():
    tools = getattr(synthesis_agent, "tools", None) or []
    assert len(tools) == 0


def test_generate_scout_report_md_structure(mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis, mock_repos):
    """scout_report.md output must contain all persona names and query (SYNTH-02)."""
    report = SynthesisReport(
        query="AI dev tools about to break out",
        hypotheses=[mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis],
        top_repos=mock_repos[:3],
    )
    md = generate_scout_report_md(report)
    assert "AI dev tools about to break out" in md
    assert "vc_analyst" in md.lower() or "Vc Analyst" in md
    assert "developer_analyst" in md.lower() or "Developer Analyst" in md
    assert "journalist" in md.lower() or "Journalist" in md
    assert "langchain-ai/langchain" in md
    assert "Overall Confidence" in md


def test_generate_scout_report_md_overall_confidence(mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis):
    """Overall confidence must be the mean of the 3 analyst scores (D-09)."""
    report = SynthesisReport(
        query="test",
        hypotheses=[mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis],
        top_repos=[],
    )
    md = generate_scout_report_md(report)
    expected = (mock_vc_hypothesis.confidence_score + mock_dev_hypothesis.confidence_score + mock_journalist_hypothesis.confidence_score) / 3
    expected_pct = f"{expected:.0%}"
    assert expected_pct in md, f"Expected {expected_pct} in markdown output"


def test_generate_top_repos_csv_columns(mock_repos):
    """top_repos.csv must have required columns (SYNTH-03)."""
    from src.models.schemas import AnalystHypothesis
    report = SynthesisReport(
        query="test",
        hypotheses=[
            AnalystHypothesis(
                persona="vc_analyst",
                confidence_score=0.7,
                evidence=[],
                counter_evidence=[],
                reasoning="test",
                hypothesis_text="test",
            )
        ],
        top_repos=mock_repos,
    )
    csv = generate_top_repos_csv(report)
    assert "name" in csv
    assert "stars" in csv
    assert "star_velocity" in csv
    assert "langchain-ai/langchain" in csv


def test_generate_top_repos_csv_empty_repos():
    """generate_top_repos_csv must handle empty top_repos without error."""
    from src.models.schemas import AnalystHypothesis
    report = SynthesisReport(
        query="test",
        hypotheses=[
            AnalystHypothesis(
                persona="vc_analyst",
                confidence_score=0.5,
                evidence=[],
                counter_evidence=[],
                reasoning="test",
                hypothesis_text="test",
            )
        ],
        top_repos=[],
    )
    csv = generate_top_repos_csv(report)
    assert "name" in csv  # header row still present


def test_build_synthesis_report_from_state(mock_vc_hypothesis, mock_dev_hypothesis, mock_journalist_hypothesis, mock_repos):
    """Fallback constructor must build a valid SynthesisReport from state dict."""
    import json
    state = {
        "vc_draft_output": mock_vc_hypothesis.model_dump(mode="json"),
        "dev_draft_output": mock_dev_hypothesis.model_dump(mode="json"),
        "journalist_draft_output": mock_journalist_hypothesis.model_dump(mode="json"),
    }
    report = build_synthesis_report_from_state(state, query="test query", repos=mock_repos)
    assert isinstance(report, SynthesisReport)
    assert len(report.hypotheses) == 3
    assert report.query == "test query"


# ---- Visualization tests ----

from src.visualization.charts import (
    star_velocity_chart,
    category_heatmap,
    hn_buzz_scatter,
    persona_score_bars,
)


def test_star_velocity_chart_returns_png(mock_synthesis_report):
    """star_velocity_chart must return non-empty bytes (VIZ-01, VIZ-05)."""
    png = star_velocity_chart(mock_synthesis_report)
    assert isinstance(png, bytes)
    assert len(png) > 0
    assert png[:4] == b'\x89PNG' or png[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes


def test_category_heatmap_returns_png(mock_synthesis_report):
    """category_heatmap must return non-empty PNG bytes (VIZ-02, VIZ-05)."""
    png = category_heatmap(mock_synthesis_report)
    assert isinstance(png, bytes)
    assert len(png) > 0


def test_hn_buzz_scatter_returns_png(mock_synthesis_report):
    """hn_buzz_scatter must return non-empty PNG bytes (VIZ-03, VIZ-05)."""
    png = hn_buzz_scatter(mock_synthesis_report)
    assert isinstance(png, bytes)
    assert len(png) > 0


def test_persona_score_bars_returns_png(mock_synthesis_report):
    """persona_score_bars must return non-empty PNG bytes (VIZ-04, VIZ-05)."""
    png = persona_score_bars(mock_synthesis_report)
    assert isinstance(png, bytes)
    assert len(png) > 0


def test_all_charts_return_valid_png_magic_bytes(mock_synthesis_report):
    """All 4 chart functions must return bytes starting with PNG magic bytes."""
    PNG_MAGIC = b'\x89PNG'  # 4 bytes: 0x89, P, N, G
    chart_fns = [star_velocity_chart, category_heatmap, hn_buzz_scatter, persona_score_bars]
    for fn in chart_fns:
        result = fn(mock_synthesis_report)
        # PNG files start with bytes: 137 80 78 71 (0x89PNG)
        assert result[1:4] == b"PNG", f"{fn.__name__} did not return a valid PNG"
