from langchain.prompts import ChatPromptTemplate
from config import Config
from tools import ResearchTools
from state import ResearchFinding
from llm_manager import LLMManager
from typing import List, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field


class SupervisorDecision(BaseModel):
    """Structured decision the supervisor returns on each loop."""

    action: Literal[
        "web_search", "wikipedia_search", "arxiv_search", "synthesize", "finish"
    ] = Field(description="The next action to take.")
    search_query: str = Field(
        default="",
        description=(
            "If action is one of the *_search actions, a concise keyword/entity "
            "query optimised for that source -- NOT the full natural-language "
            "question. Leave empty for synthesize/finish."
        ),
    )
    reasoning: str = Field(
        default="", description="One short sentence justifying the choice."
    )


SUPERVISOR_SYSTEM = """You are an intelligent research supervisor. Given the current
state of a research task, choose the single best next action.

Available actions:
- web_search       current news, recent developments, real-time data
- wikipedia_search established facts, definitions, historical context
- arxiv_search     academic papers, technical / scientific detail
- synthesize       enough diverse evidence has been gathered to analyse it
- finish           the research is already complete and comprehensive

Guidance:
- Prefer sources that have not been used yet to maximise source diversity.
- If quality is low and few sources have been used, keep researching.
- Once web, reference, and academic angles are covered, synthesize.

When the action is a search, also produce `search_query`: a SHORT query of the key
entities/terms for that source (for example "self-attention transformer
architecture"), never the full question. Focused queries retrieve better evidence."""


class AgentNodes:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.llm = self.llm_manager.llm
        self.tools = ResearchTools()

        # Supervisor returns a structured decision (action + a source-tailored query)
        # in a single call. Falls back to a heuristic if the provider/model does not
        # support structured output.
        try:
            self.structured_supervisor = self.llm.with_structured_output(SupervisorDecision)
        except Exception:
            self.structured_supervisor = None

        # Synthesis and report prompts
        self.synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research analyst. Synthesize the following information into a comprehensive analysis.

Research Question: {question}

Research Findings:
{findings}

Your synthesis should:
1. Identify key themes and patterns across sources
2. Highlight areas of consensus and agreement
3. Note conflicting information and explain possible reasons
4. Identify gaps in knowledge or missing perspectives
5. Assess the reliability and credibility of different sources
6. Provide confidence levels for different claims
7. Suggest areas that might need additional research

