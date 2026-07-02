import gradio as gr
from graph import ResearchGraph
from evaluation import ResearchEvaluator, check_research_quality, validate_research_output
import time
import json
from datetime import datetime

class ResearchApp:
    def __init__(self):
        self.research_graph = ResearchGraph()
        self.evaluator = ResearchEvaluator()
    
    # Friendly status shown in the output pane while each stage runs.
    _STAGE_MESSAGES = {
        "planner": "🧭 Planning which sources to consult…",
        "gather": "🔎 Gathering evidence from the web, Wikipedia, and ArXiv…",
        "synthesize": "🧠 Synthesizing findings and reconciling conflicts…",
        "report": "📝 Writing the cited report…",
    }

    @staticmethod
    def _waiting(message):
        """A visible 'in progress' card so the user knows work is happening."""
        return (
            "### ⏳ Researching…\n\n"
            f"{message}\n\n"
            "_This usually takes about a minute — it queries several live "
            "sources and an LLM. Please keep this tab open._"
        )

    def research_query(self, question):
        """Stream staged progress, then the final report, for a research question."""
        if not question or not question.strip():
            yield "⚠️ Please enter a research question to get started."
            return

        start_time = time.time()
        # Immediate feedback the moment Submit is clicked, before any slow work.
        yield self._waiting("Starting up…")

        try:
            # Stream the pipeline so each completed stage updates the UI.
            final_state = None
            for node_name, state in self.research_graph.stream(question):
                final_state = state
                message = self._STAGE_MESSAGES.get(node_name)
                if message:
                    yield self._waiting(message)

            if not final_state:
                yield "❌ **Error:** the research pipeline returned no result."
                return

            duration = round(time.time() - start_time, 2)
            result = dict(final_state)
            result['duration'] = duration

            # Quality checks and evaluation
            quality_passed, quality_issues = check_research_quality(result)
            validate_research_output(result)
            evaluation = self.evaluator.evaluate_research_session(result, question)

            # Metrics
            quality_score = result.get('research_quality_score', 0.0)
            sources_used = result.get('sources_used', [])
            num_findings = len(result.get('research_findings', []))

            yield self._format_enhanced_report(
                question, result, duration, quality_score, sources_used,
                num_findings, evaluation, quality_passed, quality_issues,
            )

        except Exception as e:
            yield f"❌ **Error processing your request:** {str(e)}"
    
    def _format_enhanced_report(self, question, result, duration, quality_score, sources_used, num_findings, evaluation, quality_passed, quality_issues):
        """Format the research report with enhanced styling"""
        
        # Quality status indicator
        quality_status = "✅ PASSED" if quality_passed else "⚠️ ISSUES DETECTED"
        quality_color = "🟢" if quality_passed else "🟡"
        
        # Header with metrics
        response = f"""# 🔍 Multi-Source Research Report

## 📊 Research Metrics
- **⏱️ Duration:** {duration} seconds
- **📑 Findings gathered:** {num_findings}
- **📈 Quality Score:** {quality_score:.2f}/1.0
- **📚 Sources Used:** {', '.join(sources_used) if sources_used else 'None'}
- **🎯 Overall Score:** {evaluation['overall_score']:.2f}/1.0
- **{quality_color} Quality Check:** {quality_status}
- **🕐 Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Add quality issues if any
        if not quality_passed and quality_issues:
            response += "## ⚠️ Quality Issues Detected\n"
            for issue in quality_issues:
                response += f"- {issue}\n"
            response += "\n"
        
        response += "---\n\n"
        response += f"## ❓ Research Question\n**{question}**\n\n---\n\n## 📋 Executive Summary\n"
        
        # Add the main report
        if result.get('report'):
            response += f"\n{result['report']}\n\n"
        else:
            response += "*No report generated.*\n\n"
        
        # Add research process details
        response += "---\n\n## 🔬 Research Process Details\n\n"
        
        # Research findings with enhanced formatting
        if result.get('research_findings'):
            response += "### 📖 Research Findings\n\n"
            for i, finding in enumerate(result['research_findings'], 1):
                source = finding.get('source', 'unknown').upper()
                title = finding.get('title', 'Untitled')
                confidence = finding.get('confidence', 0.0)
                url = finding.get('url', '')
                
                # Source emoji mapping
                source_emoji = {
                    'WEB': '🌐',
                    'WIKIPEDIA': '📚',
                    'ARXIV': '🔬'
                }.get(source, '📄')
                
                response += f"**{i}. {source_emoji} {source}:** {title}\n"
                response += f"   - **Confidence:** {confidence:.2f}/1.0\n"
                if url:
                    response += f"   - **URL:** [{url}]({url})\n"
                response += f"   - **Content:** {finding.get('content', '')[:300]}...\n\n"
        else:
            response += "### 📖 Research Findings\n*No findings collected.*\n\n"
        
        # Analysis section
        if result.get('analysis'):
            response += "### 🧠 Analysis\n\n"
            response += f"{result['analysis']}\n\n"
        
        # Footer
        response += "---\n\n*Generated by Multi-Source Research Analyst Agent*"
        
        return response

# Create the enhanced interface
app = ResearchApp()

# A single full-width vertical layout (gr.Blocks) — the old gr.Interface put the
# report in a narrow right-hand column, which looked off-center.
EXAMPLE_QUESTIONS = [
    "What is retrieval-augmented generation and why is it used?",
    "How do solar and wind energy compare in cost and reliability?",
    "What are the latest developments in quantum error correction?",
]

_IDLE_REPORT = "_Your research report will appear here. Enter a question above and click **Research**._"

# Keep the app a centered, readable column instead of stretching full-browser-width,
# and hide the default Gradio footer for a cleaner portfolio look.
CUSTOM_CSS = """
.gradio-container { max-width: 860px !important; margin: 0 auto !important; }
footer { display: none !important; }
"""

with gr.Blocks(
    theme=gr.themes.Soft(),
    title="Multi-Source Research Analyst Agent",
    css=CUSTOM_CSS,
) as iface:
    gr.Markdown(
        """
        # 🤖 Multi-Source Research Analyst Agent

        An AI agent that autonomously researches a question across multiple sources
        (web, Wikipedia, academic papers) and synthesizes a **cited** report.

        **How it works:** it plans which sources to consult, gathers from them in
        parallel, then synthesizes the findings into a report with confidence scores.

        ⏱️ **Each question takes about a minute** — it makes live source and LLM
        calls, and you'll see live progress below while it runs.
        """
    )

    question = gr.Textbox(
        label="🔍 Research Question",
        lines=3,
        placeholder="Enter your research question here…",
        info="Ask any research question and the agent will gather information from multiple sources.",
    )

    with gr.Row():
        submit_btn = gr.Button("🔎 Research", variant="primary")
        clear_btn = gr.Button("Clear")

    gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question, label="Example questions")

    report = gr.Markdown(value=_IDLE_REPORT, label="📊 Research Report", elem_id="report")

    # show_progress="hidden": suppress Gradio's pulsing overlay bar, which faded in
    # and out on top of the report and covered our own "Researching…" status. The
    # generator streams visible status text instead, so no overlay is needed.
    submit_btn.click(fn=app.research_query, inputs=question, outputs=report, show_progress="hidden")
    question.submit(fn=app.research_query, inputs=question, outputs=report, show_progress="hidden")
    clear_btn.click(lambda: ("", _IDLE_REPORT), outputs=[question, report])

if __name__ == "__main__":
    import os

    # Honor GRADIO_SERVER_PORT if set; otherwise let Gradio find a free port
    # starting at 7860, so a stale instance doesn't crash startup with an
    # unhelpful "Cannot find empty port" traceback.
    port_env = os.environ.get("GRADIO_SERVER_PORT")
    iface.launch(
        server_name="0.0.0.0",
        server_port=int(port_env) if port_env else None,
        share=False,
        show_error=True,
    )