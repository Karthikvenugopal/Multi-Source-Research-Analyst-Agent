"""Deterministic evaluation and capability gate tests."""

import json
from pathlib import Path

import pytest

from evals.capability_gates import (
    evaluate_capability_gates,
    heuristic_bundle_selector,
    leave_one_out_selection,
)
from evals.evaluators import (
    aggregate_results,
    answer_relevance,
    evaluate_result,
    search_query_quality,
    tool_selection_metrics,
)
from tool_bundles.academic import build_academic_bundle
from tool_bundles.registry import ToolBundleRegistry
from tool_bundles.web import build_web_bundle
from tool_bundles.wikipedia import build_wikipedia_bundle


class FakeTools:
    def search(self, source, query):
        return []


def registry():
    tools = FakeTools()
    return ToolBundleRegistry((
        build_web_bundle(tools),
        build_wikipedia_bundle(tools),
        build_academic_bundle(tools),
    ))


def result_fixture():
    return {
        "report": (
            "## Answer\n\nPhotosynthesis converts light energy in plants according "
            "to the collected encyclopedia evidence [E1].\n\n## References\n\n"
            "**[E1]** Photosynthesis"
        ),
        "evidence_ledger": [{
            "evidence_id": "E1",
            "source_type": "wikipedia",
            "title": "Photosynthesis",
            "url": "https://example.test",
            "content": "Photosynthesis in plants converts light energy to chemical energy.",
            "query": "photosynthesis",
        }],
        "evidence_coverage": {"selected_for_context": ["E1"]},
        "tool_call_history": [{"bundle": "wikipedia"}],
        "queries_attempted": [{
            "bundle": "wikipedia",
            "query": "photosynthesis",
            "normalized_query": "photosynthesis",
        }],
        "tool_calls": 1,
        "iterations": 2,
        "elapsed_time": 0.2,
        "stop_reason": "evidence_sufficient",
    }


def test_evaluate_result_exposes_all_required_metric_groups():
    case = {
        "question": "What is photosynthesis?",
        "expected_bundles": ["wikipedia"],
        "required_topics": ["photosynthesis"],
        "expected_behavior": "answer",
    }
    metrics = evaluate_result(case, result_fixture())
    assert metrics["citation_validity"] == 1.0
    assert metrics["citation_coverage"] == 1.0
    assert metrics["tool_selection_precision"] == 1.0
    assert metrics["tool_selection_recall"] == 1.0
    assert metrics["retrieval_coverage"] == 1.0
    assert metrics["completion_reason"] == "evidence_sufficient"


def test_tool_selection_precision_and_recall_are_separate():
    precision, recall = tool_selection_metrics({"web", "academic"}, {"web", "wikipedia"})
    assert precision == 0.5
    assert recall == 0.5


def test_query_quality_penalizes_full_verbose_academic_question():
    question = "What are transformer neural networks and how does self attention work in language models today?"
    concise = search_query_quality(question, [{"bundle": "academic", "query": "transformer self attention"}])
    verbose = search_query_quality(question, [{"bundle": "academic", "query": question}])
    assert concise > verbose


def test_answer_relevance_proxy_is_bounded():
    assert 0.0 <= answer_relevance("What is solar energy?", "Solar energy uses sunlight.") <= 1.0
    assert answer_relevance("What is solar energy?", "Penguins live south.") == 0.0


def test_aggregate_keeps_completion_reason_counts():
    aggregate = aggregate_results([
        {"answer_relevance": 1.0, "completion_reason": "evidence_sufficient"},
        {"answer_relevance": 0.0, "completion_reason": "iteration_limit"},
    ])
    assert aggregate["answer_relevance"] == 0.5
    assert aggregate["completion_reasons"] == {
        "evidence_sufficient": 1,
        "iteration_limit": 1,
    }


def test_default_bundle_capability_gates_pass():
    results = evaluate_capability_gates(registry())
    assert all(result.passed for result in results)


def test_adding_academic_does_not_route_factual_questions_to_it():
    selected = heuristic_bundle_selector("What is photosynthesis?", registry().names)
    assert selected == {"wikipedia"}


def test_web_instruction_strength_does_not_suppress_wikipedia_fixture():
    selected = heuristic_bundle_selector("What is the Haber process?", registry().names)
    assert "wikipedia" in selected
    assert "web" not in selected


def test_leave_one_out_does_not_return_disabled_bundle():
    selected = leave_one_out_selection(
        registry(), "What does a transformer paper say about self-attention?", "academic"
    )
    assert "academic" not in selected


def test_evaluation_dataset_has_at_least_twenty_typed_cases():
    rows = [json.loads(line) for line in Path("datasets/eval_questions.jsonl").read_text().splitlines()]
    assert len(rows) >= 20
    categories = {row["category"] for row in rows}
    assert {"factual", "technical", "comparative", "multi_hop", "conflicting_evidence", "insufficient_evidence"} <= categories
    assert all("expected_bundles" in row and "expected_behavior" in row for row in rows)
