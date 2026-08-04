"""Comparison output tests using only hermetic fixture runners."""

import json

from evals.compare_modes import (
    compare,
    offline_agentic_runner,
    offline_legacy_runner,
)


def test_compare_modes_writes_json_and_markdown(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(json.dumps({
        "id": "fixture-1",
        "category": "factual",
        "question": "What is photosynthesis?",
        "expected_bundles": ["wikipedia"],
        "expected_behavior": "answer",
        "required_topics": ["photosynthesis"],
    }) + "\n")
    report = compare(
        dataset,
        tmp_path / "out",
        runners={"legacy": offline_legacy_runner, "agentic": offline_agentic_runner},
        evaluation_label="test fixtures",
    )
    assert report["aggregate"]["legacy"]["num_questions"] == 1
    assert report["aggregate"]["agentic"]["num_questions"] == 1
    assert (tmp_path / "out" / "comparison.json").exists()
    markdown = (tmp_path / "out" / "comparison.md").read_text()
    assert "Legacy versus agentic" in markdown
    assert "fixture-1" in markdown


def test_offline_agentic_comparison_uses_real_verifier():
    result = offline_agentic_runner({
        "id": "f",
        "category": "technical",
        "question": "How does self-attention work?",
        "expected_bundles": ["academic"],
        "expected_behavior": "answer",
        "required_topics": ["self-attention"],
    })
    assert result["mode"] == "agentic"
    assert result["verification_result"]["is_valid"] is True
    assert result["tool_calls"] == 1
