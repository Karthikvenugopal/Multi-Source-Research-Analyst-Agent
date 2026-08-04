"""Transparent, passage-level evidence context selection."""

from __future__ import annotations

import re
from dataclasses import dataclass

from evidence.ledger import EvidenceLedger
from evidence.models import EvidenceItem

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]+")
_STOPWORDS = {
    "about", "after", "also", "and", "are", "from", "have", "into", "its",
    "that", "the", "their", "this", "what", "when", "where", "which", "who",
    "why", "with", "would", "could", "should", "does", "how",
}


@dataclass(frozen=True)
class ContextSelection:
    """Selected prompt text plus auditable inclusion metadata."""

    context: str
    selected_ids: tuple[str, ...]
    omitted_ids: tuple[str, ...]
    passage_chars: int
    approximate_tokens: int


class EvidenceSelector:
    """Choose relevant passages while retaining full evidence in the ledger."""

    def __init__(self, max_context_chars: int = 14_000, max_item_chars: int = 4_000):
        self.max_context_chars = max(256, max_context_chars)
        self.max_item_chars = max(128, min(max_item_chars, self.max_context_chars))

    def select(self, ledger: EvidenceLedger, focus: str) -> ContextSelection:
        """Rank records lexically and include their most relevant passages."""
        focus_tokens = self._tokens(focus)
        ranked = sorted(
            ledger.items,
            key=lambda item: (-self._item_score(item, focus_tokens), int(item.evidence_id[1:])),
        )
        blocks: list[str] = []
        selected: list[str] = []
        used = 0
        for item in ranked:
            passage = self._best_passage(item.content, focus_tokens)
            header = (
                f"[{item.evidence_id}] source={item.source_type}; title={item.title}; "
                f"url={item.url or '(none)'}; query={item.query}\n"
            )
            block = header + passage
            extra = len(block) + (2 if blocks else 0)
            if used + extra > self.max_context_chars:
                continue
            blocks.append(block)
            selected.append(item.evidence_id)
            used += extra
        omitted = tuple(
            item.evidence_id for item in ledger.items if item.evidence_id not in selected
        )
        ledger.mark_selected(selected, omitted)
        return ContextSelection(
            context="\n\n".join(blocks) or "(no evidence selected)",
            selected_ids=tuple(selected),
            omitted_ids=omitted,
            passage_chars=used,
            approximate_tokens=(used + 3) // 4,
        )

    def _best_passage(self, content: str, focus_tokens: set[str]) -> str:
        chunks = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        if len(chunks) <= 1:
            chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", content) if part.strip()]
        if not chunks:
            return ""
        ranked = sorted(
            enumerate(chunks),
            key=lambda pair: (-len(self._tokens(pair[1]) & focus_tokens), pair[0]),
        )
        chosen: list[tuple[int, str]] = []
        total = 0
        for index, chunk in ranked:
            remaining = self.max_item_chars - total
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                chunk = self._clip_at_word(chunk, remaining)
            chosen.append((index, chunk))
            total += len(chunk) + 1
        return " ".join(text for _, text in sorted(chosen))

    @staticmethod
    def _clip_at_word(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        clipped = text[: max(1, limit - 1)].rsplit(" ", 1)[0]
        return f"{clipped}…"

    def _item_score(self, item: EvidenceItem, focus_tokens: set[str]) -> float:
        content_tokens = self._tokens(f"{item.title} {item.content}")
        if not focus_tokens:
            return 0.0
        return len(content_tokens & focus_tokens) / len(focus_tokens)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS}
