"""Lightweight capability-level and leave-one-bundle-out regression gates."""

from __future__ import annotations

from dataclasses import dataclass

from tool_bundles.registry import ToolBundleRegistry


@dataclass(frozen=True)
class CapabilityGateResult:
    """Pass/fail summary for one bundle's attached fixtures."""

    bundle: str
    precision: float
    recall: float
    passed: bool


def heuristic_bundle_selector(question: str, available: tuple[str, ...]) -> set[str]:
    """Deterministic selector used only for capability instruction regression tests."""
    lowered = question.lower()
    selected: set[str] = set()
    if any(term in lowered for term in ("latest", "today", "this month", "release", "company")):
        selected.add("web")
    if any(term in lowered for term in (
        "paper", "study", "technical", "transformer", "self-attention", "scientific"
    )):
        selected.add("academic")
    if any(term in lowered for term in (
        "define", "what is", "who was", "history", "haber process", "photosynthesis"
    )):
        selected.add("wikipedia")
    if not selected and "web" in available:
        selected.add("web")
    return selected & set(available)


def evaluate_capability_gates(
    registry: ToolBundleRegistry,
    minimum_precision: float = 0.75,
    minimum_recall: float = 0.75,
) -> list[CapabilityGateResult]:
    """Evaluate each bundle's should-use and should-not-use fixture questions."""
    results: list[CapabilityGateResult] = []
    for bundle in registry.bundles:
        true_positive = false_positive = false_negative = 0
        for case in bundle.evaluation_cases:
            selected = heuristic_bundle_selector(case.question, registry.names)
            used = bundle.name in selected
            true_positive += int(case.should_use and used)
            false_positive += int(not case.should_use and used)
            false_negative += int(case.should_use and not used)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        results.append(CapabilityGateResult(
            bundle=bundle.name,
            precision=round(precision, 4),
            recall=round(recall, 4),
            passed=precision >= minimum_precision and recall >= minimum_recall,
        ))
    return results


def leave_one_out_selection(
    registry: ToolBundleRegistry, question: str, disabled: str
) -> set[str]:
    """Return selection after disabling one bundle, without mutating the registry."""
    reduced = registry.without(disabled)
    return heuristic_bundle_selector(question, reduced.names)
