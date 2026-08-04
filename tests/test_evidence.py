"""Hermetic tests for ledger, context selection, and conflict signals."""

from evidence.conflicts import ConflictDetector
from evidence.ledger import EvidenceLedger
from evidence.selector import EvidenceSelector


def candidate(content: str, title: str = "Source", url: str = "https://example.test"):
    return {"title": title, "url": url, "content": content, "metadata": {}}


def test_evidence_ids_are_stable_and_queries_are_preserved():
    ledger = EvidenceLedger()
    first = ledger.add_candidates("web", "first query", [candidate("Alpha evidence text.")])
    duplicate = ledger.add_candidates("web", "second query", [candidate("Alpha evidence text.")])
    second = ledger.add_candidates("academic", "paper terms", [candidate("Beta evidence text.")])

    assert first.new_ids == ("E1",)
    assert duplicate.duplicate_count == 1
    assert second.new_ids == ("E2",)
    assert ledger.get("E1").query == "first query"
    assert ledger.get("E2").source_type == "academic"


def test_substantially_identical_evidence_is_removed():
    ledger = EvidenceLedger(similarity_threshold=0.88)
    ledger.add_candidates("web", "q1", [candidate("The result says solar output is 50 GW today.")])
    result = ledger.add_candidates(
        "web", "q2", [candidate("The result says solar output is 50 GW today!")]
    )
    assert result.duplicate_count == 1
    assert len(ledger) == 1


def test_context_selection_respects_budget_and_tracks_omissions():
    ledger = EvidenceLedger()
    for index in range(4):
        ledger.add_candidates(
            "web",
            f"q{index}",
            [candidate((f"Relevant solar sentence {index}. " + "verbose " * 100), url=f"u{index}")],
        )
    selection = EvidenceSelector(max_context_chars=420, max_item_chars=180).select(
        ledger, "solar"
    )
    assert selection.passage_chars <= 420
    assert selection.selected_ids
    assert selection.omitted_ids
    assert set(selection.omitted_ids) == set(ledger.coverage()["omitted_due_to_context"])


def test_selector_prefers_relevant_passage_over_fixed_prefix():
    ledger = EvidenceLedger()
    ledger.add_candidates(
        "academic",
        "attention",
        [candidate("Unrelated opening.\n\nSelf-attention uses query key value projections.")],
    )
    selected = EvidenceSelector(max_context_chars=500, max_item_chars=90).select(
        ledger, "self-attention query key"
    )
    assert "query key" in selected.context


def test_conflict_detector_finds_opposing_numeric_claims():
    ledger = EvidenceLedger()
    ledger.add_candidates(
        "web", "capacity", [candidate("The national solar capacity was 50 GW in the survey.", url="a")]
    )
    ledger.add_candidates(
        "academic", "capacity", [candidate("The national solar capacity was 75 GW in the survey.", url="b")]
    )
    conflicts = ConflictDetector().detect(ledger.items)
    assert conflicts
    assert conflicts[0].kind == "numeric"
    assert conflicts[0].evidence_ids == ("E1", "E2")


def test_conflict_detector_ignores_unrelated_numbers():
    ledger = EvidenceLedger()
    ledger.add_candidates("web", "q", [candidate("Solar output was 50 GW.", url="a")])
    ledger.add_candidates("academic", "q", [candidate("Penguins can swim at 6 mph.", url="b")])
    assert ConflictDetector().detect(ledger.items) == []
