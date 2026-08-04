"""Gradio application for the agentic research runtime and legacy comparison."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

import gradio as gr

from graph import ResearchGraph


class ResearchApp:
    """Lazy mode-aware UI adapter around :class:`ResearchGraph`."""

    _STAGE_MESSAGES = {
        "agentic_research": "Inspecting evidence, iterating when justified, and verifying citations…",
        "planner": "Planning the legacy single-pass search…",
        "gather": "Gathering legacy source results…",
        "synthesize": "Synthesizing the legacy findings…",
        "report": "Writing the legacy report…",
    }

    def __init__(self, graph_factory: Callable[..., Any] = ResearchGraph) -> None:
        self.graph_factory = graph_factory
        self._graphs: dict[str, Any] = {}

    def _graph(self, mode: str):
        if mode not in self._graphs:
            self._graphs[mode] = self.graph_factory(mode=mode)
        return self._graphs[mode]

    @staticmethod
    def _waiting(message: str) -> str:
        return f"### ⏳ Researching…\n\n{message}\n\n_Please keep this tab open._"

    def research_query(self, question: str, mode: str = "agentic"):
        """Stream a status card followed by formatted report and trace outputs."""
        if not question or not question.strip():
            yield "⚠️ Please enter a research question.", "No trace available."
            return
        yield self._waiting("Starting the bounded research workflow…"), "Trace will appear here."
        try:
            final_state = None
            for node_name, state in self._graph(mode).stream(question.strip()):
                final_state = state
                message = self._STAGE_MESSAGES.get(node_name)
                if message:
                    yield self._waiting(message), "Trace will appear when research finishes."
            if not final_state:
                yield "❌ The research workflow returned no result.", "No trace available."
                return
            yield self.format_result(question, final_state), self.format_trace(final_state)
        except Exception as exc:
            yield f"❌ **Error processing the request:** {exc}", "The run failed before a trace was available."

    @staticmethod
    def format_result(question: str, result: dict[str, Any]) -> str:
        """Format final report, safeguards, sources, and compact run metrics."""
        mode = result.get("mode", "legacy")
        verification = result.get("verification_result", {})
        verified = verification.get("is_valid")
        verification_label = (
            "✅ Passed"
            if verified is True
            else "⚠️ Failed after repair"
            if verified is False
            else "Not available in legacy mode"
        )
        stop_reason = result.get("stop_reason", "legacy_completed")
        warning = ""
        if mode == "agentic" and stop_reason != "evidence_sufficient":
            warning += (
                f"> ⚠️ Research stopped with `{stop_reason}`; review the evidence gaps below.\n\n"
            )
        if verified is False:
            warning += "> ⚠️ Citation verification did not pass after the bounded repair.\n\n"

        evidence = result.get("evidence_ledger") or result.get("research_findings", [])
        source_lines = []
        for index, item in enumerate(evidence, 1):
            evidence_id = item.get("evidence_id", f"legacy-{index}")
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            source = item.get("source_type") or item.get("source", "unknown")
            label = f"[{title}]({url})" if url else title
            source_lines.append(f"- **{evidence_id}** — {label} ({source})")
        sources = "\n".join(source_lines) or "- No usable sources were collected."

        conflicts = result.get("conflicts", [])
        conflict_summary = (
            "\n".join(f"- {item.get('summary', item)}" for item in conflicts)
            if conflicts
            else "- No likely conflicts were detected by the pragmatic detector."
        )
        report = result.get("report") or "*No report generated.*"
        return f"""# Multi-Source Research Report

{warning}## Run summary

- **Mode:** {mode}
- **Iterations:** {result.get('iterations', 'n/a')}
- **Tool calls:** {result.get('tool_calls', 'n/a')}
- **Stop reason:** `{stop_reason}`
- **Citation verification:** {verification_label}
- **Evidence items:** {len(evidence)}
- **Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Research question

{question}

---

