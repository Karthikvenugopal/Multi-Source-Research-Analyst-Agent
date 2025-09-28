from langchain.prompts import ChatPromptTemplate
from config import Config
from tools import ResearchTools
from state import ResearchFinding
from llm_manager import LLMManager
import re
from datetime import datetime
from typing import List, Dict, Any

class AgentNodes:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.llm = self.llm_manager.llm
        self.tools = ResearchTools()
        
        # Define enhanced prompts
        self.supervisor_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent research supervisor. Analyze the current research state and decide the next action.

Research Question: {question}
Current Focus: {current_focus}
Research Quality Score: {quality_score}/1.0
Sources Used: {sources_used}
Iterations: {iterations}/{max_iterations}
Findings Count: {findings_count}

Available Actions:
1. web_search - For current news, recent developments, real-time data
2. wikipedia_search - For established facts, historical context, general knowledge
3. arxiv_search - For academic papers, scientific research, technical details
4. synthesize - If you have sufficient diverse information to analyze
5. finish - If the research is complete and comprehensive

Decision Criteria:
- If quality_score < 0.6 and iterations < 3: Continue researching
- If missing key sources (web/wikipedia/arxiv): Use missing source
- If findings are conflicting: Get more sources for synthesis
- If comprehensive coverage achieved: Synthesize
- If synthesis complete: Finish

Return ONLY the action name (web_search, wikipedia_search, arxiv_search, synthesize, finish)."""),
            ("human", "What should we do next?")
        ])
        
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
        """Enhanced supervisor with quality-based decisions"""
        # Check if we've exceeded max iterations
        if state['iterations'] >= Config.MAX_ITERATIONS:
            return {
                "next_node": "synthesize", 
                "max_iterations_reached": True,
                "iterations": 1
            }
        
        # Calculate research quality score
        quality_score = self.tools.calculate_research_quality(state['research_findings'])
        
        # Determine sources used
        sources_used = list(set(f['source'] for f in state['research_findings']))
        
        # Prepare findings summary
        findings_summary = self._format_findings_summary(state['research_findings'])
        
        # Prepare the enhanced prompt
        prompt = self.supervisor_prompt.format(
            question=state['question'],
            current_focus=state.get('current_focus', 'General research'),
            quality_score=round(quality_score, 2),
            sources_used=', '.join(sources_used) if sources_used else 'None',
            iterations=state['iterations'],
            max_iterations=Config.MAX_ITERATIONS,
            findings_count=len(state['research_findings']),
            findings=findings_summary
        )
        
        # Get the decision from LLM
        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                decision = response.content.strip().lower()
            elif isinstance(response, str):
                decision = response.strip().lower()
            else:
                decision = str(response).strip().lower()
        except Exception as e:
            print(f"❌ Error getting supervisor decision: {e}")
            # Fallback decision
            decision = "web_search"
        
        # Enhanced decision parsing with fallback logic
        if 'web_search' in decision or 'web' in decision:
            next_node = "web_search"
        elif 'wikipedia' in decision:
            next_node = "wikipedia_search"
        elif 'arxiv' in decision:
            next_node = "arxiv_search"
        elif 'synthesize' in decision:
            next_node = "synthesize"
        elif 'finish' in decision:
            next_node = "finish"
        else:
            # Intelligent fallback based on current state
            if quality_score < 0.6 and 'web' not in sources_used:
                next_node = "web_search"
            elif 'wikipedia' not in sources_used:
                next_node = "wikipedia_search"
            elif 'arxiv' not in sources_used:
                next_node = "arxiv_search"
            else:
                next_node = "synthesize"
        
        return {
            "next_node": next_node, 
            "iterations": 1,
            "research_quality_score": quality_score
        }
    
    def web_search_node(self, state):
        """Perform web search and add to findings"""
        results = self.tools.web_search(state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings, 
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings))
        }
    
    def wikipedia_search_node(self, state):
        """Perform Wikipedia search and add to findings"""
        results = self.tools.wikipedia_search(state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings, 
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings))
        }
    
    def arxiv_search_node(self, state):
        """Perform ArXiv search and add to findings"""
        results = self.tools.arxiv_search(state['question'])
        new_findings = state['research_findings'] + results
        return {
            "research_findings": new_findings, 
            "next_node": "supervisor",
            "sources_used": list(set(f['source'] for f in new_findings))
        }
    
    def synthesize_node(self, state):
        """Enhanced synthesis with conflict analysis"""
        findings_summary = self._format_findings_summary(state['research_findings'])
        
        prompt = self.synthesis_prompt.format(
            question=state['question'],
            findings=findings_summary
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
        
        # Calculate confidence in synthesis
        confidence = self._calculate_synthesis_confidence(state['research_findings'])
        
        return {
            "analysis": analysis, 
            "next_node": "report",
            "research_quality_score": confidence
        }
    
    def report_node(self, state):
        """Generate the final report with enhanced formatting"""
        # Format sources for citation
        sources = self._format_sources_for_citation(state['research_findings'])
        
        prompt = self.report_prompt.format(
            question=state['question'],
            analysis=state['analysis'],
            sources=sources
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
        """Format findings for display in prompts"""
        if not findings:
            return "No findings yet"
        
        summary = []
        for i, finding in enumerate(findings, 1):
            source_info = f"[{finding['source'].upper()}] {finding.get('title', 'Untitled')}"
            confidence = finding.get('confidence', 0)
            summary.append(f"{i}. {source_info} (Confidence: {confidence:.2f})\n   {finding['content'][:200]}...")
        
        return "\n\n".join(summary)
    
    def _calculate_synthesis_confidence(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence in the synthesis based on source quality"""
        if not findings:
            return 0.0
        
        # Average confidence of all findings
        avg_confidence = sum(f.get('confidence', 0) for f in findings) / len(findings)
        
        # Bonus for source diversity
        sources = set(f['source'] for f in findings)
        diversity_bonus = min(0.2, len(sources) * 0.05)
        
        return min(1.0, avg_confidence + diversity_bonus)
    
    def _format_sources_for_citation(self, findings: List[Dict[str, Any]]) -> str:
        """Format sources for citation in the report"""
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