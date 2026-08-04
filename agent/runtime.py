"""Model-directed, bounded iterative research runtime."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from agent.models import LangChainResearchModel, ResearchDecision, ResearchModel
from agent.policies import HeuristicFallbackPolicy, RuntimeLimits
from agent.state import RuntimeState
from evidence.citations import CitationVerifier, render_references
from evidence.conflicts import ConflictDetector
from evidence.selector import EvidenceSelector
from llm_manager import LLMManager
from tool_bundles.base import ToolBundle
from tool_bundles.registry import ToolBundleRegistry, build_default_registry


class ResearchAgentRuntime:
    """Run inspect/search iterations, then generate and verify one cited report."""

    def __init__(
        self,
        model: ResearchModel | None = None,
        registry: ToolBundleRegistry | None = None,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self.limits = limits or RuntimeLimits.from_config()
        self.registry = registry or build_default_registry()
        self.model: ResearchModel = model or LangChainResearchModel(LLMManager().llm)
        self.fallback = HeuristicFallbackPolicy()
        self.selector = EvidenceSelector(
            self.limits.max_context_chars, self.limits.max_evidence_chars
        )
        self.conflict_detector = ConflictDetector()
        self.citation_verifier = CitationVerifier()

    def run(self, question: str) -> dict[str, Any]:
        """Research one question within deterministic limits and return a traceable result."""
        normalized_question = " ".join(question.split()).strip()
        if not normalized_question:
            raise ValueError("question must not be empty")
        state = RuntimeState(question=normalized_question)
        started = time.monotonic()
        state.requirements = self._analyze(normalized_question)
        state.unresolved_gaps = list(state.requirements.requirements)

        if not self.registry.bundles:
            state.stop_reason = "all_tools_failed"
        else:
            self._research_loop(state, started)
        self._generate_and_verify(state)
        state.elapsed_time = round(time.monotonic() - started, 4)
        return state.to_result()

    def _research_loop(self, state: RuntimeState, started: float) -> None:
        consecutive_no_new = 0
        failed_calls = 0
        for iteration in range(1, self.limits.max_iterations + 1):
            state.iterations = iteration
            if time.monotonic() - started >= self.limits.max_elapsed_seconds:
                state.stop_reason = "time_budget_exhausted"
                self._trace_stop(state, iteration, "Elapsed-time budget reached.")
                break
            selection = self.selector.select(
                state.ledger, " ".join([state.question, *state.unresolved_gaps])
            )
            state.approximate_context_tokens += selection.approximate_tokens
            decision = self._decide(state, selection.context)
            state.unresolved_gaps = self._clean_summaries(decision.unresolved_gaps)

            if decision.action == "finish":
                state.stop_reason = "evidence_sufficient" if len(state.ledger) else (
                    "all_tools_failed" if failed_calls else "no_new_evidence"
                )
                self._append_trace(
                    state,
                    iteration=iteration,
                    action_summary=decision.action_summary,
                    unresolved_gaps=state.unresolved_gaps,
                    stop_decision=state.stop_reason,
                )
                break

            bundle = self.registry.get(decision.bundle or "")
            if bundle is None or not decision.query:
                self._append_trace(
                    state,
                    iteration=iteration,
                    tool_selected=decision.bundle,
                    search_query=decision.query,
                    action_summary=decision.action_summary,
                    unresolved_gaps=state.unresolved_gaps,
                    errors=["Model selected an unavailable bundle or empty query."],
                )
                if iteration == self.limits.max_iterations:
                    state.stop_reason = "iteration_limit"
                continue

            tailored_query = bundle.prepare_query(decision.query)
            normalized_query = self._normalize_query(tailored_query)
            attempted = {
                (row["bundle"], row["normalized_query"])
                for row in state.queries_attempted
            }
            if (bundle.name, normalized_query) in attempted:
                state.stop_reason = "no_new_evidence"
                self._append_trace(
                    state,
                    iteration=iteration,
                    tool_selected=bundle.name,
                    search_query=tailored_query,
                    action_summary=decision.action_summary,
                    unresolved_gaps=state.unresolved_gaps,
                    stop_decision=state.stop_reason,
                    errors=["Duplicate bundle/query pair blocked."],
                )
                break
            if state.tool_calls >= self.limits.max_tool_calls:
                state.stop_reason = "tool_budget_exhausted"
                self._trace_stop(state, iteration, "Tool-call budget reached.")
                break

            state.queries_attempted.append({
                "bundle": bundle.name,
                "query": tailored_query,
                "normalized_query": normalized_query,
            })
            state.tool_calls += 1
            call_started = time.monotonic()
            error: str | None = None
            results: list[dict[str, Any]] = []
            try:
                results = self._execute_with_timeout(bundle, tailored_query)
            except Exception as exc:
                error = self._safe_error(exc)
                failed_calls += 1
            add_result = state.ledger.add_candidates(
                bundle.source_type, tailored_query, results
            )
            if add_result.new_ids:
                consecutive_no_new = 0
            else:
                consecutive_no_new += 1
            state.conflicts = self.conflict_detector.detect(state.ledger.items)
            call_record = {
                "iteration": iteration,
                "bundle": bundle.name,
                "query": tailored_query,
                "result_count": len(results),
                "new_evidence_ids": list(add_result.new_ids),
                "duplicate_results_skipped": add_result.duplicate_count,
                "rejected_results": add_result.rejected_count,
                "duration_seconds": round(time.monotonic() - call_started, 4),
                "error": error,
                "retries": 0,
            }
            state.tool_call_history.append(call_record)
            self._append_trace(
                state,
                iteration=iteration,
                tool_selected=bundle.name,
                search_query=tailored_query,
                action_summary=decision.action_summary,
                tool_result_count=len(results),
                new_evidence_ids=list(add_result.new_ids),
                duplicate_results_skipped=add_result.duplicate_count,
                unresolved_gaps=state.unresolved_gaps,
                conflicts_detected=[conflict.conflict_id for conflict in state.conflicts],
                duration_seconds=call_record["duration_seconds"],
                errors=[error] if error else [],
            )

            if state.tool_calls >= self.limits.max_tool_calls:
                state.stop_reason = "tool_budget_exhausted"
                state.trace[-1]["stop_decision"] = state.stop_reason
                break
            if consecutive_no_new >= self.limits.max_consecutive_no_new:
                state.stop_reason = (
                    "all_tools_failed" if not len(state.ledger) and failed_calls == state.tool_calls
                    else "no_new_evidence"
                )
                state.trace[-1]["stop_decision"] = state.stop_reason
                break
            if iteration == self.limits.max_iterations:
                state.stop_reason = "iteration_limit"
                state.trace[-1]["stop_decision"] = state.stop_reason
                break

        if not state.stop_reason:
            state.stop_reason = "iteration_limit"

    def _generate_and_verify(self, state: RuntimeState) -> None:
        if not len(state.ledger):
            state.report = self._insufficient_report(state)
            result = self.citation_verifier.verify(state.report, state.ledger, set())
            state.verification_result = result.model_dump(mode="json")
            return

        selection = self.selector.select(
            state.ledger, " ".join([state.question, *state.unresolved_gaps])
        )
        state.approximate_context_tokens += selection.approximate_tokens
        payload = {
            "question": state.question,
            "requirements": state.requirements.requirements,
            "stop_reason": state.stop_reason,
            "unresolved_gaps": state.unresolved_gaps,
            "conflicts": [conflict.summary for conflict in state.conflicts],
            "evidence_context": selection.context,
        }
        try:
            draft = self.model.write_report(payload)
        except Exception as exc:
            draft = self._extractive_fallback(state, selection.selected_ids, exc)
        prepared = render_references(
            self._ensure_disclosures(draft, state), state.ledger, selection.selected_ids
        )
        verification = self.citation_verifier.verify(
            prepared, state.ledger, selection.selected_ids
        )

        if not verification.is_valid:
            repair_payload = {
                "draft_report": prepared,
                "evidence_context": selection.context,
                "verification_errors": [
                    issue.model_dump(mode="json") for issue in verification.issues
                ],
            }
            try:
                repaired = self.model.repair_report(repair_payload)
                prepared = render_references(
                    self._ensure_disclosures(repaired, state),
                    state.ledger,
                    selection.selected_ids,
                )
                verification = self.citation_verifier.verify(
                    prepared, state.ledger, selection.selected_ids
                )
            except Exception as exc:
                verification.issues.append(
                    self._repair_error_issue(self._safe_error(exc))
                )
                verification.is_valid = False
            verification.repair_attempted = True

        state.ledger.mark_cited(verification.cited_ids)
        if not verification.is_valid:
            warning = (
                "> ⚠️ **Citation verification warning:** deterministic checks still "
                "found unresolved citation or coverage issues after one repair attempt.\n\n"
            )
            prepared = warning + prepared
        state.report = prepared
        state.verification_result = verification.model_dump(mode="json")

    def _analyze(self, question: str):
        try:
            result = self.model.analyze(question)
            if result.requirements:
                return result
        except Exception:
            pass
        return self.fallback.analyze(question)

    def _decide(self, state: RuntimeState, evidence_context: str) -> ResearchDecision:
        payload = {
            "question": state.question,
            "requirements": state.requirements.requirements,
            "bundle_catalog": self.registry.prompt_catalog(),
            "bundle_names": self.registry.names,
            "queries_attempted": state.queries_attempted,
            "unresolved_gaps": state.unresolved_gaps,
            "conflicts": [conflict.summary for conflict in state.conflicts],
            "evidence_context": evidence_context,
            "evidence_count": len(state.ledger),
        }
        try:
            return self.model.decide(payload)
        except Exception:
            return self.fallback.decide(payload)

    def _execute_with_timeout(self, bundle: ToolBundle, query: str) -> list[dict[str, Any]]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(bundle.execute, query)
        timeout = min(self.limits.tool_timeout_seconds, bundle.timeout_seconds)
        try:
            return future.result(timeout=timeout).results
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(
                f"{bundle.name} exceeded its {timeout:.1f}s timeout"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _normalize_query(query: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", " ".join(query.lower().split()))

    @staticmethod
    def _clean_summaries(values: list[str]) -> list[str]:
        return [" ".join(value.split())[:500] for value in values if value.strip()][:8]

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        message = str(exc)
        message = re.sub(
            r"(?i)(api[_-]?key|token|authorization)=?[: ]+[^\s&]+",
            r"\1=[REDACTED]",
            message,
        )
        return f"{type(exc).__name__}: {message}"[:1000]

    def _ensure_disclosures(self, report: str, state: RuntimeState) -> str:
        body = report.strip()
        if state.conflicts and "detected evidence conflicts" not in body.lower():
            body += "\n\n## Detected Evidence Conflicts\n\n"
            body += "\n".join(
                f"- {conflict.summary} "
                + "".join(f"[{eid}]" for eid in conflict.evidence_ids)
                for conflict in state.conflicts
            )
        if state.unresolved_gaps and not any(
            heading in body.lower() for heading in ("limitations", "evidence gaps")
        ):
            body += "\n\n## Evidence Gaps\n\n"
            body += "\n".join(f"- {gap}" for gap in state.unresolved_gaps)
        return body

    @staticmethod
    def _insufficient_report(state: RuntimeState) -> str:
        gaps = state.unresolved_gaps or ["No usable evidence was retrieved."]
        return (
            "## Insufficient Evidence\n\n"
            "- The system cannot provide a supported answer from the collected evidence.\n"
            f"- Stop reason: `{state.stop_reason}`.\n\n"
            "## Evidence Gaps\n\n"
            + "\n".join(f"- {gap}" for gap in gaps)
            + "\n- An accessible authoritative source or successful search is required."
        )

    @staticmethod
    def _extractive_fallback(state: RuntimeState, selected_ids: tuple[str, ...], exc: Exception) -> str:
        lines = ["## Evidence Summary", ""]
        for evidence_id in selected_ids:
            item = state.ledger.get(evidence_id)
            if item:
                sentence = re.split(r"(?<=[.!?])\s+", item.content.strip())[0]
                lines.append(f"- {sentence} [{evidence_id}]")
        lines.extend((
            "",
            "## Limitations and Evidence Gaps",
            "",
            "- The report model failed, so this is a deterministic extractive fallback.",
            f"- Failure type: `{type(exc).__name__}`.",
        ))
        return "\n".join(lines)

    @staticmethod
    def _repair_error_issue(message: str):
        from evidence.citations import CitationIssue

        return CitationIssue(code="repair_failed", message=f"Citation repair failed: {message}")

    def _trace_stop(self, state: RuntimeState, iteration: int, summary: str) -> None:
        self._append_trace(
            state,
            iteration=iteration,
            action_summary=summary,
            unresolved_gaps=state.unresolved_gaps,
            stop_decision=state.stop_reason,
        )

    @staticmethod
    def _append_trace(state: RuntimeState, **values: Any) -> None:
        event = {
            "iteration": values.get("iteration", state.iterations),
            "tool_selected": values.get("tool_selected"),
            "search_query": values.get("search_query"),
            "action_summary": values.get("action_summary", ""),
            "tool_result_count": values.get("tool_result_count", 0),
            "new_evidence_ids": values.get("new_evidence_ids", []),
            "duplicate_results_skipped": values.get("duplicate_results_skipped", 0),
            "unresolved_gaps": values.get("unresolved_gaps", []),
            "conflicts_detected": values.get("conflicts_detected", []),
            "stop_decision": values.get("stop_decision"),
            "duration_seconds": values.get("duration_seconds", 0.0),
            "errors": values.get("errors", []),
            "retries": values.get("retries", 0),
        }
        state.trace.append(event)
