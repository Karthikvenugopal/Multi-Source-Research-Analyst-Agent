"""Deterministic parsing, reference rendering, and citation verification."""

from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, Field

from evidence.ledger import EvidenceLedger

_CITATION_RE = re.compile(r"\[(E[1-9]\d*)\]")
_REFERENCE_RE = re.compile(r"^\s*(?:<a[^>]+></a>)?\s*\*\*\[(E[1-9]\d*)\]\*\*", re.M)
_REFERENCE_HEADING_RE = re.compile(r"^#{1,6}\s+References\s*$", re.I | re.M)
_MALFORMED_RE = re.compile(r"\[(?:[eE]\d*[A-Za-z]+|[eE]0\d*|[eE]\d*|\d+)\]")
_WORD_RE = re.compile(r"\b[\w'-]+\b")


class CitationIssue(BaseModel):
    """One machine-readable citation failure."""

    code: str
    message: str
    evidence_id: str | None = None
    paragraph_index: int | None = None


class CitationVerificationResult(BaseModel):
    """Complete deterministic citation verification result."""

    is_valid: bool
    cited_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    unsupported_ids: list[str] = Field(default_factory=list)
    uncited_paragraphs: list[int] = Field(default_factory=list)
    substantive_paragraphs: int = 0
    cited_substantive_paragraphs: int = 0
    citation_coverage: float = 0.0
    issues: list[CitationIssue] = Field(default_factory=list)
    repair_attempted: bool = False


def split_references(report: str) -> tuple[str, str]:
    """Split a report body from its final References section."""
    match = _REFERENCE_HEADING_RE.search(report)
    if not match:
        return report.rstrip(), ""
    return report[: match.start()].rstrip(), report[match.end() :].strip()


def parse_citations(report: str) -> list[str]:
    """Return inline evidence IDs in occurrence order, excluding references."""
    body, _ = split_references(report)
    return _CITATION_RE.findall(body)


def render_references(
    report_body: str,
    ledger: EvidenceLedger,
    allowed_ids: Iterable[str] | None = None,
) -> str:
    """Append canonical references for valid citations in first-use order."""
    body, _ = split_references(report_body)
    allowed = set(allowed_ids) if allowed_ids is not None else {
        item.evidence_id for item in ledger.items
    }
    ordered = list(dict.fromkeys(parse_citations(body)))
    lines: list[str] = []
    for evidence_id in ordered:
        item = ledger.get(evidence_id)
        if item is None or evidence_id not in allowed:
            continue
        title = item.title.replace("[", "\\[").replace("]", "\\]")
        label = f"[{title}]({item.url})" if item.url else title
        lines.append(
            f'<a id="ref-{evidence_id}"></a>**[{evidence_id}]** '
            f"{label} — {item.source_type.upper()}"
        )
    if not lines:
        return body
    return f"{body}\n\n## References\n\n" + "\n\n".join(lines)


class CitationVerifier:
    """Verify evidence membership, references, syntax, and paragraph coverage."""

    def verify(
        self,
        report: str,
        ledger: EvidenceLedger,
        allowed_ids: Iterable[str] | None = None,
    ) -> CitationVerificationResult:
        """Return structured errors without making any model calls."""
        body, references = split_references(report)
        citations = _CITATION_RE.findall(body)
        reference_ids = _REFERENCE_RE.findall(references)
        ledger_ids = {item.evidence_id for item in ledger.items}
        allowed = set(allowed_ids) if allowed_ids is not None else ledger_ids
        issues: list[CitationIssue] = []

        malformed = [token for token in _MALFORMED_RE.findall(body) if not _CITATION_RE.fullmatch(token)]
        for token in dict.fromkeys(malformed):
            issues.append(CitationIssue(code="malformed_citation", message=f"Malformed citation {token}."))

        unsupported: list[str] = []
        for evidence_id in dict.fromkeys(citations):
            if evidence_id not in ledger_ids:
                unsupported.append(evidence_id)
                issues.append(CitationIssue(
                    code="unknown_evidence",
                    message=f"Citation {evidence_id} is not in the evidence ledger.",
                    evidence_id=evidence_id,
                ))
            elif evidence_id not in allowed:
                unsupported.append(evidence_id)
                issues.append(CitationIssue(
                    code="unavailable_evidence",
                    message=f"Citation {evidence_id} was not provided to the report generator.",
                    evidence_id=evidence_id,
                ))

        for evidence_id in dict.fromkeys(citations):
            if evidence_id in ledger_ids and evidence_id in allowed and evidence_id not in reference_ids:
                issues.append(CitationIssue(
                    code="missing_reference",
                    message=f"Cited evidence {evidence_id} is missing from References.",
                    evidence_id=evidence_id,
                ))
        for evidence_id in dict.fromkeys(reference_ids):
            if evidence_id not in citations:
                issues.append(CitationIssue(
                    code="orphan_reference",
                    message=f"Reference {evidence_id} is not cited in the report body.",
                    evidence_id=evidence_id,
                ))
        for evidence_id in set(reference_ids):
            if reference_ids.count(evidence_id) > 1:
                issues.append(CitationIssue(
                    code="duplicate_reference",
                    message=f"Reference {evidence_id} appears more than once.",
                    evidence_id=evidence_id,
                ))
        for cluster in re.findall(r"(?:\[E[1-9]\d*\])+", body):
            cluster_ids = _CITATION_RE.findall(cluster)
            if len(cluster_ids) != len(set(cluster_ids)):
                issues.append(CitationIssue(
                    code="duplicate_inline_citation",
                    message=f"A citation cluster repeats an evidence ID: {cluster}.",
                ))

        paragraphs = self._substantive_paragraphs(body)
        uncited: list[int] = []
        cited_paragraphs = 0
        for index, paragraph in paragraphs:
            if _CITATION_RE.search(paragraph):
                cited_paragraphs += 1
            else:
                uncited.append(index)
                issues.append(CitationIssue(
                    code="uncited_claim",
                    message=f"Substantive paragraph {index} has no evidence citation.",
                    paragraph_index=index,
                ))
        coverage = cited_paragraphs / len(paragraphs) if paragraphs else 1.0
        valid_cited = [
            evidence_id
            for evidence_id in dict.fromkeys(citations)
            if evidence_id in ledger_ids and evidence_id in allowed
        ]
        return CitationVerificationResult(
            is_valid=not issues,
            cited_ids=valid_cited,
            reference_ids=list(dict.fromkeys(reference_ids)),
            unsupported_ids=unsupported,
            uncited_paragraphs=uncited,
            substantive_paragraphs=len(paragraphs),
            cited_substantive_paragraphs=cited_paragraphs,
            citation_coverage=round(coverage, 4),
            issues=issues,
        )

    @staticmethod
    def _substantive_paragraphs(body: str) -> list[tuple[int, str]]:
        paragraphs: list[tuple[int, str]] = []
        in_code = False
        index = 0
        for block in re.split(r"\n\s*\n", body):
            stripped = block.strip()
            if not stripped:
                continue
            if stripped.startswith("```"):
                in_code = not in_code if stripped.count("```") == 1 else in_code
                continue
            if in_code or stripped.startswith(("#", "- ", "* ", ">", "|")):
                continue
            normalized = " ".join(line.strip() for line in stripped.splitlines())
            words = _WORD_RE.findall(_CITATION_RE.sub("", normalized))
            if len(words) < 8:
                continue
            index += 1
            paragraphs.append((index, normalized))
        return paragraphs
