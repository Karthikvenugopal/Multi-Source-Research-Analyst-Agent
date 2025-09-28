"""
Evaluation metrics and quality checks for the Multi-Source Research Analyst Agent
"""

import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json

class ResearchEvaluator:
    """Evaluates the performance and quality of research sessions"""
    
    def __init__(self):
        self.evaluation_metrics = {}
    
    def evaluate_research_session(self, result: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Comprehensive evaluation of a research session"""
        
        evaluation = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'basic_metrics': self._calculate_basic_metrics(result),
            'quality_metrics': self._calculate_quality_metrics(result),
            'source_metrics': self._calculate_source_metrics(result),
            'efficiency_metrics': self._calculate_efficiency_metrics(result),
            'overall_score': 0.0
        }
        
        # Calculate overall score
        evaluation['overall_score'] = self._calculate_overall_score(evaluation)
        
        return evaluation
    
    def _calculate_basic_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate basic research metrics"""
        findings = result.get('research_findings', [])
        
        return {
            'total_findings': len(findings),
            'iterations': result.get('iterations', 0),
            'duration': result.get('duration', 0),
            'has_analysis': bool(result.get('analysis')),
            'has_report': bool(result.get('report')),
            'max_iterations_reached': result.get('max_iterations_reached', False)
        }
    
    def _calculate_quality_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality-related metrics"""
        findings = result.get('research_findings', [])
        
        if not findings:
            return {
                'average_confidence': 0.0,
                'high_confidence_findings': 0,
                'low_confidence_findings': 0,
                'research_quality_score': 0.0,
                'content_quality': 0.0
            }
        
        # Calculate confidence metrics
        confidences = [f.get('confidence', 0) for f in findings]
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence = sum(1 for c in confidences if c >= 0.7)
        low_confidence = sum(1 for c in confidences if c < 0.3)
        
        # Content quality assessment
        content_quality = self._assess_content_quality(findings)
        
        return {
            'average_confidence': avg_confidence,
            'high_confidence_findings': high_confidence,
            'low_confidence_findings': low_confidence,
            'research_quality_score': result.get('research_quality_score', 0.0),
            'content_quality': content_quality
        }
    
    def _calculate_source_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate source diversity and utilization metrics"""
        findings = result.get('research_findings', [])
        sources_used = result.get('sources_used', [])
        
        if not findings:
            return {
                'source_diversity': 0.0,
                'sources_used_count': 0,
                'source_distribution': {},
                'source_effectiveness': {}
            }
        
        # Source distribution
        source_counts = {}
        for finding in findings:
            source = finding.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Source effectiveness (average confidence per source)
        source_effectiveness = {}
        for source in source_counts:
            source_findings = [f for f in findings if f.get('source') == source]
            if source_findings:
                avg_confidence = sum(f.get('confidence', 0) for f in source_findings) / len(source_findings)
                source_effectiveness[source] = avg_confidence
        
        return {
            'source_diversity': len(set(f.get('source', 'unknown') for f in findings)),
            'sources_used_count': len(sources_used),
            'source_distribution': source_counts,
            'source_effectiveness': source_effectiveness
        }
    
    def _calculate_efficiency_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate efficiency and performance metrics"""
        findings = result.get('research_findings', [])
        iterations = result.get('iterations', 0)
        duration = result.get('duration', 0)
        
        return {
            'findings_per_iteration': len(findings) / max(iterations, 1),
            'time_per_finding': duration / max(len(findings), 1),
            'iterations_efficiency': 1.0 if not result.get('max_iterations_reached', False) else 0.5,
            'completion_rate': 1.0 if result.get('report') else 0.0
        }
    
    def _assess_content_quality(self, findings: List[Dict[str, Any]]) -> float:
        """Assess the quality of content in findings"""
        if not findings:
            return 0.0
        
        quality_scores = []
        for finding in findings:
            content = finding.get('content', '')
            
            # Simple heuristics for content quality
            score = 0.0
            
            # Length check (not too short, not too long)
            if 50 <= len(content) <= 1000:
                score += 0.3
            
            # Check for structured content (numbers, dates, etc.)
            if any(char.isdigit() for char in content):
                score += 0.2
            
            # Check for proper capitalization
            if content and content[0].isupper():
                score += 0.1
            
            # Check for complete sentences
            if '.' in content and len(content.split('.')) > 1:
                score += 0.2
            
            # Check for specific information (not just generic text)
            if any(word in content.lower() for word in ['research', 'study', 'data', 'analysis', 'results']):
                score += 0.2
            
            quality_scores.append(min(1.0, score))
        
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_overall_score(self, evaluation: Dict[str, Any]) -> float:
        """Calculate overall evaluation score"""
        basic = evaluation['basic_metrics']
        quality = evaluation['quality_metrics']
        source = evaluation['source_metrics']
        efficiency = evaluation['efficiency_metrics']
        
        # Weighted scoring
        scores = {
            'completion': basic['has_report'] * 0.3,  # 30% weight
            'quality': quality['research_quality_score'] * 0.25,  # 25% weight
            'diversity': min(1.0, source['source_diversity'] / 3) * 0.2,  # 20% weight
            'efficiency': efficiency['completion_rate'] * 0.15,  # 15% weight
            'content': quality['content_quality'] * 0.1  # 10% weight
        }
        
        return sum(scores.values())
    
    def generate_evaluation_report(self, evaluations: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive evaluation report"""
        if not evaluations:
            return "No evaluations available."
        
        total_sessions = len(evaluations)
        avg_overall_score = sum(e['overall_score'] for e in evaluations) / total_sessions
        successful_sessions = sum(1 for e in evaluations if e['basic_metrics']['has_report'])
        
        # Calculate aggregate metrics
        avg_quality = sum(e['quality_metrics']['research_quality_score'] for e in evaluations) / total_sessions
        avg_diversity = sum(e['source_metrics']['source_diversity'] for e in evaluations) / total_sessions
        avg_efficiency = sum(e['efficiency_metrics']['completion_rate'] for e in evaluations) / total_sessions
        
        report = f"""
# 📊 Research Agent Evaluation Report

## 📈 Overall Performance
- **Total Sessions**: {total_sessions}
- **Success Rate**: {(successful_sessions/total_sessions)*100:.1f}%
- **Average Overall Score**: {avg_overall_score:.2f}/1.0

## 🎯 Quality Metrics
- **Average Research Quality**: {avg_quality:.2f}/1.0
- **Source Diversity**: {avg_diversity:.1f} sources per session
- **Completion Rate**: {avg_efficiency:.2f}

## 📊 Detailed Breakdown
"""
        
        # Add individual session details
        for i, evaluation in enumerate(evaluations, 1):
            report += f"""
### Session {i}: {evaluation['question'][:50]}...
- **Overall Score**: {evaluation['overall_score']:.2f}/1.0
- **Quality Score**: {evaluation['quality_metrics']['research_quality_score']:.2f}
- **Sources Used**: {evaluation['source_metrics']['sources_used_count']}
- **Findings**: {evaluation['basic_metrics']['total_findings']}
- **Iterations**: {evaluation['basic_metrics']['iterations']}
"""
        
        return report
    
    def save_evaluation_results(self, evaluations: List[Dict[str, Any]], filename: str = None):
        """Save evaluation results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(evaluations, f, indent=2)
        
        return filename

# Quality check functions
def check_research_quality(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check if research meets quality standards"""
    issues = []
    
    # Check for basic requirements
    if not result.get('research_findings'):
        issues.append("No research findings collected")
    
    if not result.get('analysis'):
        issues.append("No analysis generated")
    
    if not result.get('report'):
        issues.append("No final report generated")
    
    # Check quality scores
    quality_score = result.get('research_quality_score', 0)
    if quality_score < 0.3:
        issues.append(f"Low quality score: {quality_score:.2f}")
    
    # Check source diversity
    sources_used = result.get('sources_used', [])
    if len(sources_used) < 2:
        issues.append(f"Insufficient source diversity: {len(sources_used)} sources")
    
    # Check for iteration limits
    if result.get('max_iterations_reached', False):
        issues.append("Maximum iterations reached - research may be incomplete")
    
    return len(issues) == 0, issues

def validate_research_output(result: Dict[str, Any]) -> bool:
    """Validate that research output meets minimum standards"""
    required_fields = ['question', 'research_findings', 'analysis', 'report']
    
    for field in required_fields:
        if not result.get(field):
            return False
    
    # Check findings quality
    findings = result.get('research_findings', [])
    if len(findings) < 2:
        return False
    
    # Check for at least one high-confidence finding
    high_confidence_findings = [f for f in findings if f.get('confidence', 0) >= 0.7]
    if not high_confidence_findings:
        return False
    
    return True
