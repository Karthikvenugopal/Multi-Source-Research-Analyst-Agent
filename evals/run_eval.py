"""Run the research agent over an evaluation set and grade every report.

Usage:
    python -m evals.run_eval                      # full dataset
    python -m evals.run_eval --limit 3            # first 3 questions
    python -m evals.run_eval --dataset path.jsonl --out evals

Outputs:
    <out>/results.json   full per-question detail + aggregate scores
    <out>/results.md     a Markdown summary table (drop straight into the README)
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from evals.judge import ReportJudge
from graph import ResearchGraph

DEFAULT_DATASET = Path("datasets/eval_questions.jsonl")
DEFAULT_OUT = Path("evals")


def load_questions(path: Path, limit: int | None = None) -> List[Dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows[:limit] if limit else rows


def _mean(values: List[float]) -> float:
    return round(statistics.mean(values), 4) if values else 0.0


def run(dataset: Path, out_dir: Path, limit: int | None,
        judge_model: str | None = None) -> Dict[str, Any]:
    from config import Config

    questions = load_questions(dataset, limit)
    agent = ResearchGraph()
    judge = ReportJudge(model=judge_model)
    agent_model = Config.LLM_MODEL

    per_question: List[Dict[str, Any]] = []
    for i, row in enumerate(questions, 1):
        q = row["question"]
        print(f"\n[{i}/{len(questions)}] {row.get('id', '?')}: {q}")

        t0 = time.time()
        result = agent.run(q)
        duration = round(time.time() - t0, 1)

        findings = result.get("research_findings", [])
        report = result.get("report", "")
        verdict = judge.evaluate(q, report, findings)

        print(
            f"    faithfulness={verdict.faithfulness:.2f} "
            f"relevance={verdict.answer_relevance:.2f} "
            f"citations={verdict.citation_coverage:.2f} "
            f"overall={verdict.overall:.2f}  ({duration}s)"
        )

        per_question.append({
            "id": row.get("id"),
            "category": row.get("category"),
            "question": q,
            "duration_s": duration,
            "num_findings": len(findings),
            "sources_used": sorted({f.get("source", "?") for f in findings}),
            "report_chars": len(report),
            "scores": {
                "faithfulness": verdict.faithfulness,
                "answer_relevance": verdict.answer_relevance,
                "citation_coverage": verdict.citation_coverage,
                "overall": verdict.overall,
            },
            "rationale": verdict.rationale,
        })

    aggregate = {
        "num_questions": len(per_question),
        "faithfulness": _mean([r["scores"]["faithfulness"] for r in per_question]),
        "answer_relevance": _mean([r["scores"]["answer_relevance"] for r in per_question]),
        "citation_coverage": _mean([r["scores"]["citation_coverage"] for r in per_question]),
        "overall": _mean([r["scores"]["overall"] for r in per_question]),
        "avg_duration_s": _mean([r["duration_s"] for r in per_question]),
        "avg_sources": _mean([len(r["sources_used"]) for r in per_question]),
        "avg_findings": _mean([r["num_findings"] for r in per_question]),
    }

    report_obj = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent_model": agent_model,
        "judge_model": judge.model,
        "dataset": str(dataset),
        "aggregate": aggregate,
        "results": per_question,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(report_obj, indent=2))
    (out_dir / "results.md").write_text(_render_markdown(report_obj))

    print("\n=== AGGREGATE ===")
    for k, v in aggregate.items():
        print(f"  {k}: {v}")
    print(f"\nWrote {out_dir/'results.json'} and {out_dir/'results.md'}")
    return report_obj


def _render_markdown(report_obj: Dict[str, Any]) -> str:
    agg = report_obj["aggregate"]
    lines = [
        "## Evaluation results",
        "",
        f"_Agent: `{report_obj.get('agent_model', '?')}` · "
        f"Judge: `{report_obj['judge_model']}` (temperature 0) · "
        f"{agg['num_questions']} questions · generated {report_obj['generated_at']}_",
        "",
        "| Metric | Score |",
        "| --- | --- |",
        f"| Faithfulness (grounded-in-evidence) | **{agg['faithfulness']:.2f}** |",
        f"| Answer relevance | **{agg['answer_relevance']:.2f}** |",
        f"| Citation coverage | **{agg['citation_coverage']:.2f}** |",
        f"| Overall | **{agg['overall']:.2f}** |",
        f"| Avg. latency | {agg['avg_duration_s']:.0f}s |",
        f"| Avg. sources / question | {agg['avg_sources']:.1f} |",
        "",
        "### Per-question",
        "",
        "| ID | Category | Faithful | Relevance | Citations | Overall | Latency |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report_obj["results"]:
        s = r["scores"]
        lines.append(
            f"| {r['id']} | {r['category']} | {s['faithfulness']:.2f} | "
            f"{s['answer_relevance']:.2f} | {s['citation_coverage']:.2f} | "
            f"{s['overall']:.2f} | {r['duration_s']:.0f}s |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the research agent.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run the first N questions.")
    parser.add_argument("--judge-model", default=None,
                        help="Model for the judge (defaults to LLM_MODEL). Use a "
                             "different model than the agent to split free-tier "
                             "quota and reduce self-grading bias.")
    args = parser.parse_args()
    run(args.dataset, args.out, args.limit, judge_model=args.judge_model)


if __name__ == "__main__":
    main()
