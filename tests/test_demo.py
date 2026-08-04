"""No-network CLI helper smoke tests for both modes."""

from demo import format_trace, run_question


def test_offline_agentic_end_to_end():
    result = run_question("What is photosynthesis?", "agentic", offline_fixtures=True)
    assert result["mode"] == "agentic"
    assert result["verification_result"]["is_valid"] is True
    assert "E1" in result["report"]
    assert "iteration" in format_trace(result)


def test_offline_legacy_end_to_end():
    result = run_question("What is photosynthesis?", "legacy", offline_fixtures=True)
    assert result["mode"] == "legacy"
    assert "numeric citation format" in result["report"]
    assert "no iterative" in format_trace(result)
