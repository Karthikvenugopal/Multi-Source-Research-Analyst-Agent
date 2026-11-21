"""Stable evidence IDs, provenance, and substantial duplicate removal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

from evidence.models import EvidenceItem, normalize_content


@dataclass(frozen=True)
class AddResult:
    """Outcome of adding one tool response to a ledger."""

    new_ids: tuple[str, ...]
    duplicate_count: int
    rejected_count: int


class EvidenceLedger:
    """Append-only evidence store with deterministic, stable identifiers."""

    def __init__(self, similarity_threshold: float = 0.92) -> None:
        self._items: list[EvidenceItem] = []
        self._by_id: dict[str, EvidenceItem] = {}
        self._hashes: set[str] = set()
        self.similarity_threshold = similarity_threshold
        self.selected_ids: set[str] = set()
        self.cited_ids: set[str] = set()
        self.omitted_due_to_context: set[str] = set()

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    @property
    def items(self) -> tuple[EvidenceItem, ...]:
        """Return ledger items in stable insertion order."""
        return tuple(self._items)

    def get(self, evidence_id: str) -> EvidenceItem | None:
        """Look up an item by stable evidence ID."""
        return self._by_id.get(evidence_id)

    def add_candidates(
        self,
        source_type: str,
        query: str,
        candidates: Iterable[dict[str, Any]],
    ) -> AddResult:
        """Normalize candidates, reject duplicates, and allocate stable IDs."""
        new_ids: list[str] = []
        duplicates = 0
        rejected = 0
        for candidate in candidates:
            try:
                provisional = EvidenceItem.from_candidate(
                    f"E{len(self._items) + 1}", source_type, query, candidate
                )
            except (TypeError, ValueError):
                rejected += 1
                continue
            if provisional.content_hash in self._hashes or self._is_substantial_duplicate(
                provisional
            ):
                duplicates += 1
                continue
            self._items.append(provisional)
            self._by_id[provisional.evidence_id] = provisional
            self._hashes.add(provisional.content_hash)
            new_ids.append(provisional.evidence_id)
        return AddResult(tuple(new_ids), duplicates, rejected)

    def mark_selected(self, ids: Iterable[str], omitted: Iterable[str] = ()) -> None:
        """Record evidence context selection without mutating source records."""
        self.selected_ids.update(eid for eid in ids if eid in self._by_id)
        self.omitted_due_to_context.update(eid for eid in omitted if eid in self._by_id)

    def mark_cited(self, ids: Iterable[str]) -> None:
        """Record valid final-report citations."""
        self.cited_ids.update(eid for eid in ids if eid in self._by_id)

    def coverage(self) -> dict[str, list[str]]:
        """Describe retrieval, selection, citation, and non-use deterministically."""
        retrieved = [item.evidence_id for item in self._items]
        cited = [eid for eid in retrieved if eid in self.cited_ids]
        selected = [eid for eid in retrieved if eid in self.selected_ids]
        return {
            "retrieved": retrieved,
            "selected_for_context": selected,
            "cited": cited,
            "not_used": [eid for eid in retrieved if eid not in self.cited_ids],
            "omitted_due_to_context": [
                eid for eid in retrieved if eid in self.omitted_due_to_context
            ],
        }

    def to_list(self) -> list[dict[str, Any]]:
        """Serialize records for traces, UI, and evaluation output."""
        return [item.model_dump(mode="json") for item in self._items]

    def _is_substantial_duplicate(self, candidate: EvidenceItem) -> bool:
        normalized = self._comparison_text(candidate.content)
        if not normalized:
            return True
        for existing in self._items:
            other = self._comparison_text(existing.content)
            candidate_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", normalized))
            existing_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", other))
            # Near-identical prose with incompatible values is exactly the kind
            # of evidence the conflict detector needs to retain.
            if candidate_numbers and existing_numbers and candidate_numbers != existing_numbers:
                continue
            if (
                len(normalized) >= 100
                and candidate.url
                and existing.url
                and candidate.url == existing.url
            ):
                if SequenceMatcher(None, normalized, other).ratio() >= 0.75:
                    return True
            if SequenceMatcher(None, normalized, other).ratio() >= self.similarity_threshold:
                return True
        return False

    @staticmethod
    def _comparison_text(content: str) -> str:
        text = normalize_content(content).lower()
        return re.sub(r"[^a-z0-9 ]", "", text)[:6000]
