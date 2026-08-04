"""Hermetic end-to-end tests for the bounded iterative runtime."""

from __future__ import annotations

import re

from agent.models import ResearchDecision, ResearchRequirements
from agent.policies import RuntimeLimits
from agent.runtime import ResearchAgentRuntime
from tool_bundles.base import BundleTool, EvaluationCase, ToolBundle
from tool_bundles.registry import ToolBundleRegistry


class ScriptedModel:
    def __init__(self, decisions, report=None, repair=None):
        self.decisions = list(decisions)
        self.report = report
        self.repair = repair
        self.decision_payloads = []
        self.repair_calls = 0

    def analyze(self, question):
        return ResearchRequirements(
            requirements=["Find a supported answer."], subquestions=[question]
        )

    def decide(self, payload):
        self.decision_payloads.append(payload)
        return self.decisions.pop(0)

    def write_report(self, payload):
        if isinstance(self.report, Exception):
            raise self.report
        if self.report is not None:
            return self.report
        ids = list(dict.fromkeys(re.findall(r"\[(E\d+)\]", payload["evidence_context"])))
        citations = "".join(f"[{eid}]" for eid in ids)
        return (
            "## Answer\n\nThe collected evidence supports this detailed response to "
            f"the user research question {citations}.\n\n## Limitations\n\n"
            "- The answer is limited to the selected evidence."
        )

    def repair_report(self, payload):
        self.repair_calls += 1
        if isinstance(self.repair, Exception):
            raise self.repair
        if self.repair is not None:
            return self.repair
        ids = re.findall(r"\[(E\d+)\]", payload["evidence_context"])
        return (
            "## Repaired Answer\n\nThis detailed supported paragraph is grounded in "
            f"the available evidence [{ids[0]}].\n\n## Limitations\n\n- Bounded evidence."
        )


def search(bundle, query, summary="search", gaps=None):
    return ResearchDecision(
        action="search",
        bundle=bundle,
        query=query,
        action_summary=summary,
        unresolved_gaps=gaps or ["Need more evidence."],
    )


def finish(gaps=None):
    return ResearchDecision(
        action="finish",
        action_summary="Evidence inspected; stop.",
        unresolved_gaps=gaps or [],
    )


def make_bundle(name, rows=None, failure=None):
    def execute(query):
        if failure:
            raise failure
        if callable(rows):
            return rows(query)
        return rows or [{
            "title": f"{name} result",
            "url": f"https://{name}.test/{query.replace(' ', '-')}",
            "content": f"Evidence returned by {name} for {query} with enough supporting detail.",
        }]

    return ToolBundle(
        name=name,
        source_type=name,
        description=f"{name} capability",
        when_to_use=f"Use for {name} evidence.",
        when_not_to_use="Avoid when irrelevant.",
        tools=(BundleTool(f"{name}_search", "fixture search", execute),),
        evaluation_cases=(EvaluationCase("fixture", True),),
        result_limit=5,
        timeout_seconds=1,
    )


def runtime(model, bundles, **limit_overrides):
    defaults = dict(
        max_iterations=5,
        max_tool_calls=5,
        tool_timeout_seconds=1,
        max_elapsed_seconds=10,
        max_context_chars=2000,
        max_evidence_chars=800,
        max_consecutive_no_new=2,
    )
    defaults.update(limit_overrides)
    return ResearchAgentRuntime(
        model=model,
        registry=ToolBundleRegistry(bundles),
        limits=RuntimeLimits(**defaults),
    )


def test_model_selects_academic_bundle_for_technical_fixture():
    model = ScriptedModel([search("academic", "transformer self-attention"), finish()])
    result = runtime(model, [make_bundle("web"), make_bundle("academic")]).run("technical q")
    assert result["sources_used"] == ["academic"]
    assert result["queries_attempted"][0]["query"] == "transformer self-attention"


def test_second_search_follows_missing_information_signal():
    model = ScriptedModel([
        search("wikipedia", "Ada Lovelace", gaps=["Need the later influence."]),
        search("web", "Ada Lovelace influence computing", gaps=["Need modern evidence."]),
        finish(),
    ])
    result = runtime(model, [make_bundle("wikipedia"), make_bundle("web")]).run("multi-hop q")
    assert result["tool_calls"] == 2
    assert "[E1]" in model.decision_payloads[1]["evidence_context"]
    assert [row["bundle"] for row in result["tool_call_history"]] == ["wikipedia", "web"]


