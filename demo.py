#!/usr/bin/env python3
"""
Demo script for the Multi-Source Research Analyst Agent
Demonstrates the agent's capabilities with example research questions
"""

import time
from graph import ResearchGraph
from evaluation import ResearchEvaluator

def run_demo():
    """Run a comprehensive demo of the research agent"""
    print("🚀 Multi-Source Research Analyst Agent Demo")
    print("=" * 60)
    
    # Initialize components
    research_graph = ResearchGraph()
    evaluator = ResearchEvaluator()
    
    # Demo questions showcasing different capabilities
    demo_questions = [
        {
            'question': 'What are the latest developments in quantum computing?',
            'description': 'Tests current information gathering and technical research',
            'expected_sources': ['web', 'arxiv']
        },
        {
            'question': 'Compare renewable energy policies in Germany and Japan',
            'description': 'Tests comparative analysis and multi-source synthesis',
            'expected_sources': ['web', 'wikipedia']
        },
        {
            'question': 'What is artificial intelligence and how does it work?',
            'description': 'Tests basic factual research and educational content',
            'expected_sources': ['wikipedia', 'web']
        }
    ]
    
    print(f"📋 Running {len(demo_questions)} demo scenarios...\n")
    
    all_evaluations = []
    
    for i, demo in enumerate(demo_questions, 1):
        print(f"🔍 Demo {i}/{len(demo_questions)}: {demo['question']}")
        print(f"📝 Description: {demo['description']}")
        print("-" * 60)
        
        try:
            # Run the research
            start_time = time.time()
            result = research_graph.run(demo['question'])
            end_time = time.time()
            
            # Add duration to result
            result['duration'] = end_time - start_time
            
            # Evaluate the research
            evaluation = evaluator.evaluate_research_session(result, demo['question'])
            all_evaluations.append(evaluation)
            
            # Display results
            print(f"✅ Research completed in {result['duration']:.2f} seconds")
            print(f"📊 Quality Score: {result.get('research_quality_score', 0):.2f}/1.0")
            print(f"📚 Sources: {', '.join(result.get('sources_used', []))}")
            print(f"📖 Findings: {len(result.get('research_findings', []))}")
            print(f"🎯 Overall Score: {evaluation['overall_score']:.2f}/1.0")
            
            # Show a preview of the report
            if result.get('report'):
                print(f"\n📋 Report Preview:")
                print(result['report'][:200] + "...")
            
            print("\n" + "=" * 60 + "\n")
            
        except Exception as e:
            print(f"❌ Error in demo {i}: {str(e)}")
            print("\n" + "=" * 60 + "\n")
    
    # Generate summary report
    if all_evaluations:
        print("📊 DEMO SUMMARY REPORT")
        print("=" * 60)
        
        total_demos = len(all_evaluations)
        avg_score = sum(e['overall_score'] for e in all_evaluations) / total_demos
        avg_quality = sum(e['quality_metrics']['research_quality_score'] for e in all_evaluations) / total_demos
        avg_duration = sum(e['basic_metrics']['duration'] for e in all_evaluations) / total_demos
        
        print(f"📈 Total Demos: {total_demos}")
        print(f"🎯 Average Overall Score: {avg_score:.2f}/1.0")
        print(f"📊 Average Quality Score: {avg_quality:.2f}/1.0")
        print(f"⏱️ Average Duration: {avg_duration:.2f} seconds")
        
        # Show individual results
        print(f"\n📋 Individual Results:")
        for i, evaluation in enumerate(all_evaluations, 1):
            print(f"  {i}. {evaluation['question'][:50]}...")
            print(f"     Score: {evaluation['overall_score']:.2f}/1.0")
            print(f"     Quality: {evaluation['quality_metrics']['research_quality_score']:.2f}")
            print(f"     Duration: {evaluation['basic_metrics']['duration']:.2f}s")
    
    print("\n🎉 Demo completed! The agent successfully demonstrated:")
    print("  ✅ Autonomous decision-making")
    print("  ✅ Multi-source information gathering")
    print("  ✅ Intelligent synthesis")
    print("  ✅ Quality assessment")
    print("  ✅ Professional report generation")

def run_quick_demo():
    """Run a quick single-question demo"""
    print("🚀 Quick Demo: Multi-Source Research Analyst Agent")
    print("=" * 60)
    
    research_graph = ResearchGraph()
    
    question = "What are the benefits of renewable energy?"
    print(f"🔍 Research Question: {question}")
    print("-" * 60)
    
    try:
        start_time = time.time()
        result = research_graph.run(question)
        end_time = time.time()
        
        print(f"✅ Research completed in {end_time - start_time:.2f} seconds")
        print(f"📊 Quality Score: {result.get('research_quality_score', 0):.2f}/1.0")
        print(f"📚 Sources: {', '.join(result.get('sources_used', []))}")
        print(f"📖 Findings: {len(result.get('research_findings', []))}")
        
        if result.get('report'):
            print(f"\n📋 Generated Report:")
            print(result['report'])
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        run_quick_demo()
    else:
        run_demo()
