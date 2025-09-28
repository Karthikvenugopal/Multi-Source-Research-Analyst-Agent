from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import AgentNodes

class ResearchGraph:
    def __init__(self):
        self.nodes = AgentNodes()
        self.graph = StateGraph(AgentState)
        
        # Add nodes
        self.graph.add_node("supervisor", self.nodes.supervisor_node)
        self.graph.add_node("web_search", self.nodes.web_search_node)
        self.graph.add_node("wikipedia_search", self.nodes.wikipedia_search_node)
        self.graph.add_node("arxiv_search", self.nodes.arxiv_search_node)
        self.graph.add_node("synthesize", self.nodes.synthesize_node)
        self.graph.add_node("report", self.nodes.report_node)
        
        # Set entry point
        self.graph.set_entry_point("supervisor")
        
        # Add conditional edges
        self.graph.add_conditional_edges(
            "supervisor",
            self.route_next_node,
            {
                "web_search": "web_search",
                "wikipedia_search": "wikipedia_search",
                "arxiv_search": "arxiv_search",
                "synthesize": "synthesize",
                "finish": "report"
            }
        )
        
        # Add edges from research nodes back to supervisor
        self.graph.add_edge("web_search", "supervisor")
        self.graph.add_edge("wikipedia_search", "supervisor")
        self.graph.add_edge("arxiv_search", "supervisor")
        
        # Add edges from synthesize to report
        self.graph.add_edge("synthesize", "report")
        
        # Add edge from report to end
        self.graph.add_edge("report", END)
        
        # Compile the graph
        self.compiled_graph = self.graph.compile()
    
    def route_next_node(self, state):
        """Route to the next node based on the supervisor's decision"""
        return state.get("next_node", "web_search")
    
    def run(self, question: str):
        """Run the graph with a question"""
        from datetime import datetime
        
        initial_state = {
            "question": question,
            "research_findings": [],
            "analysis": "",
            "report": "",
            "iterations": 0,
            "next_node": "supervisor",
            "research_quality_score": 0.0,
            "sources_used": [],
            "max_iterations_reached": False,
            "start_time": datetime.now().isoformat(),
            "current_focus": "Initial research"
        }
        
        return self.compiled_graph.invoke(initial_state)