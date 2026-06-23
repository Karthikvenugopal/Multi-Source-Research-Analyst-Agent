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

    def run(self, question: str):
        """Run the pipeline for a single question."""
        initial_state = {
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

        return self.compiled_graph.invoke(initial_state)
