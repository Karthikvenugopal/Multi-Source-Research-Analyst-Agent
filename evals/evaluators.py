"""Deterministic evaluators for agent behavior and evidence safeguards."""

from __future__ import annotations

import re
import statistics
from typing import Any, Iterable

from evidence.citations import CitationVerifier, parse_citations
from evidence.ledger import EvidenceLedger

_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9-]{2,}\b")
_STOPWORDS = {
    "about", "and", "are", "does", "for", "from", "how", "into", "that", "the",
    "their", "this", "was", "what", "when", "which", "who", "why", "with",
}


def _tokens(text: str) -> set[str]:
    return {word for word in _TOKEN_RE.findall(text.lower()) if word not in _STOPWORDS}


def _safe_mean(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return round(statistics.mean(present), 4) if present else None


def _ledger_from_result(result: dict[str, Any]) -> EvidenceLedger:
    ledger = EvidenceLedger()
    for row in result.get("evidence_ledger", []):
        ledger.add_candidates(
            row.get("source_type", "unknown"),
            row.get("query", "unknown query"),
            [row],
        )
    if len(ledger):
        return ledger
    for finding in result.get("research_findings", []):
        ledger.add_candidates(
            finding.get("source_type") or finding.get("source", "unknown"),
            finding.get("query", "legacy retrieval"),
            [finding],
        )
    return ledger


def answer_relevance(question: str, report: str) -> float:
    """Return a transparent lexical relevance proxy for hermetic evaluation."""
    question_tokens = _tokens(question)
    if not question_tokens:
        return 1.0 if report.strip() else 0.0
    return round(len(question_tokens & _tokens(report)) / len(question_tokens), 4)


def faithfulness_to_evidence(report: str, ledger: EvidenceLedger) -> float:
    """Score cited sentences by lexical support in the specifically cited evidence.

    This is a deterministic support proxy, not semantic entailment. Live judge
    scores are kept separately and may replace it in an explicitly live run.
    """
    sentences = re.split(r"(?<=[.!?])\s+", report)
    assessed = 0
    supported = 0
    for sentence in sentences:
        ids = parse_citations(sentence)
        if not ids:
            continue
        claim_tokens = _tokens(re.sub(r"\[E\d+\]", "", sentence))
        evidence_tokens: set[str] = set()
        for evidence_id in ids:
            item = ledger.get(evidence_id)
            if item:
                evidence_tokens |= _tokens(f"{item.title} {item.content}")
        if not claim_tokens:
            continue
        assessed += 1
        if len(claim_tokens & evidence_tokens) / len(claim_tokens) >= 0.2:
            supported += 1
    return round(supported / assessed, 4) if assessed else 0.0


def tool_selection_metrics(
    actual: set[str], expected: set[str]
) -> tuple[float, float]:
    """Return expected-bundle precision and recall."""
    precision = len(actual & expected) / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = len(actual & expected) / len(expected) if expected else 1.0
    return round(precision, 4), round(recall, 4)


def search_query_quality(question: str, attempts: list[dict[str, Any]]) -> float:
    """Score source-tailoring, concision, and exact-question avoidance."""
    if not attempts:
        return 0.0
    normalized_question = " ".join(question.lower().split()).rstrip("?")
    scores: list[float] = []
    limits = {"academic": 12, "wikipedia": 12, "web": 24}
    for attempt in attempts:
        query = " ".join(str(attempt.get("query", "")).lower().split()).rstrip("?")
        words = query.split()
        score = 0.0
        if query:
            score += 0.4
        if len(words) <= limits.get(attempt.get("bundle"), 20):
            score += 0.4
        if len(normalized_question.split()) <= 8 or query != normalized_question:
            score += 0.2
        scores.append(score)
    return round(statistics.mean(scores), 4)


def retrieval_coverage(result: dict[str, Any], required_topics: list[str]) -> float:
    """Measure whether expected topic strings appear in collected evidence."""
    if not required_topics:
        return 1.0
    corpus = " ".join(
        f"{row.get('title', '')} {row.get('content', '')}"
        for row in result.get("evidence_ledger") or result.get("research_findings", [])
    ).lower()
    covered = sum(1 for topic in required_topics if topic.lower() in corpus)
    return round(covered / len(required_topics), 4)


def evaluate_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one run with deterministic metrics and explicit proxy labels."""
    ledger = _ledger_from_result(result)
    report = result.get("report") or result.get("final_report", "")
    allowed = result.get("evidence_coverage", {}).get("selected_for_context")
    verification = CitationVerifier().verify(report, ledger, allowed or None)
    actual_bundles = {
        row.get("bundle")
        for row in result.get("tool_call_history", [])
        if row.get("bundle")
    } or set(result.get("sources_used", []))
    expected_bundles = set(case.get("expected_bundles", []))
    selection_precision, selection_recall = tool_selection_metrics(
        actual_bundles, expected_bundles
    )
    repeated_queries = len(result.get("queries_attempted", [])) - len({
        (row.get("bundle"), row.get("normalized_query") or row.get("query"))
        for row in result.get("queries_attempted", [])
    })
    expected_behavior = case.get("expected_behavior", "answer")
    abstained = any(
        phrase in report.lower()
        for phrase in ("insufficient evidence", "cannot verify", "cannot provide a supported")
    )
    conflict_expected = expected_behavior == "disclose_conflict"
    conflict_handling = (
        1.0
        if not conflict_expected
        else float(bool(result.get("conflicts")) and "conflict" in report.lower())
    )
    abstention_score = (
        float(abstained) if expected_behavior == "abstain" else float(not abstained)
    )
    return {
        "answer_relevance": answer_relevance(case["question"], report),
        "answer_relevance_method": "deterministic_lexical_proxy",
        "faithfulness": faithfulness_to_evidence(report, ledger),
        "faithfulness_method": "deterministic_cited_overlap_proxy",
        "citation_validity": float(verification.is_valid),
        "citation_coverage": verification.citation_coverage,
        "tool_selection_precision": selection_precision,
        "tool_selection_recall": selection_recall,
        "retrieval_coverage": retrieval_coverage(result, case.get("required_topics", [])),
        "search_query_quality": search_query_quality(
            case["question"], result.get("queries_attempted", [])
        ),
        "conflict_handling": conflict_handling,
        "correct_abstention": abstention_score,
        "tool_calls": result.get("tool_calls", len(result.get("tool_call_history", []))),
        "iterations": result.get("iterations", 1 if report else 0),
        "latency_s": result.get("elapsed_time", result.get("duration", 0.0)),
        "repeated_queries": max(0, repeated_queries),
        "completion_reason": result.get("stop_reason", "legacy_completed"),
    }


def aggregate_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate numeric metrics while retaining completion-reason counts."""
    numeric_keys = (
        "answer_relevance", "faithfulness", "citation_validity", "citation_coverage",
        "tool_selection_precision", "tool_selection_recall", "retrieval_coverage",
        "search_query_quality", "conflict_handling", "correct_abstention", "tool_calls",
        "iterations", "latency_s", "repeated_queries",
    )
    aggregate = {key: _safe_mean(row.get(key) for row in rows) for key in numeric_keys}
    reasons: dict[str, int] = {}
    for row in rows:
        reason = row.get("completion_reason", "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
    aggregate["completion_reasons"] = reasons
    aggregate["num_questions"] = len(rows)
    return aggregate
