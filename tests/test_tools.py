"""Unit tests for ResearchTools — every external API client is mocked."""
from unittest.mock import Mock

import pytest

import tools as tools_mod


@pytest.fixture
def research_tools(monkeypatch):
    # Replace the external client classes so __init__ builds harmless mocks.
    monkeypatch.setattr(tools_mod, "TavilySearchResults", lambda **k: Mock())
    monkeypatch.setattr(tools_mod, "WikipediaAPIWrapper", lambda **k: Mock())
    monkeypatch.setattr(tools_mod, "ArxivAPIWrapper", lambda **k: Mock())
    return tools_mod.ResearchTools()


def test_web_search_formats_list_results(research_tools):
    research_tools.tavily_tool.invoke = Mock(return_value=[
        {"content": "RAG content", "url": "http://x", "title": "RAG"},
    ])
    out = research_tools.web_search("rag")
    assert len(out) == 1
    f = out[0]
    assert f["source"] == "web"
    assert f["confidence"] == 0.8
    assert f["title"] == "RAG"
    assert f["url"] == "http://x"
    assert "timestamp" in f


def test_web_search_handles_errors(research_tools):
    research_tools.tavily_tool.invoke = Mock(side_effect=RuntimeError("boom"))
    out = research_tools.web_search("rag")
    assert out[0]["source"] == "web"
    assert out[0]["confidence"] == 0.0
    assert "boom" in out[0]["content"]


def test_wikipedia_search_success(research_tools):
    research_tools.wikipedia_api.run = Mock(return_value="Some encyclopedia text")
    out = research_tools.wikipedia_search("rag")
    assert out[0]["source"] == "wikipedia"
    assert out[0]["confidence"] == 0.9
    assert out[0]["url"].startswith("https://en.wikipedia.org/wiki/")


def test_wikipedia_search_empty(research_tools):
    research_tools.wikipedia_api.run = Mock(return_value="")
    out = research_tools.wikipedia_search("rag")
    assert out[0]["confidence"] == 0.0


def test_arxiv_search_success(research_tools):
    research_tools.arxiv_api.run = Mock(return_value="Paper abstract")
    out = research_tools.arxiv_search("rag")
    assert out[0]["source"] == "arxiv"
    assert out[0]["confidence"] == 0.85


def test_quality_empty_is_zero(research_tools):
    assert research_tools.calculate_research_quality([]) == 0.0


def test_quality_rewards_source_diversity(research_tools):
    findings = [
        {"source": "web", "confidence": 0.8},
        {"source": "wikipedia", "confidence": 0.9},
        {"source": "arxiv", "confidence": 0.85},
    ]
    # avg 0.85 + diversity bonus 0.15 -> capped at 1.0
    assert research_tools.calculate_research_quality(findings) == pytest.approx(1.0)


def test_quality_penalises_low_confidence(research_tools):
    findings = [
        {"source": "web", "confidence": 0.2},
        {"source": "web", "confidence": 0.2},
    ]
    # avg 0.2 + diversity 0.05 - penalty 0.2 -> 0.05
    assert research_tools.calculate_research_quality(findings) == pytest.approx(0.05)
