from datetime import datetime

from langgraph.graph import StateGraph, END

from state import AgentState
from nodes import AgentNodes


class ResearchGraph:
    """Linear plan-execute pipeline: plan -> gather -> synthesize -> report."""

    def __init__(self):
        self.nodes = AgentNodes()
        self.graph = StateGraph(AgentState)

        self.graph.add_node("planner", self.nodes.planner_node)
        self.graph.add_node("gather", self.nodes.gather_node)
        self.graph.add_node("synthesize", self.nodes.synthesize_node)
        self.graph.add_node("report", self.nodes.report_node)

        self.graph.set_entry_point("planner")
        self.graph.add_edge("planner", "gather")
        self.graph.add_edge("gather", "synthesize")
        self.graph.add_edge("synthesize", "report")
        self.graph.add_edge("report", END)

        self.compiled_graph = self.graph.compile()

    def _initial_state(self, question: str) -> dict:
        return {
            "question": question,
            "research_findings": [],
            "research_plan": [],
            "analysis": "",
            "report": "",
            "next_node": "planner",
            "research_quality_score": 0.0,
            "sources_used": [],
            "start_time": datetime.now().isoformat(),
            "current_focus": "Initial research",
        }

    def run(self, question: str):
        """Run the pipeline for a single question."""
        return self.compiled_graph.invoke(self._initial_state(question))

    def stream(self, question: str):
        """Run the pipeline, yielding (node_name, full_state) after each node.

        Executes exactly the same nodes as run() with the same LLM-call count;
        it just surfaces the intermediate state so a UI can show live progress.
        """
        state = self._initial_state(question)
        for update in self.compiled_graph.stream(state, stream_mode="updates"):
            for node_name, delta in update.items():
                if isinstance(delta, dict):
                    state = {**state, **delta}
                yield node_name, state
