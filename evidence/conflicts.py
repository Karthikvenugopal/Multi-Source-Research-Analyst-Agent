"""Conservative deterministic signals for likely evidence conflicts."""

from __future__ import annotations

import re
from itertools import combinations

from evidence.models import EvidenceConflict, EvidenceItem

_WORD_RE = re.compile(r"\b[a-z][a-z-]{2,}\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")
_NEGATIONS = {"no", "not", "never", "without", "cannot", "isn't", "doesn't"}
_OPPOSITES = (("increase", "decrease"), ("higher", "lower"), ("supports", "refutes"))
_STOPWORDS = {"the", "and", "that", "with", "from", "this", "were", "was", "are", "for"}


class ConflictDetector:
    """Flag high-signal numeric, date, negation, and directional disagreements.

    This detector intentionally emits candidates for inspection; it does not
    claim semantic contradiction detection is complete.
    """

    def detect(self, items: tuple[EvidenceItem, ...]) -> list[EvidenceConflict]:
        conflicts: list[EvidenceConflict] = []
        for left, right in combinations(items, 2):
            if left.source_type == right.source_type and left.url == right.url:
                continue
            candidate = self._compare(left, right)
            if candidate:
                candidate.conflict_id = f"C{len(conflicts) + 1}"
                conflicts.append(candidate)
        return conflicts

    def _compare(self, left: EvidenceItem, right: EvidenceItem) -> EvidenceConflict | None:
        left_words = self._words(left.content)
        right_words = self._words(right.content)
        shared = left_words & right_words
        if len(shared) < 3:
            return None

        left_numbers = set(_NUMBER_RE.findall(left.content))
        right_numbers = set(_NUMBER_RE.findall(right.content))
        left_years = {n for n in left_numbers if len(n) == 4 and n.startswith(("19", "20"))}
        right_years = {n for n in right_numbers if len(n) == 4 and n.startswith(("19", "20"))}
        if left_years and right_years and left_years.isdisjoint(right_years):
            return self._conflict(left, right, "date", left_years, right_years)

        left_values = left_numbers - left_years
        right_values = right_numbers - right_years
        if left_values and right_values and left_values.isdisjoint(right_values):
            return self._conflict(left, right, "numeric", left_values, right_values)

        left_negated = bool(left_words & _NEGATIONS)
        right_negated = bool(right_words & _NEGATIONS)
        union = (left_words | right_words) - _NEGATIONS
        overlap = len((left_words & right_words) - _NEGATIONS) / max(1, len(union))
        if left_negated != right_negated and overlap >= 0.45:
            return self._conflict(left, right, "negation", set(), set())

        for positive, negative in _OPPOSITES:
            if (positive in left_words and negative in right_words) or (
                negative in left_words and positive in right_words
            ):
                return self._conflict(left, right, "directional", {positive}, {negative})
        return None

    @staticmethod
    def _conflict(
        left: EvidenceItem,
        right: EvidenceItem,
        kind: str,
        left_values: set[str],
        right_values: set[str],
    ) -> EvidenceConflict:
        values = ""
        if left_values or right_values:
            values = f" ({sorted(left_values)} vs {sorted(right_values)})"
        return EvidenceConflict(
            conflict_id="pending",
            evidence_ids=(left.evidence_id, right.evidence_id),
            kind=kind,
            summary=(
                f"Possible {kind} disagreement between {left.evidence_id} and "
                f"{right.evidence_id}{values}."
            ),
            details={"left_title": left.title, "right_title": right.title},
        )

    @staticmethod
    def _words(text: str) -> set[str]:
        return {word for word in _WORD_RE.findall(text.lower()) if word not in _STOPWORDS}