Be objective, balanced, and acknowledge uncertainty where it exists. Use evidence from the findings to support your analysis."""),
            ("human", "Please provide a comprehensive synthesis of this research.")
        ])

        self.report_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional research report writer. Create a comprehensive final report.

Research Question: {question}

Analysis: {analysis}

Sources: {sources}

Create a well-structured report with:

## Executive Summary
- Brief overview of key findings and conclusions

## Introduction
- Context and importance of the research question
- Methodology overview

## Key Findings
- Main discoveries organized by theme
- Supporting evidence from sources
- Confidence levels for major claims

## Analysis
- Detailed analysis of findings
- Discussion of conflicting information
- Assessment of source reliability

## Limitations and Gaps
- Acknowledgment of research limitations
- Areas requiring further investigation

## Conclusion
- Summary of main findings
- Implications and recommendations

## Sources
- Properly formatted citations
- Source reliability assessment

Maintain a professional, objective tone throughout. Use clear headings and logical flow."""),
            ("human", "Please create the final research report.")
        ])

    def supervisor_node(self, state):
        """Decide the next action (and a tailored search query) from the current state."""
        if state['iterations'] >= Config.MAX_ITERATIONS:
            return {
                "next_node": "synthesize",
                "max_iterations_reached": True,
                "iterations": 1,
            }

        quality_score = self.tools.calculate_research_quality(state['research_findings'])
        sources_used = list(set(f['source'] for f in state['research_findings']))
        findings_summary = self._format_findings_summary(state['research_findings'])

        next_node, search_query = self._decide_next_action(
            state, quality_score, sources_used, findings_summary
        )

        return {
            "next_node": next_node,
            "search_query": search_query,
            "iterations": 1,
            "research_quality_score": quality_score,
        }

    def _decide_next_action(self, state, quality_score, sources_used, findings_summary) -> Tuple[str, str]:
        """Return ``(next_node, search_query)``.

        Uses the model's structured output when available, otherwise a deterministic
        heuristic. Never raises.
        """
        context = (
            f"Question: {state['question']}\n"
            f"Current focus: {state.get('current_focus', 'General research')}\n"
            f"Research quality score: {round(quality_score, 2)}/1.0\n"
            f"Sources used: {', '.join(sources_used) if sources_used else 'None'}\n"
            f"Iterations: {state['iterations']}/{Config.MAX_ITERATIONS}\n"
            f"Findings so far:\n{findings_summary}\n\n"
            "Choose the next action."
        )

        if self.structured_supervisor is not None:
            try:
                decision = self.structured_supervisor.invoke(
                    [("system", SUPERVISOR_SYSTEM), ("human", context)]
                )
                query = (decision.search_query or "").strip() or state['question']
                return decision.action, query
            except Exception as e:
                print(f"⚠️ Structured supervisor failed, using heuristic: {e}")

        # Deterministic fallback: gather missing sources, then synthesize.
        return self._fallback_action(quality_score, sources_used), state['question']

    @staticmethod
    def _fallback_action(quality_score, sources_used) -> str:
        if quality_score < 0.6 and 'web' not in sources_used:
            return "web_search"
        if 'wikipedia' not in sources_used:
            return "wikipedia_search"
        if 'arxiv' not in sources_used:
            return "arxiv_search"
        return "synthesize"

    def web_search_node(self, state):
        """Perform web search (with the supervisor's query) and add to findings."""
        results = self.tools.web_search(state.get('search_query') or state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings,
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings)),
        }

    def wikipedia_search_node(self, state):
        """Perform Wikipedia search (with the supervisor's query) and add to findings."""
        results = self.tools.wikipedia_search(state.get('search_query') or state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings,
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings)),
        }

    def arxiv_search_node(self, state):
        """Perform ArXiv search (with the supervisor's query) and add to findings."""
        results = self.tools.arxiv_search(state.get('search_query') or state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings,
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings)),
        }

    def synthesize_node(self, state):
        """Synthesize the findings into a single analysis."""
        findings_summary = self._format_findings_summary(state['research_findings'])

        prompt = self.synthesis_prompt.format(
            question=state['question'],
            findings=findings_summary,
        )

        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                analysis = response.content
            elif isinstance(response, str):
                analysis = response
            else:
                analysis = str(response)
        except Exception as e:
            print(f"❌ Error in synthesis: {e}")
            analysis = f"Error in synthesis: {str(e)}"

        confidence = self._calculate_synthesis_confidence(state['research_findings'])

        return {
            "analysis": analysis,
            "next_node": "report",
            "research_quality_score": confidence,
        }

    def report_node(self, state):
        """Generate the final cited report."""
        sources = self._format_sources_for_citation(state['research_findings'])

        prompt = self.report_prompt.format(
            question=state['question'],
            analysis=state['analysis'],
            sources=sources,
        )

        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                report = response.content
            elif isinstance(response, str):
                report = response
            else:
                report = str(response)
        except Exception as e:
            print(f"❌ Error in report generation: {e}")
            report = f"Error in report generation: {str(e)}"
        return {"report": report, "next_node": "finish"}

    def _format_findings_summary(self, findings: List[Dict[str, Any]]) -> str:
        """Format findings for display in prompts."""
        if not findings:
            return "No findings yet"

        summary = []
        for i, finding in enumerate(findings, 1):
            source_info = f"[{finding['source'].upper()}] {finding.get('title', 'Untitled')}"
            confidence = finding.get('confidence', 0)
            content = finding.get('content', '')
            summary.append(f"{i}. {source_info} (Confidence: {confidence:.2f})\n   {content[:200]}...")

        return "\n\n".join(summary)

    def _calculate_synthesis_confidence(self, findings: List[Dict[str, Any]]) -> float:
        """Confidence in the synthesis based on source quality and diversity."""
        if not findings:
            return 0.0

        avg_confidence = sum(f.get('confidence', 0) for f in findings) / len(findings)
        sources = set(f['source'] for f in findings)
        diversity_bonus = min(0.2, len(sources) * 0.05)

        return min(1.0, avg_confidence + diversity_bonus)

    def _format_sources_for_citation(self, findings: List[Dict[str, Any]]) -> str:
        """Format sources for citation in the report."""
        if not findings:
            return "No sources available"

        citations = []
        for i, finding in enumerate(findings, 1):
            source = finding['source']
            title = finding.get('title', 'Untitled')
            url = finding.get('url', '')

            if url:
                citations.append(f"{i}. {title} - {source.upper()} ({url})")
            else:
                citations.append(f"{i}. {title} - {source.upper()}")

        return "\n".join(citations)
