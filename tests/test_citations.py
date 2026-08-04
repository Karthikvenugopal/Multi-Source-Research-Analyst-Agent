"""Citation parser and deterministic verifier tests."""

from evidence.citations import CitationVerifier, parse_citations, render_references
from evidence.ledger import EvidenceLedger


def ledger_with_two() -> EvidenceLedger:
    ledger = EvidenceLedger()
    ledger.add_candidates("web", "q", [{
        "title": "First", "url": "https://one.test", "content": "Grounded first claim."
    }])
    ledger.add_candidates("academic", "q", [{
        "title": "Second", "url": "https://two.test", "content": "Grounded second claim."
    }])
    return ledger


def test_citation_parser_uses_evidence_ids_and_ignores_references():
    report = "A claim [E2] and another [E1].\n\n## References\n\n**[E2]** Source"
    assert parse_citations(report) == ["E2", "E1"]


def test_verifier_accepts_canonical_grounded_report():
    ledger = ledger_with_two()
    body = (
        "## Finding\n\nThe collected evidence supports this substantive research "
        "finding for the requested question [E1][E2]."
    )
    report = render_references(body, ledger, {"E1", "E2"})
    result = CitationVerifier().verify(report, ledger, {"E1", "E2"})
    assert result.is_valid
    assert result.cited_ids == ["E1", "E2"]
    assert result.citation_coverage == 1.0


def test_verifier_rejects_unknown_and_unavailable_citations():
    ledger = ledger_with_two()
    body = (
        "This substantive paragraph makes a detailed claim using unavailable "
        "and invented evidence [E2][E99]."
    )
    report = render_references(body, ledger, {"E1"})
    result = CitationVerifier().verify(report, ledger, {"E1"})
    codes = {issue.code for issue in result.issues}
    assert not result.is_valid
    assert result.unsupported_ids == ["E2", "E99"]
    assert {"unavailable_evidence", "unknown_evidence"} <= codes


def test_verifier_detects_uncited_substantive_paragraph():
    ledger = ledger_with_two()
    body = "This paragraph makes a detailed factual assertion but provides no source citation at all."
    result = CitationVerifier().verify(body, ledger)
    assert result.uncited_paragraphs == [1]
    assert result.citation_coverage == 0.0


def test_verifier_detects_malformed_duplicate_and_orphaned_entries():
    ledger = ledger_with_two()
    report = (
        "A sufficiently detailed factual claim appears here [E1][E1] plus [E0].\n\n"
        "## References\n\n**[E1]** One\n\n**[E1]** Again\n\n**[E2]** Orphan"
    )
    codes = {issue.code for issue in CitationVerifier().verify(report, ledger).issues}
    assert "malformed_citation" in codes
    assert "duplicate_inline_citation" in codes
    assert "duplicate_reference" in codes
    assert "orphan_reference" in codes


def test_verifier_requires_reference_for_each_citation():
    ledger = ledger_with_two()
    result = CitationVerifier().verify(
        "A substantive factual paragraph is supported by collected source evidence [E1].",
        ledger,
    )
    assert any(issue.code == "missing_reference" for issue in result.issues)
