#!/usr/bin/env python3
"""
Simple Test Suite for AI Video Compilation Pipeline
Basic structure validation without database dependencies
"""

import asyncio
import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleCompilationTest:
    """Simple test suite for basic pipeline validation."""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all basic tests."""
        logger.info("🧪 Starting Simple Compilation Pipeline Test")
        start_time = time.time()
        
        try:
            # Test imports
            await self._test_imports()
            
            # Test data structures
            await self._test_data_structures()
            
            # Test basic functionality
            await self._test_basic_functionality()
            
            # Calculate results
            total_time = time.time() - start_time
            self.test_results["total_time"] = total_time
            self.test_results["success_rate"] = (
                self.test_results["passed"] / max(self.test_results["total_tests"], 1) * 100
            )
            
            # Print summary
            self._print_summary()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            self.test_results["errors"].append(f"Test suite failure: {str(e)}")
            return self.test_results
    
    async def _test_imports(self):
        """Test that all components can be imported."""
        logger.info("📦 Testing Component Imports...")
        
        # Test 1: Requirements Generator
        try:
            from app.ai_requirements_generator import RequirementsGenerator, SearchQuery
            logger.info("✅ RequirementsGenerator imported successfully")
            self._record_test_result("Import RequirementsGenerator", True)
        except Exception as e:
            logger.error(f"❌ Failed to import RequirementsGenerator: {e}")
            self._record_test_result("Import RequirementsGenerator", False, str(e))
        
        # Test 2: Search Engine
        try:
            from app.compilation_search import CompilationSearchEngine, SearchResult, ContentMatch
            logger.info("✅ CompilationSearchEngine imported successfully")
            self._record_test_result("Import CompilationSearchEngine", True)
        except Exception as e:
            logger.error(f"❌ Failed to import CompilationSearchEngine: {e}")
            self._record_test_result("Import CompilationSearchEngine", False, str(e))
        
        # Test 3: Script Generator
        try:
            from app.ai_script_generator import ScriptGenerator, CompilationScript, ScriptSegment
            logger.info("✅ ScriptGenerator imported successfully")
            self._record_test_result("Import ScriptGenerator", True)
        except Exception as e:
            logger.error(f"❌ Failed to import ScriptGenerator: {e}")
            self._record_test_result("Import ScriptGenerator", False, str(e))
        
        # Test 4: Database Operations
        try:
            from app.generated_video_operations import GeneratedVideoDatabase
            logger.info("✅ GeneratedVideoDatabase imported successfully")
            self._record_test_result("Import GeneratedVideoDatabase", True)
        except Exception as e:
            logger.error(f"❌ Failed to import GeneratedVideoDatabase: {e}")
            self._record_test_result("Import GeneratedVideoDatabase", False, str(e))
        
        # Test 5: Main Pipeline
        try:
            from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest, CompilationResponse
            logger.info("✅ CompilationPipeline imported successfully")
            self._record_test_result("Import CompilationPipeline", True)
        except Exception as e:
            logger.error(f"❌ Failed to import CompilationPipeline: {e}")
            self._record_test_result("Import CompilationPipeline", False, str(e))
    
    async def _test_data_structures(self):
        """Test data structure creation and validation."""
        logger.info("🏗️ Testing Data Structures...")
        
        # Test 1: SearchQuery creation
        try:
            from app.ai_requirements_generator import SearchQuery
            
            query = SearchQuery(
                query_text="morning workout routine",
                priority=8,
                duration_target=300,
                tags_filter=["fitness", "beginner"],
                exclude_terms=[],  # Fixed: Added missing required parameter
                content_type="exercise"
            )
            
            assert query.query_text == "morning workout routine"
            assert query.priority == 8
            assert query.duration_target == 300
            assert "fitness" in query.tags_filter
            assert query.exclude_terms == []
            
            logger.info("✅ SearchQuery structure validated")
            self._record_test_result("SearchQuery Structure", True)
            
        except Exception as e:
            logger.error(f"❌ SearchQuery structure test failed: {e}")
            self._record_test_result("SearchQuery Structure", False, str(e))
        
        # Test 2: ContentMatch creation
        try:
            from app.compilation_search import ContentMatch
            
            match = ContentMatch(
                video_id="test-video-1",
                segment_type="scene",
                start_time=0.0,
                end_time=30.0,
                relevance_score=0.9,
                content_text="Morning warm-up routine",
                tags=["workout", "warm-up"],
                metadata={"duration": 30.0}
            )
            
            assert match.video_id == "test-video-1"
            assert match.segment_type == "scene"
            assert match.relevance_score == 0.9
            
            logger.info("✅ ContentMatch structure validated")
            self._record_test_result("ContentMatch Structure", True)
            
        except Exception as e:
            logger.error(f"❌ ContentMatch structure test failed: {e}")
            self._record_test_result("ContentMatch Structure", False, str(e))
        
        # Test 3: ScriptSegment creation
        try:
            from app.ai_script_generator import ScriptSegment
            
            segment = ScriptSegment(
                script_text="Welcome to your morning workout",
                start_time=0.0,
                end_time=30.0,
                assigned_video_id="test-video-1",
                assigned_video_start=0.0,
                assigned_video_end=30.0,
                transition_type="fade",
                segment_type="intro"
            )
            
            assert segment.script_text == "Welcome to your morning workout"
            assert segment.duration == 30.0  # Should calculate duration
            assert segment.assigned_video_id == "test-video-1"
            
            logger.info("✅ ScriptSegment structure validated")
            self._record_test_result("ScriptSegment Structure", True)
            
        except Exception as e:
            logger.error(f"❌ ScriptSegment structure test failed: {e}")
            self._record_test_result("ScriptSegment Structure", False, str(e))
        
        # Test 4: CompilationRequest creation
        try:
            from app.video_compilation_pipeline import CompilationRequest
            
            request = CompilationRequest(
                context="I want to create a morning workout routine",
                requirements="5 minutes, beginner-friendly, mobility focus",
                title="Morning Mobility Routine",
                voice_preference="alloy",
                resolution="720p",
                max_duration=600.0,
                include_base64=False
            )
            
            assert request.context == "I want to create a morning workout routine"
            assert request.voice_preference == "alloy"
            assert request.resolution == "720p"
            
            logger.info("✅ CompilationRequest structure validated")
            self._record_test_result("CompilationRequest Structure", True)
            
        except Exception as e:
            logger.error(f"❌ CompilationRequest structure test failed: {e}")
            self._record_test_result("CompilationRequest Structure", False, str(e))
    
    async def _test_basic_functionality(self):
        """Test basic functionality without database connections."""
        logger.info("⚙️ Testing Basic Functionality...")
        
        # Test 1: Fallback query generation (direct method call)
        try:
            from app.ai_requirements_generator import RequirementsGenerator
            
            # Test the fallback method directly instead of through the main method
            generator = RequirementsGenerator(None)  # No connections
            
            context = "I want to create a morning workout routine"
            requirements = "5 minutes, beginner-friendly, mobility focus"
            
            # Call the fallback method directly
            queries = generator._generate_fallback_queries(context, requirements)
            
            assert len(queries) > 0, "Should generate fallback queries"
            assert all(hasattr(q, 'query_text') for q in queries), "All queries should have query_text"
            assert all(1 <= q.priority <= 10 for q in queries), "Priority should be 1-10"
            
            logger.info(f"✅ Fallback query generation works ({len(queries)} queries)")
            self._record_test_result("Fallback Query Generation", True)
            
        except Exception as e:
            logger.error(f"❌ Fallback query generation failed: {e}")
            self._record_test_result("Fallback Query Generation", False, str(e))
        
        # Test 2: Script segment timing calculations
        try:
            from app.ai_script_generator import ScriptSegment
            
            # Create segments with different timings
            segment1 = ScriptSegment(
                script_text="First segment",
                start_time=0.0,
                end_time=30.0,
                assigned_video_id="video-1",
                assigned_video_start=0.0,
                assigned_video_end=30.0,
                transition_type="fade",
                segment_type="intro"
            )
            
            segment2 = ScriptSegment(
                script_text="Second segment",
                start_time=30.0,
                end_time=90.0,
                assigned_video_id="video-2",
                assigned_video_start=0.0,
                assigned_video_end=60.0,
                transition_type="cut",
                segment_type="main"
            )
            
            # Test duration calculations
            assert segment1.duration == 30.0, f"Expected 30.0, got {segment1.duration}"
            assert segment2.duration == 60.0, f"Expected 60.0, got {segment2.duration}"
            
            logger.info("✅ Script segment timing calculations work")
            self._record_test_result("Script Timing Calculations", True)
            
        except Exception as e:
            logger.error(f"❌ Script timing calculations failed: {e}")
            self._record_test_result("Script Timing Calculations", False, str(e))
        
        # Test 3: Pipeline request validation
        try:
            from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest
            
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
            
            logger.info("✅ Pipeline request validation works")
            self._record_test_result("Pipeline Request Validation", True)
            
        except Exception as e:
            logger.error(f"❌ Pipeline request validation failed: {e}")
            self._record_test_result("Pipeline Request Validation", False, str(e))
        
        # Test 4: Auto title generation
        try:
            from app.video_compilation_pipeline import CompilationPipeline
            
            pipeline = CompilationPipeline()
            
            # Test different contexts
            title1 = pipeline._generate_auto_title("morning workout routine", "beginner friendly")
            title2 = pipeline._generate_auto_title("mobility session", "stretching and flexibility")
            title3 = pipeline._generate_auto_title("strength training", "core exercises")
            
            assert isinstance(title1, str) and len(title1) > 0, "Should generate valid title"
            assert isinstance(title2, str) and len(title2) > 0, "Should generate valid title"
            assert isinstance(title3, str) and len(title3) > 0, "Should generate valid title"
            
            logger.info("✅ Auto title generation works")
            self._record_test_result("Auto Title Generation", True)
            
        except Exception as e:
            logger.error(f"❌ Auto title generation failed: {e}")
            self._record_test_result("Auto Title Generation", False, str(e))
    
    def _record_test_result(self, test_name: str, passed: bool, error: str = None):
        """Record a test result."""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
            if error:
                self.test_results["errors"].append(f"{test_name}: {error}")
    
    def _print_summary(self):
        """Print test summary."""
        logger.info("\n" + "="*60)
        logger.info("🧪 SIMPLE COMPILATION PIPELINE TEST SUMMARY")
        logger.info("="*60)
        
        # Overall stats
        logger.info(f"📊 OVERALL RESULTS:")
        logger.info(f"   Total Tests: {self.test_results['total_tests']}")
        logger.info(f"   ✅ Passed: {self.test_results['passed']}")
        logger.info(f"   ❌ Failed: {self.test_results['failed']}")
        logger.info(f"   📈 Success Rate: {self.test_results['success_rate']:.1f}%")
        logger.info(f"   ⏱️  Total Time: {self.test_results['total_time']:.2f}s")
        
        # Errors
        if self.test_results["errors"]:
            logger.info(f"\n❌ ERRORS:")
            for error in self.test_results["errors"]:
                logger.info(f"   - {error}")
        
        # Status
        if self.test_results["failed"] == 0:
            logger.info(f"\n🎉 ALL TESTS PASSED! Pipeline structure is valid.")
        else:
            logger.info(f"\n⚠️  Some tests failed. Check errors above.")
        
        logger.info("="*60)

# Main execution
async def main():
    """Run the simple test suite."""
    tester = SimpleCompilationTest()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    if results["failed"] > 0:
        return 1
    else:
        return 0

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 