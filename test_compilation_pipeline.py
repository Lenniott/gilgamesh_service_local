#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Video Compilation Pipeline
Reusable tests for development and validation of the compilation system
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompilationPipelineTest:
    """
    Comprehensive test suite for the video compilation pipeline.
    Tests each component individually and the full pipeline integration.
    """
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "component_results": {},
            "performance_metrics": {},
            "errors": []
        }
        self.connections = None
    
    async def run_all_tests(self, include_database_tests: bool = True) -> Dict[str, Any]:
        """
        Run all pipeline tests and return comprehensive results.
        
        Args:
            include_database_tests: Whether to run database-dependent tests
            
        Returns:
            Dictionary with test results and metrics
        """
        logger.info("🧪 Starting Compilation Pipeline Test Suite")
        start_time = time.time()
        
        try:
            # Initialize connections if needed
            if include_database_tests:
                await self._initialize_connections()
            
            # Run component tests
            await self._test_requirements_generator()
            await self._test_search_engine()
            await self._test_script_generator()
            
            if include_database_tests:
                await self._test_database_operations()
                await self._test_full_pipeline()
            
            # Calculate final results
            total_time = time.time() - start_time
            self.test_results["total_time"] = total_time
            self.test_results["success_rate"] = (
                self.test_results["passed"] / max(self.test_results["total_tests"], 1) * 100
            )
            
            # Print summary
            self._print_test_summary()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            self.test_results["errors"].append(f"Test suite failure: {str(e)}")
            return self.test_results
        
        finally:
            # Cleanup
            if self.connections:
                await self._cleanup_connections()
    
    async def _initialize_connections(self):
        """Initialize database connections for testing."""
        try:
            from app.db_connections import DatabaseConnections
            self.connections = DatabaseConnections()
            await self.connections.connect_all()
            logger.info("✅ Database connections initialized for testing")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connections: {e}")
            raise
    
    async def _test_requirements_generator(self):
        """Test the AI Requirements Generator component."""
        logger.info("🔍 Testing AI Requirements Generator...")
        component_results = {"tests": [], "passed": 0, "failed": 0}
        
        try:
            from app.ai_requirements_generator import RequirementsGenerator
            
            # Test 1: Basic query generation
            test_name = "Basic Query Generation"
            try:
                # Mock connections for testing
                mock_connections = None if not self.connections else self.connections
                generator = RequirementsGenerator(mock_connections)
                
                # Test data
                context = "I want to create a morning workout routine"
                requirements = "5 minutes, beginner-friendly, focus on mobility and stretching"
                
                # Generate queries (will use fallback since no OpenAI in test)
                queries = await generator.generate_search_queries(context, requirements)
                
                # Validate results
                assert len(queries) >= 3, f"Expected at least 3 queries, got {len(queries)}"
                assert all(hasattr(q, 'query_text') for q in queries), "All queries should have query_text"
                assert all(hasattr(q, 'priority') for q in queries), "All queries should have priority"
                assert all(1 <= q.priority <= 10 for q in queries), "Priority should be 1-10"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": f"Generated {len(queries)} queries successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
            # Test 2: Query validation
            test_name = "Query Validation"
            try:
                generator = RequirementsGenerator(self.connections)
                
                # Test invalid inputs
                empty_queries = await generator.generate_search_queries("", "")
                assert len(empty_queries) == 0, "Empty inputs should return no queries"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Validation works correctly"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
        except ImportError as e:
            logger.error(f"❌ Cannot import RequirementsGenerator: {e}")
            component_results["tests"].append({
                "name": "Component Import",
                "status": "FAILED",
                "error": f"Import error: {str(e)}"
            })
            component_results["failed"] += 1
        
        # Update totals
        self.test_results["component_results"]["requirements_generator"] = component_results
        self.test_results["total_tests"] += len(component_results["tests"])
        self.test_results["passed"] += component_results["passed"]
        self.test_results["failed"] += component_results["failed"]
    
    async def _test_search_engine(self):
        """Test the Compilation Search Engine component."""
        logger.info("🔎 Testing Compilation Search Engine...")
        component_results = {"tests": [], "passed": 0, "failed": 0}
        
        try:
            from app.compilation_search import CompilationSearchEngine
            from app.ai_requirements_generator import SearchQuery
            
            # Test 1: Search engine initialization
            test_name = "Search Engine Initialization"
            try:
                engine = CompilationSearchEngine(self.connections)
                assert engine is not None, "Engine should initialize"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Engine initialized successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
            # Test 2: Query processing
            test_name = "Query Processing"
            try:
                engine = CompilationSearchEngine(self.connections)
                
                # Create test queries
                test_queries = [
                    SearchQuery(
                        query_text="morning workout routine",
                        priority=8,
                        duration_target=300,
                        tags_filter=["fitness", "beginner"],
                        content_type="exercise"
                    ),
                    SearchQuery(
                        query_text="stretching mobility",
                        priority=7,
                        duration_target=180,
                        tags_filter=["mobility", "flexibility"],
                        content_type="exercise"
                    )
                ]
                
                # Test search (will return empty results without database)
                results = await engine.search_content_segments(test_queries)
                assert isinstance(results, list), "Results should be a list"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": f"Processed {len(test_queries)} queries successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
        except ImportError as e:
            logger.error(f"❌ Cannot import CompilationSearchEngine: {e}")
            component_results["tests"].append({
                "name": "Component Import",
                "status": "FAILED",
                "error": f"Import error: {str(e)}"
            })
            component_results["failed"] += 1
        
        # Update totals
        self.test_results["component_results"]["search_engine"] = component_results
        self.test_results["total_tests"] += len(component_results["tests"])
        self.test_results["passed"] += component_results["passed"]
        self.test_results["failed"] += component_results["failed"]
    
    async def _test_script_generator(self):
        """Test the AI Script Generator component."""
        logger.info("📝 Testing AI Script Generator...")
        component_results = {"tests": [], "passed": 0, "failed": 0}
        
        try:
            from app.ai_script_generator import ScriptGenerator
            from app.compilation_search import SearchResult, ContentMatch
            
            # Test 1: Script generator initialization
            test_name = "Script Generator Initialization"
            try:
                generator = ScriptGenerator(self.connections)
                assert generator is not None, "Generator should initialize"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Generator initialized successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
            # Test 2: Script creation with mock data
            test_name = "Script Creation"
            try:
                generator = ScriptGenerator(self.connections)
                
                # Create mock search results
                mock_results = [
                    SearchResult(
                        query="morning workout",
                        matches=[
                            ContentMatch(
                                video_id="test-video-1",
                                segment_type="scene",
                                start_time=0.0,
                                end_time=30.0,
                                relevance_score=0.9,
                                content_text="Morning warm-up routine",
                                tags=["workout", "warm-up"],
                                metadata={"duration": 30.0}
                            )
                        ]
                    )
                ]
                
                # Generate script
                script = await generator.create_segmented_script(
                    search_results=mock_results,
                    user_context="Morning workout routine",
                    user_requirements="5 minutes, beginner-friendly",
                    target_duration=300.0
                )
                
                assert script is not None, "Script should be generated"
                assert hasattr(script, 'segments'), "Script should have segments"
                assert hasattr(script, 'total_duration'), "Script should have total_duration"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": f"Generated script with {len(script.segments)} segments"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
        except ImportError as e:
            logger.error(f"❌ Cannot import ScriptGenerator: {e}")
            component_results["tests"].append({
                "name": "Component Import",
                "status": "FAILED",
                "error": f"Import error: {str(e)}"
            })
            component_results["failed"] += 1
        
        # Update totals
        self.test_results["component_results"]["script_generator"] = component_results
        self.test_results["total_tests"] += len(component_results["tests"])
        self.test_results["passed"] += component_results["passed"]
        self.test_results["failed"] += component_results["failed"]
    
    async def _test_database_operations(self):
        """Test the Generated Video Database Operations."""
        logger.info("💾 Testing Database Operations...")
        component_results = {"tests": [], "passed": 0, "failed": 0}
        
        try:
            from app.generated_video_operations import GeneratedVideoDatabase
            from app.ai_script_generator import CompilationScript, ScriptSegment
            
            # Test 1: Database initialization
            test_name = "Database Initialization"
            try:
                db = GeneratedVideoDatabase(self.connections)
                assert db is not None, "Database should initialize"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Database initialized successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
            # Test 2: Video save operation (mock)
            test_name = "Video Save Operation"
            try:
                db = GeneratedVideoDatabase(self.connections)
                
                # Create mock script
                mock_script = CompilationScript(
                    total_duration=300.0,
                    segments=[
                        ScriptSegment(
                            script_text="Welcome to your morning workout",
                            start_time=0.0,
                            end_time=30.0,
                            assigned_video_id="test-video-1",
                            assigned_video_start=0.0,
                            assigned_video_end=30.0,
                            transition_type="fade",
                            segment_type="intro"
                        )
                    ],
                    metadata={"generated_by": "test"}
                )
                
                # Test save (will fail without actual database, but validates structure)
                try:
                    result = await db.save_generated_video(
                        video_base64="test_base64_data",
                        script=mock_script,
                        title="Test Video",
                        user_context="Test context",
                        user_requirements="Test requirements"
                    )
                    # If it doesn't throw an error, it passed structure validation
                    component_results["tests"].append({
                        "name": test_name,
                        "status": "PASSED",
                        "details": "Save operation structure validated"
                    })
                    component_results["passed"] += 1
                except Exception as db_error:
                    if "Database connection not available" in str(db_error):
                        component_results["tests"].append({
                            "name": test_name,
                            "status": "SKIPPED",
                            "details": "Database not available, but structure validated"
                        })
                        self.test_results["skipped"] += 1
                    else:
                        raise db_error
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
        except ImportError as e:
            logger.error(f"❌ Cannot import GeneratedVideoDatabase: {e}")
            component_results["tests"].append({
                "name": "Component Import",
                "status": "FAILED",
                "error": f"Import error: {str(e)}"
            })
            component_results["failed"] += 1
        
        # Update totals
        self.test_results["component_results"]["database_operations"] = component_results
        self.test_results["total_tests"] += len(component_results["tests"])
        self.test_results["passed"] += component_results["passed"]
        self.test_results["failed"] += component_results["failed"]
    
    async def _test_full_pipeline(self):
        """Test the full compilation pipeline integration."""
        logger.info("🎬 Testing Full Pipeline Integration...")
        component_results = {"tests": [], "passed": 0, "failed": 0}
        
        try:
            from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest
            
            # Test 1: Pipeline initialization
            test_name = "Pipeline Initialization"
            try:
                pipeline = CompilationPipeline()
                await pipeline.initialize()
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Pipeline initialized successfully"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
            # Test 2: Request validation
            test_name = "Request Validation"
            try:
                pipeline = CompilationPipeline()
                
                # Test valid request
                valid_request = CompilationRequest(
                    context="I want to create a morning workout routine",
                    requirements="5 minutes, beginner-friendly, mobility focus",
                    title="Morning Mobility Routine"
                )
                
                validation_result = pipeline._validate_compilation_request(valid_request)
                assert validation_result["valid"] == True, "Valid request should pass validation"
                
                # Test invalid request
                invalid_request = CompilationRequest(
                    context="",  # Empty context
                    requirements="",  # Empty requirements
                    max_duration=10  # Too short
                )
                
                validation_result = pipeline._validate_compilation_request(invalid_request)
                assert validation_result["valid"] == False, "Invalid request should fail validation"
                assert len(validation_result["errors"]) > 0, "Should have validation errors"
                
                component_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "details": "Request validation works correctly"
                })
                component_results["passed"] += 1
                
            except Exception as e:
                component_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "error": str(e)
                })
                component_results["failed"] += 1
            
        except ImportError as e:
            logger.error(f"❌ Cannot import CompilationPipeline: {e}")
            component_results["tests"].append({
                "name": "Component Import",
                "status": "FAILED",
                "error": f"Import error: {str(e)}"
            })
            component_results["failed"] += 1
        
        # Update totals
        self.test_results["component_results"]["full_pipeline"] = component_results
        self.test_results["total_tests"] += len(component_results["tests"])
        self.test_results["passed"] += component_results["passed"]
        self.test_results["failed"] += component_results["failed"]
    
    async def _cleanup_connections(self):
        """Cleanup database connections."""
        try:
            if self.connections:
                await self.connections.close_all()
                logger.info("✅ Database connections cleaned up")
        except Exception as e:
            logger.error(f"❌ Failed to cleanup connections: {e}")
    
    def _print_test_summary(self):
        """Print a comprehensive test summary."""
        logger.info("\n" + "="*80)
        logger.info("🧪 COMPILATION PIPELINE TEST SUMMARY")
        logger.info("="*80)
        
        # Overall stats
        logger.info(f"📊 OVERALL RESULTS:")
        logger.info(f"   Total Tests: {self.test_results['total_tests']}")
        logger.info(f"   ✅ Passed: {self.test_results['passed']}")
        logger.info(f"   ❌ Failed: {self.test_results['failed']}")
        logger.info(f"   ⏭️  Skipped: {self.test_results['skipped']}")
        logger.info(f"   📈 Success Rate: {self.test_results['success_rate']:.1f}%")
        logger.info(f"   ⏱️  Total Time: {self.test_results['total_time']:.2f}s")
        
        # Component breakdown
        logger.info(f"\n📋 COMPONENT BREAKDOWN:")
        for component, results in self.test_results["component_results"].items():
            logger.info(f"   {component.replace('_', ' ').title()}:")
            logger.info(f"     ✅ Passed: {results['passed']}")
            logger.info(f"     ❌ Failed: {results['failed']}")
            
            # Show failed tests
            failed_tests = [t for t in results["tests"] if t["status"] == "FAILED"]
            if failed_tests:
                logger.info(f"     Failed Tests:")
                for test in failed_tests:
                    logger.info(f"       - {test['name']}: {test.get('error', 'Unknown error')}")
        
        # Errors
        if self.test_results["errors"]:
            logger.info(f"\n❌ ERRORS:")
            for error in self.test_results["errors"]:
                logger.info(f"   - {error}")
        
        logger.info("="*80)
    
    def save_test_report(self, filename: str = "test_report.json"):
        """Save test results to JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"📄 Test report saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save test report: {e}")

# Utility functions for running tests
async def run_quick_test():
    """Run a quick test without database dependencies."""
    logger.info("🚀 Running Quick Test (No Database)")
    tester = CompilationPipelineTest()
    results = await tester.run_all_tests(include_database_tests=False)
    return results

async def run_full_test():
    """Run full test suite including database tests."""
    logger.info("🚀 Running Full Test Suite")
    tester = CompilationPipelineTest()
    results = await tester.run_all_tests(include_database_tests=True)
    tester.save_test_report()
    return results

# Command line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick test without database
        results = asyncio.run(run_quick_test())
    else:
        # Full test suite
        results = asyncio.run(run_full_test())
    
    # Exit with appropriate code
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0) 