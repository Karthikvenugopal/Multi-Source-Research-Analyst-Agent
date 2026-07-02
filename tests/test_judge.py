"""Unit tests for the LLM-as-judge data model and evidence formatting.

The judge model itself is mocked; we never call Gemini here.
"""
from unittest.mock import Mock

import pytest

from evals.judge import JudgeVerdict


def test_overall_is_mean_of_three_metrics():
    v = JudgeVerdict(
        faithfulness=0.9, answer_relevance=0.6, citation_coverage=0.3, rationale="r"
    )
    assert v.overall == pytest.approx(0.6)


def test_scores_must_be_within_unit_interval():
    with pytest.raises(Exception):
        JudgeVerdict(
            faithfulness=1.5, answer_relevance=0.5, citation_coverage=0.5, rationale="r"
        )


def _make_judge(monkeypatch):
    import langchain_google_genai
    from config import Config

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", lambda **k: Mock())
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "dummy")
    from evals.judge import ReportJudge

    return ReportJudge()


def test_format_evidence_truncates_and_labels(monkeypatch):
    judge = _make_judge(monkeypatch)
    text = judge._format_evidence([
        {"source": "web", "title": "Title A", "content": "C" * 5000},
    ])
    assert "WEB" in text
    assert "Title A" in text
    assert text.count("C") <= judge.evidence_char_limit


def test_format_evidence_handles_empty(monkeypatch):
    judge = _make_judge(monkeypatch)
    assert "no evidence" in judge._format_evidence([]).lower()


def test_evaluate_returns_zero_verdict_on_judge_error(monkeypatch):
    judge = _make_judge(monkeypatch)
    judge._judge = Mock()
    judge._judge.invoke = Mock(side_effect=RuntimeError("429 quota"))
    verdict = judge.evaluate("q", "report", [{"source": "web", "content": "x"}])
    assert verdict.overall == 0.0
    assert "429" in verdict.rationale
