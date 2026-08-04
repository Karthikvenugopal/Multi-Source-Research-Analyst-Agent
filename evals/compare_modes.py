"""Compare legacy and agentic modes on the same evaluation cases.

Live usage (requires configured model and source credentials):
    python -m evals.compare_modes --limit 3

Hermetic architecture smoke benchmark (explicitly fixture-backed):
    python -m evals.compare_modes --offline-fixtures
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agent.models import ResearchDecision, ResearchRequirements
from agent.policies import RuntimeLimits
from agent.runtime import ResearchAgentRuntime
from evals.evaluators import aggregate_results, evaluate_result
from evals.run_eval import load_questions
from tool_bundles.base import BundleTool, EvaluationCase, ToolBundle
from tool_bundles.registry import ToolBundleRegistry

DEFAULT_DATASET = Path("datasets/eval_questions.jsonl")
DEFAULT_OUT = Path("evals/comparison")
CaseRunner = Callable[[dict[str, Any]], dict[str, Any]]


def compare(
    dataset: Path,
    out_dir: Path,
    limit: int | None = None,
    runners: dict[str, CaseRunner] | None = None,
    live_judge: Any | None = None,
    evaluation_label: str = "deterministic proxies; live retrieval",
) -> dict[str, Any]:
    """Run both modes, save machine-readable JSON and a concise Markdown report."""
    cases = load_questions(dataset, limit)
    if runners is None:
        from graph import ResearchGraph

        graphs = {mode: ResearchGraph(mode=mode) for mode in ("legacy", "agentic")}
        runners = {
            mode: (lambda case, graph=graph: graph.run(case["question"]))
            for mode, graph in graphs.items()
        }

    per_question: list[dict[str, Any]] = []
    mode_metrics: dict[str, list[dict[str, Any]]] = {"legacy": [], "agentic": []}
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case['id']}: {case['question']}")
        row = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
        }
        for mode in ("legacy", "agentic"):
            started = time.monotonic()
            result = runners[mode](case)
            result.setdefault("duration", round(time.monotonic() - started, 4))
            metrics = evaluate_result(case, result)
            if live_judge is not None:
                verdict = live_judge.evaluate(
                    case["question"],
                    result.get("report", ""),
                    result.get("research_findings", []),
                )
                metrics["faithfulness"] = verdict.faithfulness
                metrics["faithfulness_method"] = "live_model_judge"
                metrics["answer_relevance"] = verdict.answer_relevance
                metrics["answer_relevance_method"] = "live_model_judge"
                metrics["live_judge_citation_coverage"] = verdict.citation_coverage
            row[mode] = metrics
            mode_metrics[mode].append(metrics)
        per_question.append(row)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": str(dataset),
        "evaluation_label": evaluation_label,
        "aggregate": {
            mode: aggregate_results(metrics) for mode, metrics in mode_metrics.items()
        },
        "results": per_question,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    (out_dir / "comparison.md").write_text(render_markdown(report))
    print(f"Wrote {out_dir / 'comparison.json'} and {out_dir / 'comparison.md'}")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """Render aggregate and per-question comparison tables."""
    lines = [
        "# Legacy versus agentic comparison",
        "",
        f"_Generated {report['generated_at']} · {report['evaluation_label']} · "
        f"{len(report['results'])} questions._",
        "",
        "Faithfulness and relevance are deterministic lexical proxies unless the "
        "label explicitly says a live model judge was used.",
        "",
        "| Metric | Legacy | Agentic |",
        "| --- | ---: | ---: |",
    ]
    legacy = report["aggregate"]["legacy"]
    agentic = report["aggregate"]["agentic"]
    for key in (
        "faithfulness", "answer_relevance", "citation_validity", "citation_coverage",
        "tool_selection_recall", "tool_calls", "iterations", "latency_s",
    ):
        lines.append(f"| {key.replace('_', ' ').title()} | {legacy[key]:.3f} | {agentic[key]:.3f} |")
    lines.extend((
        "",
        "## Per question",
        "",
        "| ID | Category | Mode | Faithfulness | Relevance | Citations valid | Tool recall | Calls | Iterations | Stop reason |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ))
    for row in report["results"]:
        for mode in ("legacy", "agentic"):
            metrics = row[mode]
            lines.append(
                f"| {row['id']} | {row['category']} | {mode} | "
                f"{metrics['faithfulness']:.2f} | {metrics['answer_relevance']:.2f} | "
                f"{metrics['citation_validity']:.2f} | {metrics['tool_selection_recall']:.2f} | "
                f"{metrics['tool_calls']} | {metrics['iterations']} | "
                f"{metrics['completion_reason']} |"
            )
    return "\n".join(lines) + "\n"


class _OfflineModel:
    def __init__(self, case: dict[str, Any]) -> None:
        topics = case.get("required_topics") or [case["question"]]
        self.decisions = [
            ResearchDecision(
                action="search",
                bundle=bundle,
                query=(
                    " ".join(topics)
                    if index == 0
                    else f"{' '.join(topics)} corroborating evidence"
                )[:120],
                action_summary=(
                    f"Fixture selects expected {bundle} capability."
                    if index == 0
                    else f"The first fixture source left a cross-source gap; refine with {bundle}."
                ),
                unresolved_gaps=["Inspect fixture evidence."],
            )
            for index, bundle in enumerate(case.get("expected_bundles", []))
        ]
        self.decisions.append(ResearchDecision(
            action="finish",
            action_summary="Fixture evidence inspected.",
            unresolved_gaps=[] if case.get("expected_behavior") != "abstain" else [
                "The fixture intentionally contains no verifiable evidence."
            ],
        ))

    def analyze(self, question: str) -> ResearchRequirements:
        return ResearchRequirements(requirements=[f"Research {question}"], subquestions=[])

    def decide(self, payload: dict[str, Any]) -> ResearchDecision:
        return self.decisions.pop(0)

    def write_report(self, payload: dict[str, Any]) -> str:
        ids = list(dict.fromkeys(re.findall(r"\[(E\d+)\]", payload["evidence_context"])))
        citations = "".join(f"[{evidence_id}]" for evidence_id in ids)
        conflict = " The fixture contains a possible conflict that remains disclosed." if payload["conflicts"] else ""
        return (
            "## Fixture Answer\n\nThe fixture evidence addresses "
            f"{payload['question']} with traceable source content {citations}.{conflict}\n\n"
            "## Limitations\n\n- This is a hermetic architecture benchmark, not a live quality score."
        )

    def repair_report(self, payload: dict[str, Any]) -> str:
        return payload["draft_report"].split("## References", 1)[0]


def _offline_bundle(name: str, case: dict[str, Any]) -> ToolBundle:
    def retrieve(query: str):
        if case.get("expected_behavior") in {"abstain"}:
            return []
        topics = ", ".join(case.get("required_topics") or [case["question"]])
        if case.get("expected_behavior") == "disclose_conflict":
            return [
                {"title": f"{name} fixture A", "url": f"fixture://{name}/a", "content": f"The {topics} reported value was 50 units in 2024."},
                {"title": f"{name} fixture B", "url": f"fixture://{name}/b", "content": f"The {topics} reported value was 75 units in 2025."},
            ]
        return [{
            "title": f"{name} fixture",
            "url": f"fixture://{name}",
            "content": f"Fixture evidence about {topics} answers the requested topic with source detail.",
        }]

    return ToolBundle(
        name=name,
        source_type=name,
        description=f"Offline {name} fixture.",
        when_to_use=f"Fixture cases expecting {name}.",
        when_not_to_use="Other fixture cases.",
        tools=(BundleTool(f"{name}_fixture", "Return deterministic evidence.", retrieve),),
        evaluation_cases=(EvaluationCase("fixture", True),),
        timeout_seconds=1,
    )


def offline_agentic_runner(case: dict[str, Any]) -> dict[str, Any]:
    """Run the real agentic loop against deterministic local fixture bundles."""
    names = tuple(dict.fromkeys(case.get("expected_bundles") or ["web"]))
    runtime = ResearchAgentRuntime(
        model=_OfflineModel(case),
        registry=ToolBundleRegistry(_offline_bundle(name, case) for name in names),
        limits=RuntimeLimits(
            max_iterations=max(2, len(names) + 1),
            max_tool_calls=max(2, len(names) + 1),
            tool_timeout_seconds=1,
            max_elapsed_seconds=10,
            max_context_chars=4000,
            max_evidence_chars=1000,
            max_consecutive_no_new=max(1, len(names)),
        ),
    )
    return runtime.run(case["question"])


def offline_legacy_runner(case: dict[str, Any]) -> dict[str, Any]:
    """Represent the preserved single-pass contract with deterministic fixtures."""
    topics = ", ".join(case.get("required_topics") or [case["question"]])
    sources = case.get("expected_bundles") or ["web"]
    findings = [
        {
            "source": source,
            "title": f"{source} fixture",
            "url": f"fixture://{source}",
            "content": f"Legacy one-pass fixture evidence about {topics}.",
        }
        for source in sources
    ]
    return {
        "mode": "legacy",
        "question": case["question"],
        "research_findings": findings,
        "sources_used": sources,
        "report": (
            f"## Fixture baseline\n\nThe legacy one-pass report covers {topics} using "
            "its historical numeric citation format [1].\n\n## References\n\n**[1]** Fixture"
        ),
        "iterations": 1,
        "tool_calls": len(sources),
        "tool_call_history": [{"bundle": source} for source in sources],
        "queries_attempted": [{"bundle": source, "query": case["question"]} for source in sources],
        "duration": 0.0,
        "stop_reason": "legacy_completed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare legacy and agentic research modes.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offline-fixtures", action="store_true")
    parser.add_argument("--live-judge", action="store_true")
    parser.add_argument("--judge-model", default=None)
    args = parser.parse_args()

    runners = None
    judge = None
    label = "deterministic proxies; live retrieval"
    if args.offline_fixtures:
        runners = {"legacy": offline_legacy_runner, "agentic": offline_agentic_runner}
        label = "hermetic fixture architecture benchmark; no live retrieval or model grading"
    if args.live_judge:
        from evals.judge import ReportJudge

        judge = ReportJudge(model=args.judge_model)
        label += "; live model judge for faithfulness and relevance"
    compare(args.dataset, args.out, args.limit, runners, judge, label)


if __name__ == "__main__":
    main()
