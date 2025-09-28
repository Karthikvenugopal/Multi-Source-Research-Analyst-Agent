from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.utilities import ArxivAPIWrapper
import arxiv
import requests
from datetime import datetime
from typing import List, Dict, Any
import json

class ResearchTools:
    def __init__(self):
        self.tavily_tool = TavilySearchResults(max_results=5)
        self.wikipedia_api = WikipediaAPIWrapper(top_k_results=3)
        self.arxiv_api = ArxivAPIWrapper(top_k_results=3)
    
    def web_search(self, query: str) -> List[Dict[str, Any]]:
        """Search the web for current information with enhanced formatting"""
        try:
            results = self.tavily_tool.invoke(query)
            formatted_results = []
            
            if isinstance(results, list):
                for result in results:
                    formatted_results.append({
                        'source': 'web',
                        'content': result.get('content', ''),
                        'url': result.get('url', ''),
                        'title': result.get('title', ''),
                        'confidence': 0.8,  # High confidence for web results
                        'timestamp': datetime.now().isoformat()
                    })
            else:
                # Fallback for different result formats
                formatted_results.append({
                    'source': 'web',
                    'content': str(results),
                    'url': '',
                    'title': 'Web Search Results',
                    'confidence': 0.7,
                    'timestamp': datetime.now().isoformat()
                })
            
            return formatted_results
        except Exception as e:
            return [{
                'source': 'web',
                'content': f"Error in web search: {str(e)}",
                'url': '',
                'title': 'Search Error',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }]
    
    def wikipedia_search(self, query: str) -> List[Dict[str, Any]]:
        """Search Wikipedia for established facts with enhanced formatting"""
        try:
            results = self.wikipedia_api.run(query)
            formatted_results = []
            
            # Wikipedia results are typically a string, so we'll parse it
            if results:
                formatted_results.append({
                    'source': 'wikipedia',
                    'content': results,
                    'url': f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                    'title': f"Wikipedia: {query}",
                    'confidence': 0.9,  # High confidence for Wikipedia
                    'timestamp': datetime.now().isoformat()
                })
            else:
                formatted_results.append({
                    'source': 'wikipedia',
                    'content': f"No Wikipedia results found for: {query}",
                    'url': '',
                    'title': 'No Results',
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat()
                })
            
            return formatted_results
        except Exception as e:
            return [{
                'source': 'wikipedia',
                'content': f"Error in Wikipedia search: {str(e)}",
                'url': '',
                'title': 'Search Error',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }]
    
    def arxiv_search(self, query: str) -> List[Dict[str, Any]]:
        """Search ArXiv for academic papers with enhanced formatting"""
        try:
            results = self.arxiv_api.run(query)
            formatted_results = []
            
            if results:
                formatted_results.append({
                    'source': 'arxiv',
                    'content': results,
                    'url': f"https://arxiv.org/search/?query={query.replace(' ', '+')}",
                    'title': f"ArXiv: {query}",
                    'confidence': 0.85,  # High confidence for academic sources
                    'timestamp': datetime.now().isoformat()
                })
            else:
                formatted_results.append({
                    'source': 'arxiv',
                    'content': f"No ArXiv results found for: {query}",
                    'url': '',
                    'title': 'No Results',
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat()
                })
            
            return formatted_results
        except Exception as e:
            return [{
                'source': 'arxiv',
                'content': f"Error in ArXiv search: {str(e)}",
                'url': '',
                'title': 'Search Error',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }]
    
    def calculate_research_quality(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate overall research quality score"""
        if not findings:
            return 0.0
        
        # Calculate average confidence
        avg_confidence = sum(f['confidence'] for f in findings) / len(findings)
        
        # Bonus for diversity of sources
        sources = set(f['source'] for f in findings)
        diversity_bonus = min(0.2, len(sources) * 0.05)
        
        # Penalty for low-quality findings
        quality_penalty = sum(0.1 for f in findings if f['confidence'] < 0.3)
        
        return min(1.0, max(0.0, avg_confidence + diversity_bonus - quality_penalty))