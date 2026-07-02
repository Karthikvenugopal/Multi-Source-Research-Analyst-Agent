"""Unit tests for the heuristic evaluation helpers (pure functions, no I/O)."""
from evaluation import (
    ResearchEvaluator,
    check_research_quality,
    validate_research_output,
)


def _good_result():
    return {
        "question": "What is RAG?",
        "research_findings": [
            {"source": "web", "confidence": 0.8, "content": "Study shows data results in 2020."},
            {"source": "arxiv", "confidence": 0.9, "content": "Analysis of research data."},
        ],
        "analysis": "some analysis",
        "report": "some report",
        "sources_used": ["web", "arxiv"],
        "research_quality_score": 0.8,
        "duration": 10,
    }


def test_validate_passes_on_good_result():
    assert validate_research_output(_good_result()) is True


def test_validate_fails_without_report():
    r = _good_result()
    r["report"] = ""
    assert validate_research_output(r) is False


def test_validate_requires_a_high_confidence_finding():
    r = _good_result()
    for f in r["research_findings"]:
        f["confidence"] = 0.5
    assert validate_research_output(r) is False


def test_check_quality_flags_empty_result():
    ok, issues = check_research_quality(
        {"research_findings": [], "analysis": "", "report": "", "sources_used": []}
    )
    assert ok is False
    assert any("finding" in i.lower() for i in issues)


def test_check_quality_passes_on_good_result():
    ok, issues = check_research_quality(_good_result())
    assert ok is True
    assert issues == []


def test_overall_score_within_bounds():
    out = ResearchEvaluator().evaluate_research_session(_good_result(), "What is RAG?")
    assert 0.0 <= out["overall_score"] <= 1.0
    assert out["basic_metrics"]["has_report"] is True
    assert out["source_metrics"]["source_diversity"] == 2