{report}

---

## Collected sources

{sources}

## Detected evidence conflicts

{conflict_summary}
"""

    @staticmethod
    def format_trace(result: dict[str, Any]) -> str:
        """Render concise operational events without private model reasoning."""
        events = result.get("trace", [])
        if not events:
            return "Legacy mode does not expose an iterative trace."
        lines = []
        for event in events:
            lines.append(f"### Iteration {event.get('iteration')}")
            lines.append(f"- **Action:** {event.get('action_summary') or 'Inspect evidence'}")
            if event.get("tool_selected"):
                lines.append(f"- **Tool:** {event['tool_selected']}")
                lines.append(f"- **Query:** `{event.get('search_query', '')}`")
                lines.append(f"- **Results / new evidence:** {event.get('tool_result_count', 0)} / {event.get('new_evidence_ids', [])}")
                lines.append(f"- **Duplicates skipped:** {event.get('duplicate_results_skipped', 0)}")
            if event.get("conflicts_detected"):
                lines.append(f"- **Conflicts:** {event['conflicts_detected']}")
            if event.get("unresolved_gaps"):
                lines.append(f"- **Open gaps:** {event['unresolved_gaps']}")
            if event.get("errors"):
                lines.append(f"- **Errors:** {event['errors']}")
            if event.get("stop_decision"):
                lines.append(f"- **Stop:** `{event['stop_decision']}`")
            lines.append("")
        coverage = result.get("evidence_coverage", {})
        lines.extend((
            "### Evidence coverage",
            "",
            f"```json\n{json.dumps(coverage, indent=2)}\n```",
        ))
        return "\n".join(lines)


app = ResearchApp()

EXAMPLE_QUESTIONS = [
    "What is retrieval-augmented generation and why is it used?",
    "How do solar and wind energy compare in cost and reliability?",
    "What are the latest advances in quantum error correction research?",
]
_IDLE_REPORT = "_Enter a research question and click **Research**._"
CUSTOM_CSS = """
.gradio-container { max-width: 980px !important; margin: 0 auto !important; }
footer { display: none !important; }
"""

with gr.Blocks(theme=gr.themes.Soft(), title="Multi-Source Research Analyst", css=CUSTOM_CSS) as iface:
    gr.Markdown("""
    # Multi-Source Research Analyst

    Bounded iterative research with an evidence ledger, explicit gaps/conflicts,
    and deterministic citation verification. Agentic mode is the default; legacy
    mode preserves the original single-pass pipeline for comparison.
    """)
    question = gr.Textbox(
        label="Research question",
        lines=3,
        placeholder="Ask a factual, comparative, technical, or multi-hop question…",
    )
    mode = gr.Radio(
        choices=[("Agentic (default)", "agentic"), ("Legacy / v1", "legacy")],
        value="agentic",
        label="Research mode",
    )
    with gr.Row():
        submit_btn = gr.Button("Research", variant="primary")
        clear_btn = gr.Button("Clear")
    gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question, label="Examples")
    report = gr.Markdown(value=_IDLE_REPORT, label="Research report")
    with gr.Accordion("Research trace and evidence coverage", open=False):
        trace = gr.Markdown(value="Trace will appear here.")

    submit_btn.click(
        fn=app.research_query,
        inputs=[question, mode],
        outputs=[report, trace],
        show_progress="hidden",
    )
    question.submit(
        fn=app.research_query,
        inputs=[question, mode],
        outputs=[report, trace],
        show_progress="hidden",
    )
    clear_btn.click(
        lambda: ("", _IDLE_REPORT, "Trace will appear here."),
        outputs=[question, report, trace],
    )


if __name__ == "__main__":
    import os

    port_env = os.environ.get("GRADIO_SERVER_PORT")
    iface.launch(
        server_name="0.0.0.0",
        server_port=int(port_env) if port_env else None,
        share=False,
        show_error=True,
    )
