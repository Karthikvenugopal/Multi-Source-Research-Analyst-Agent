"""Unit tests for AgentNodes — the LLM and tools are mocked."""
from unittest.mock import Mock

import pytest

import nodes as nodes_mod
from config import Config


@pytest.fixture
def agent_nodes(monkeypatch):
    monkeypatch.setattr(nodes_mod, "LLMManager", lambda: Mock())
    monkeypatch.setattr(nodes_mod, "ResearchTools", lambda: Mock())
    return nodes_mod.AgentNodes()


def test_format_findings_summary_empty(agent_nodes):
    assert agent_nodes._format_findings_summary([]) == "No findings yet"


def test_format_findings_summary_includes_source_and_confidence(agent_nodes):
    out = agent_nodes._format_findings_summary([
        {"source": "web", "title": "T", "content": "body text", "confidence": 0.8},
    ])
    assert "WEB" in out
    assert "0.80" in out


def test_synthesis_confidence_in_range(agent_nodes):
    c = agent_nodes._calculate_synthesis_confidence([
        {"source": "web", "confidence": 0.8},
        {"source": "arxiv", "confidence": 0.9},
    ])
    assert 0.0 < c <= 1.0


def test_synthesis_confidence_zero_without_findings(agent_nodes):
    assert agent_nodes._calculate_synthesis_confidence([]) == 0.0


def test_sources_for_citation_includes_url(agent_nodes):
    out = agent_nodes._format_sources_for_citation([
        {"source": "web", "title": "T", "url": "http://x"},
    ])
    assert "http://x" in out
    assert "WEB" in out


def test_supervisor_forces_synthesis_at_max_iterations(agent_nodes):
    state = {
        "iterations": Config.MAX_ITERATIONS,
        "research_findings": [],
        "question": "q",
    }
    out = agent_nodes.supervisor_node(state)
    assert out["next_node"] == "synthesize"
    assert out["max_iterations_reached"] is True


def test_supervisor_parses_llm_decision(agent_nodes):
    agent_nodes.tools.calculate_research_quality = Mock(return_value=0.5)
    response = Mock()
    response.content = "arxiv_search"
    agent_nodes.llm.invoke = Mock(return_value=response)

    state = {
        "iterations": 1,
        "research_findings": [{"source": "web", "confidence": 0.8}],
        "question": "q",
        "current_focus": "x",
    }
    out = agent_nodes.supervisor_node(state)
    assert out["next_node"] == "arxiv_search"


def test_supervisor_falls_back_on_llm_error(agent_nodes):
    agent_nodes.tools.calculate_research_quality = Mock(return_value=0.5)
    agent_nodes.llm.invoke = Mock(side_effect=RuntimeError("api down"))

    state = {
        "iterations": 1,
        "research_findings": [],
        "question": "q",
        "current_focus": "x",
    }
    out = agent_nodes.supervisor_node(state)
    # On error the supervisor defaults to web_search rather than crashing.
    assert out["next_node"] == "web_search"
