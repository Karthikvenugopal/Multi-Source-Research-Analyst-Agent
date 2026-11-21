#!/usr/bin/env python3
"""Command-line entry point for legacy and agentic research modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _offline_case(question: str) -> dict[str, Any]:
    from evals.capability_gates import heuristic_bundle_selector

    bundles = sorted(
        heuristic_bundle_selector(question, ("web", "wikipedia", "academic"))
    ) or ["web"]
    return {
        "id": "cli-fixture",
        "category": "offline_fixture",
        "question": question,
        "expected_bundles": bundles,
        "expected_behavior": "answer",
        "required_topics": [question.rstrip("?")],
    }


def run_question(
    question: str,
    mode: str = "agentic",
    offline_fixtures: bool = False,
) -> dict[str, Any]:
    """Run one question through the selected mode."""
    if offline_fixtures:
        from evals.compare_modes import offline_agentic_runner, offline_legacy_runner

        runner = offline_agentic_runner if mode == "agentic" else offline_legacy_runner
        return runner(_offline_case(question))
    from graph import ResearchGraph

    return ResearchGraph(mode=mode).run(question)


def format_trace(result: dict[str, Any]) -> str:
    """Render the operational trace without hidden model reasoning."""
    trace = result.get("trace", [])
    if not trace:
        return "(legacy mode has no iterative operational trace)"
    lines: list[str] = []
    for event in trace:
        line = f"iteration {event['iteration']}: "
        if event.get("tool_selected"):
            line += f"{event['tool_selected']} query={event.get('search_query')!r}; "
            line += f"results={event.get('tool_result_count', 0)}; "
            line += f"new={event.get('new_evidence_ids', [])}; "
            line += f"duplicates={event.get('duplicate_results_skipped', 0)}"
        else:
            line += event.get("action_summary", "inspection")
        if event.get("stop_decision"):
            line += f"; stop={event['stop_decision']}"
        if event.get("errors"):
            line += f"; errors={event['errors']}"
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the research analyst agent.")
    parser.add_argument("--mode", choices=("legacy", "agentic"), default="agentic")
    parser.add_argument(
        "--question",
        default="What is retrieval-augmented generation and why is it used?",
    )
    parser.add_argument(
        "--trace-json",
        type=Path,
        default=None,
        help="Optionally export the complete structured result and trace as JSON.",
    )
    parser.add_argument(
        "--offline-fixtures",
        action="store_true",
        help="Use deterministic local fixtures; no API keys or network required.",
    )
    args = parser.parse_args()

    result = run_question(args.question, args.mode, args.offline_fixtures)
    print(result.get("report") or "No report was generated.")
    print("\n--- Operational summary ---")
    print(f"mode: {args.mode}")
    print(f"iterations: {result.get('iterations', 'n/a')}")
    print(f"tool calls: {result.get('tool_calls', 'n/a')}")
    print(f"stop reason: {result.get('stop_reason', 'legacy_completed')}")
    verification = result.get("verification_result", {})
    print(
        "citation verification: "
        + ("passed" if verification.get("is_valid") else "not passed / not available")
    )
    print(format_trace(result))

    if args.trace_json:
        args.trace_json.parent.mkdir(parents=True, exist_ok=True)
        args.trace_json.write_text(json.dumps(result, indent=2, default=str) + "\n")
        print(f"trace JSON: {args.trace_json}")


if __name__ == "__main__":
    main()
