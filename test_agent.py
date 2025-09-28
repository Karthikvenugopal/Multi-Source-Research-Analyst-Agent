#!/usr/bin/env python3
"""
Test script for the Multi-Source Research Analyst Agent
Tests the agent with various research questions and evaluates performance
"""

import time
import json
from datetime import datetime
from graph import ResearchGraph

class AgentTester:
    def __init__(self):
        self.research_graph = ResearchGraph()
        self.test_results = []
    
    def run_test(self, question: str, expected_sources: list = None, max_duration: int = 60):
        """Run a single test case"""
        print(f"\n🔍 Testing: {question}")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            result = self.research_graph.run(question)
            end_time = time.time()
            
            duration = end_time - start_time
            quality_score = result.get('research_quality_score', 0.0)
            iterations = result.get('iterations', 0)
            sources_used = result.get('sources_used', [])
            findings_count = len(result.get('research_findings', []))
            
            # Evaluate the test
            test_result = {
                'question': question,
                'duration': duration,
                'quality_score': quality_score,
                'iterations': iterations,
                'sources_used': sources_used,
                'findings_count': findings_count,
                'success': duration < max_duration and quality_score > 0.3,
                'timestamp': datetime.now().isoformat()
            }
            
            # Print results
            print(f"✅ Duration: {duration:.2f}s")
            print(f"📊 Quality Score: {quality_score:.2f}/1.0")
            print(f"🔄 Iterations: {iterations}")
            print(f"📚 Sources: {', '.join(sources_used)}")
            print(f"📖 Findings: {findings_count}")
            print(f"🎯 Success: {'✅' if test_result['success'] else '❌'}")
            
            if result.get('report'):
                print(f"\n📋 Report Preview:")
                print(result['report'][:200] + "...")
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            error_result = {
                'question': question,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            self.test_results.append(error_result)
            return error_result
    
    def run_test_suite(self):
        """Run a comprehensive test suite"""
        print("🚀 Starting Multi-Source Research Analyst Test Suite")
        print("=" * 80)
        
        # Test cases with different complexity levels
        test_cases = [
            {
                'question': 'What is artificial intelligence?',
                'expected_sources': ['wikipedia', 'web'],
                'max_duration': 30
            },
            {
                'question': 'What are the latest developments in quantum computing?',
                'expected_sources': ['web', 'arxiv'],
                'max_duration': 45
            },
            {
                'question': 'Compare renewable energy policies in Germany and Japan',
                'expected_sources': ['web', 'wikipedia'],
                'max_duration': 60
            },
            {
                'question': 'What are the competing theories about dark matter?',
                'expected_sources': ['arxiv', 'wikipedia', 'web'],
                'max_duration': 60
            },
            {
                'question': 'How does climate change affect global food security?',
                'expected_sources': ['web', 'wikipedia'],
                'max_duration': 45
            }
        ]
        
        print(f"📋 Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}/{len(test_cases)}")
            self.run_test(
                test_case['question'],
                test_case.get('expected_sources'),
                test_case.get('max_duration', 60)
            )
            time.sleep(2)  # Brief pause between tests
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a summary report of all tests"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get('success', False))
        failed_tests = total_tests - successful_tests
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if self.test_results:
            avg_duration = sum(r.get('duration', 0) for r in self.test_results if 'duration' in r) / len([r for r in self.test_results if 'duration' in r])
            avg_quality = sum(r.get('quality_score', 0) for r in self.test_results if 'quality_score' in r) / len([r for r in self.test_results if 'quality_score' in r])
            avg_iterations = sum(r.get('iterations', 0) for r in self.test_results if 'iterations' in r) / len([r for r in self.test_results if 'iterations' in r])
            
            print(f"⏱️ Average Duration: {avg_duration:.2f}s")
            print(f"📊 Average Quality Score: {avg_quality:.2f}/1.0")
            print(f"🔄 Average Iterations: {avg_iterations:.1f}")
        
        # Save detailed results
        self.save_results()
    
    def save_results(self):
        """Save test results to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")

def main():
    """Main function to run the test suite"""
    tester = AgentTester()
    tester.run_test_suite()

if __name__ == "__main__":
    main()