def test_simple_question_stops_early():
    model = ScriptedModel([search("wikipedia", "photosynthesis"), finish()])
    result = runtime(model, [make_bundle("wikipedia")]).run("What is photosynthesis?")
    assert result["iterations"] == 2
    assert result["tool_calls"] == 1
    assert result["stop_reason"] == "evidence_sufficient"


def test_maximum_iteration_limit_is_enforced():
    model = ScriptedModel([search("web", "q one"), search("web", "q two")])
    result = runtime(model, [make_bundle("web")], max_iterations=2).run("keep searching")
    assert result["iterations"] == 2
    assert result["stop_reason"] == "iteration_limit"


def test_maximum_tool_call_limit_is_enforced():
    model = ScriptedModel([search("web", "only call")])
    result = runtime(model, [make_bundle("web")], max_tool_calls=1).run("bounded")
    assert result["tool_calls"] == 1
    assert result["stop_reason"] == "tool_budget_exhausted"


def test_duplicate_query_is_blocked_before_tool_execution():
    model = ScriptedModel([search("web", "same query"), search("web", "same query")])
    result = runtime(model, [make_bundle("web")]).run("duplicate")
    assert result["tool_calls"] == 1
    assert result["stop_reason"] == "no_new_evidence"
    assert "Duplicate" in result["trace"][-1]["errors"][0]


def test_tool_failure_is_traced_and_results_in_abstention():
    model = ScriptedModel([
        search("web", "failing query"),
        finish(["The source remains unavailable."]),
    ])
    result = runtime(
        model, [make_bundle("web", failure=RuntimeError("API_KEY: secret-value unavailable"))]
    ).run("unanswerable")
    assert result["stop_reason"] == "all_tools_failed"
    assert "Insufficient Evidence" in result["report"]
    assert "secret-value" not in result["tool_call_history"][0]["error"]
    assert result["verification_result"]["is_valid"] is True


def test_multi_source_collection_preserves_ids_and_trace():
    model = ScriptedModel([
        search("web", "side a"),
        search("academic", "side b"),
        finish(),
    ])
    result = runtime(model, [make_bundle("web"), make_bundle("academic")]).run("compare")
    assert [row["evidence_id"] for row in result["evidence_ledger"]] == ["E1", "E2"]
    assert result["evidence_coverage"]["cited"] == ["E1", "E2"]
    assert result["trace"][0]["new_evidence_ids"] == ["E1"]


def test_one_bounded_repair_can_make_citations_valid():
    uncited = "This draft contains a detailed substantive claim but has no evidence citation anywhere."
    model = ScriptedModel(
        [search("web", "q"), finish()],
        report=uncited,
        repair=(
            "## Answer\n\nThis repaired substantive research claim is supported by "
            "the selected evidence [E1].\n\n## Limitations\n\n- Fixture only."
        ),
    )
    result = runtime(model, [make_bundle("web")]).run("repair")
    assert model.repair_calls == 1
    assert result["verification_result"]["repair_attempted"] is True
    assert result["verification_result"]["is_valid"] is True


def test_failed_repair_returns_visible_warning():
    model = ScriptedModel(
        [search("web", "q"), finish()],
        report="This long factual claim has no citation and therefore should fail verification.",
        repair="This repaired factual claim still has no citation and therefore remains invalid.",
    )
    result = runtime(model, [make_bundle("web")]).run("bad repair")
    assert result["verification_result"]["is_valid"] is False
    assert "Citation verification warning" in result["report"]


def test_conflicts_are_exposed_in_trace_and_report():
    def rows(query):
        value = "50" if "first" in query else "75"
        return [{
            "title": query,
            "url": f"https://source.test/{value}",
            "content": f"The national solar capacity was {value} GW in the survey.",
        }]

    model = ScriptedModel([
        search("web", "first estimate"),
        search("web", "second estimate"),
        finish(),
    ])
    result = runtime(model, [make_bundle("web", rows=rows)]).run("capacity")
    assert result["conflicts"][0]["kind"] == "numeric"
    assert result["trace"][1]["conflicts_detected"] == ["C1"]
    assert "Detected Evidence Conflicts" in result["report"]


def test_disabling_a_bundle_does_not_crash_runtime():
    model = ScriptedModel([search("academic", "paper") for _ in range(2)])
    result = runtime(model, [make_bundle("web")], max_iterations=2).run("paper")
    assert result["stop_reason"] == "iteration_limit"
    assert result["tool_calls"] == 0
    assert "Insufficient Evidence" in result["report"]
