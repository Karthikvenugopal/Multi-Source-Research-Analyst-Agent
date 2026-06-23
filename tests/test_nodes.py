"""Unit tests for AgentNodes — the LLM and tools are mocked."""
from unittest.mock import Mock

import pytest

import nodes as nodes_mod


@pytest.fixture
def agent_nodes(monkeypatch):
    monkeypatch.setattr(nodes_mod, "LLMManager", lambda: Mock())
    monkeypatch.setattr(nodes_mod, "ResearchTools", lambda: Mock())
    return nodes_mod.AgentNodes()


# --- planner ---------------------------------------------------------------

def test_planner_returns_structured_plan(agent_nodes):
    from nodes import ResearchPlan, PlannedSearch

    agent_nodes.planner.invoke = Mock(return_value=ResearchPlan(searches=[
        PlannedSearch(source="web", query="rag"),
        PlannedSearch(source="arxiv", query="retrieval augmented generation"),
    ]))
    out = agent_nodes.planner_node({"question": "What is RAG?"})
    plan = out["research_plan"]
    assert {p["source"] for p in plan} == {"web", "arxiv"}
    assert plan[0]["query"] == "rag"


def test_planner_falls_back_to_all_sources_on_error(agent_nodes):
    agent_nodes.planner.invoke = Mock(side_effect=RuntimeError("api down"))
    out = agent_nodes.planner_node({"question": "What is RAG?"})
    assert {p["source"] for p in out["research_plan"]} == {"web", "wikipedia", "arxiv"}
    assert all(p["query"] == "What is RAG?" for p in out["research_plan"])


# --- gather (parallel retrieval) -------------------------------------------

def test_gather_runs_every_planned_search(agent_nodes):
    agent_nodes.tools.web_search = Mock(return_value=[{"source": "web", "confidence": 0.8, "content": "w"}])
    agent_nodes.tools.wikipedia_search = Mock(return_value=[{"source": "wikipedia", "confidence": 0.9, "content": "x"}])
    agent_nodes.tools.arxiv_search = Mock(return_value=[{"source": "arxiv", "confidence": 0.85, "content": "y"}])
    agent_nodes.tools.calculate_research_quality = Mock(return_value=0.9)

    out = agent_nodes.gather_node({
        "question": "q",
        "research_plan": [
            {"source": "web", "query": "qa"},
            {"source": "wikipedia", "query": "qb"},
            {"source": "arxiv", "query": "qc"},
        ],
    })
    assert len(out["research_findings"]) == 3
    assert out["sources_used"] == ["arxiv", "web", "wikipedia"]  # sorted
    agent_nodes.tools.web_search.assert_called_once_with("qa")
    agent_nodes.tools.arxiv_search.assert_called_once_with("qc")


def test_gather_passes_per_source_query(agent_nodes):
    captured = {}

    def fake_web(query):
        captured["q"] = query
        return [{"source": "web", "confidence": 0.8, "content": "c"}]

    agent_nodes.tools.web_search = fake_web
    agent_nodes.tools.calculate_research_quality = Mock(return_value=0.5)
    agent_nodes.gather_node({
        "question": "a long natural-language question",
        "research_plan": [{"source": "web", "query": "short keywords"}],
    })
    assert captured["q"] == "short keywords"


def test_gather_defaults_to_all_sources_when_no_plan(agent_nodes):
    calls = []
    agent_nodes.tools.web_search = lambda q: calls.append(("web", q)) or [{"source": "web", "confidence": 0.8, "content": "c"}]
    agent_nodes.tools.wikipedia_search = lambda q: calls.append(("wikipedia", q)) or []
    agent_nodes.tools.arxiv_search = lambda q: calls.append(("arxiv", q)) or []
    agent_nodes.tools.calculate_research_quality = Mock(return_value=0.5)

    agent_nodes.gather_node({"question": "the question"})  # no research_plan
    assert {c[0] for c in calls} == {"web", "wikipedia", "arxiv"}
    assert all(q == "the question" for _, q in calls)


# --- helpers ---------------------------------------------------------------

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
