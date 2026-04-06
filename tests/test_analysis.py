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
