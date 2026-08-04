"""Gradio-facing formatting and lazy graph adapter tests."""

from app import ResearchApp


class FakeGraph:
    def __init__(self, result):
        self.result = result

    def stream(self, question):
        yield "agentic_research", {**self.result, "question": question}


def agentic_result():
    return {
        "mode": "agentic",
        "report": "## Answer\n\nSupported answer [E1].",
        "iterations": 2,
        "tool_calls": 1,
        "stop_reason": "evidence_sufficient",
        "verification_result": {"is_valid": True},
        "evidence_ledger": [{
            "evidence_id": "E1",
            "source_type": "web",
            "title": "Source",
            "url": "https://example.test",
        }],
        "conflicts": [],
        "trace": [{
            "iteration": 1,
            "tool_selected": "web",
            "search_query": "concise query",
            "action_summary": "Need current evidence.",
            "tool_result_count": 1,
            "new_evidence_ids": ["E1"],
            "duplicate_results_skipped": 0,
            "unresolved_gaps": [],
            "conflicts_detected": [],
            "errors": [],
            "stop_decision": None,
        }],
        "evidence_coverage": {
            "retrieved": ["E1"], "selected_for_context": ["E1"], "cited": ["E1"]
        },
    }


def test_gradio_query_defaults_to_agentic_and_returns_trace():
    calls = []

    def factory(mode):
        calls.append(mode)
        return FakeGraph(agentic_result())

    outputs = list(ResearchApp(factory).research_query("What changed?"))
    report, trace = outputs[-1]
    assert calls == ["agentic"]
    assert "Citation verification:** ✅ Passed" in report
    assert "Stop reason:** `evidence_sufficient`" in report
    assert "Collected sources" in report
    assert "Iteration 1" in trace
    assert "concise query" in trace


def test_gradio_formatting_warns_on_incomplete_or_unverified_result():
    result = agentic_result()
    result["stop_reason"] = "iteration_limit"
    result["verification_result"] = {"is_valid": False}
    report = ResearchApp.format_result("q", result)
    assert "Research stopped with `iteration_limit`" in report
    assert "verification did not pass" in report


def test_gradio_invalid_question_does_not_construct_graph():
    app = ResearchApp(lambda **kwargs: (_ for _ in ()).throw(AssertionError("not called")))
    output = list(app.research_query("   "))[-1]
    assert "Please enter" in output[0]


def test_legacy_result_format_is_available():
    report = ResearchApp.format_result("q", {
        "mode": "legacy",
        "report": "legacy report",
        "research_findings": [],
    })
    assert "legacy" in report
    assert "Not available in legacy mode" in report
