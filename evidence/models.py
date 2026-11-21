"""Validated models shared by the evidence subsystem."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def normalize_content(text: str) -> str:
    """Normalize content for stable hashing without altering stored source text."""
    return re.sub(r"\s+", " ", text).strip()


def content_digest(text: str) -> str:
    """Return a deterministic SHA-256 digest of normalized source content."""
    return hashlib.sha256(normalize_content(text).encode("utf-8")).hexdigest()


class EvidenceItem(BaseModel):
    """One immutable-in-practice source item in the central ledger."""

    evidence_id: str = Field(pattern=r"^E[1-9]\d*$")
    source_type: str
    title: str
    url: str = ""
    authors: list[str] = Field(default_factory=list)
    published_at: str | None = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    query: str
    content: str
    content_hash: str
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_candidate(
        cls,
        evidence_id: str,
        source_type: str,
        query: str,
        candidate: dict[str, Any],
    ) -> "EvidenceItem":
        """Validate and convert one normalized tool result."""
        content = str(candidate.get("content") or "").strip()
        if not content:
            raise ValueError("evidence content must not be empty")
        metadata = dict(candidate.get("metadata") or {})
        candidate_source = candidate.get("source_type")
        if candidate_source and candidate_source != source_type:
            metadata["reported_source_type"] = candidate_source
        return cls(
            evidence_id=evidence_id,
            source_type=source_type,
            title=str(candidate.get("title") or "Untitled"),
            url=str(candidate.get("url") or ""),
            authors=[str(author) for author in candidate.get("authors") or []],
            published_at=candidate.get("published_at"),
            query=query,
            content=content,
            content_hash=content_digest(content),
            # Relevance is reserved for an explicit model assessment. Provider
            # scores remain deterministic metadata and are not promoted here.
            relevance_score=candidate.get("relevance_score"),
            metadata=metadata,
        )


class EvidenceConflict(BaseModel):
    """A likely, explainable contradiction between two evidence items."""

    conflict_id: str
    evidence_ids: tuple[str, str]
    kind: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
