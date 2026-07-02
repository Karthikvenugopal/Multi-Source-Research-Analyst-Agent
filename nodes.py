import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Literal

from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import Config
from tools import ResearchTools
from llm_manager import LLMManager


class PlannedSearch(BaseModel):
    """A single source + the query to run against it."""

    source: Literal["web", "wikipedia", "arxiv"]
    query: str = Field(
        description="Concise keyword/entity query for this source -- NOT the full "
                    "natural-language question."
    )


class ResearchPlan(BaseModel):
    """The planner's decision: which sources to search and with what queries."""

    searches: List[PlannedSearch] = Field(
        description="One to three source+query searches to run for this question."
    )
    reasoning: str = Field(default="", description="One sentence on the choice of sources.")


PLANNER_SYSTEM = """You are a research planner. Given a question, design a focused
multi-source research plan: choose the sources that will best answer it and, for
each, write a SHORT keyword query (key entities/terms, never the full sentence).

Sources:
- web        current events, recent developments, real-time data
- wikipedia  established facts, definitions, background
- arxiv      academic papers, technical / scientific detail

Pick one to three sources. Prefer breadth across different source types for
well-rounded research, and tune each query to its source (for example
"self-attention transformer architecture" rather than "how does self-attention
work?")."""


class AgentNodes:
    """Plan-execute research agent.

    planner (1 LLM call -> sources + queries)
      -> gather (parallel retrieval, no LLM calls)
      -> synthesize (1 LLM call)
      -> report (1 LLM call)
    """

    def __init__(self):
        self.llm_manager = LLMManager()
        self.llm = self.llm_manager.llm
        self.tools = ResearchTools()

        # Planner returns a structured ResearchPlan in one call. Falls back to a
        # default "all sources" plan if the provider lacks structured output.
        try:
            self.planner = self.llm.with_structured_output(ResearchPlan)
        except Exception:
            self.planner = None

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

Numbered sources (cite these by their number):
{sources}

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

CITATIONS (important):
- Support every substantive claim with an inline citation in square brackets that
  refers to the numbered sources above, e.g. "RAG reduces hallucination [1][3]."
- Only cite source numbers that appear in the list; never invent sources or URLs.
- Do NOT write your own Sources or References section — a canonical, clickable
  reference list is appended automatically.

Maintain a professional, objective tone throughout. Use clear headings and logical flow."""),
            ("human", "Please create the final research report.")
        ])

    # --- planning -----------------------------------------------------------

    def planner_node(self, state):
        """Decide which sources to search and with what query (one LLM call)."""
        plan = self._make_plan(state['question'])
        return {"research_plan": plan, "next_node": "gather"}

    def _make_plan(self, question: str) -> List[Dict[str, str]]:
        if self.planner is not None:
            try:
                result = self.planner.invoke(
                    [("system", PLANNER_SYSTEM),
                     ("human", f"Question: {question}\n\nProduce the research plan.")]
                )
                plan = [
                    {"source": s.source, "query": (s.query or question).strip() or question}
                    for s in result.searches
                    if s.source in ("web", "wikipedia", "arxiv")
                ]
                if plan:
                    return plan
            except Exception as e:
                print(f"⚠️ Planner failed, using default plan: {e}")

        # Default plan: query every source with the full question.
        return [{"source": s, "query": question} for s in ("web", "wikipedia", "arxiv")]

    # --- retrieval ----------------------------------------------------------

    def gather_node(self, state):
        """Run every planned search concurrently and collect the findings."""
        plan = state.get('research_plan') or [
            {"source": s, "query": state['question']} for s in ("web", "wikipedia", "arxiv")
        ]
        tool_for = {
            "web": self.tools.web_search,
            "wikipedia": self.tools.wikipedia_search,
            "arxiv": self.tools.arxiv_search,
        }

        def run_one(item):
            fn = tool_for.get(item["source"])
            if fn is None:
                return []
            try:
                return fn(item.get("query") or state['question'])
            except Exception as e:
                print(f"⚠️ {item['source']} search failed: {e}")
                return []

        findings: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, len(plan))) as pool:
            for results in pool.map(run_one, plan):
                findings.extend(results)

        return {
            "research_findings": findings,
            "sources_used": sorted({f["source"] for f in findings}),
            "research_quality_score": self.tools.calculate_research_quality(findings),
            "next_node": "synthesize",
        }

    # --- synthesis & reporting ---------------------------------------------

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

        return {
            "analysis": analysis,
            "next_node": "report",
            "research_quality_score": self._calculate_synthesis_confidence(state['research_findings']),
        }

    def report_node(self, state):
        """Generate the final cited report."""
        findings = state['research_findings']
        sources = self._format_sources_for_citation(findings)

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

        # Turn the writer's inline [n] markers into links that jump to the
        # matching reference, then append the canonical reference list (with the
        # anchor targets) built from the real findings.
        report = self._link_citations(report, findings)
        references = self._format_references(findings)
        if references:
            report = f"{report.rstrip()}\n\n{references}"
        return {"report": report, "next_node": "finish"}

    # --- helpers ------------------------------------------------------------

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

    def _link_citations(self, report: str, findings: List[Dict[str, Any]]) -> str:
        """Turn inline [n] markers into links that jump to reference n.

        Only numbers within the reference range are linked, so stray brackets in
        the prose (e.g. a year like [2023]) are left untouched.
        """
        valid = set(range(1, len(findings) + 1))

        def repl(match):
            n = int(match.group(1))
            return f"[[{n}]](#ref-{n})" if n in valid else match.group(0)

        return re.sub(r"\[(\d+)\]", repl, report)

    def _format_references(self, findings: List[Dict[str, Any]]) -> str:
        """Canonical, numbered reference list appended to every report.

        Each entry carries an ``<a id="ref-n">`` anchor so the inline [n]
        citations in the body link straight down to it. Titles link to the URL.
        """
        if not findings:
            return ""

        lines = ["## References", ""]
        for i, finding in enumerate(findings, 1):
            title = finding.get('title', 'Untitled')
            source = finding.get('source', 'unknown').upper()
            url = finding.get('url', '')
            label = f"[{title}]({url})" if url else title
            # Anchor target + visible number, its own paragraph so the jump lands cleanly.
            lines.append(f'<a id="ref-{i}"></a>**[{i}]** {label} — {source}')
            lines.append("")
        return "\n".join(lines).rstrip()
