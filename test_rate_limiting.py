#!/usr/bin/env python3
"""
Test script for AI Rate Limiting functionality

Demonstrates:
- Rate limiting in action
- Circuit breaker behavior
- Usage statistics monitoring
- Error handling for different rate limit scenarios
"""

import asyncio
import json
import time
from app.ai_rate_limiter import get_rate_limiter, get_all_usage_stats, RateLimitType

async def simulate_api_call_success():
    """Simulate a successful API call"""
    await asyncio.sleep(0.1)  # Simulate API latency
    return {"status": "success", "result": "AI analysis complete"}

async def simulate_api_call_rate_limit():
    """Simulate a rate limit error"""
    await asyncio.sleep(0.1)
    raise Exception("Rate limit exceeded - too many requests per minute")

async def simulate_api_call_quota_exceeded():
    """Simulate daily quota exceeded"""
    await asyncio.sleep(0.1)
    raise Exception("Daily quota exceeded for this API key")

async def simulate_api_call_service_overload():
    """Simulate service overload"""
    await asyncio.sleep(0.1)
    raise Exception("Service temporarily overloaded - please try again later")

async def test_basic_rate_limiting():
    """Test basic rate limiting functionality"""
    print("🧪 Testing Basic Rate Limiting...")
    
    rate_limiter = get_rate_limiter("openai")
    
    try:
        # Test successful API call
        result = await rate_limiter.execute_with_rate_limiting(
            simulate_api_call_success,
            estimated_tokens=1000
        )
        print("✅ Successful API call:", result)
        
        # Get usage stats
        stats = rate_limiter.get_usage_stats()
        print(f"📊 Usage: {stats['current_usage']['requests_this_minute']} requests, "
              f"{stats['current_usage']['tokens_this_minute']} tokens")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_rate_limit_handling():
    """Test rate limit error handling"""
    print("\n🧪 Testing Rate Limit Error Handling...")
    
    rate_limiter = get_rate_limiter("gemini")
    
    try:
        # This should trigger rate limiting behavior
        result = await rate_limiter.execute_with_rate_limiting(
            simulate_api_call_rate_limit,
            estimated_tokens=2000
        )
        print("✅ Rate limit handled:", result)
        
    except Exception as e:
        print(f"⚠️ Rate limit error (expected): {e}")

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n🧪 Testing Circuit Breaker...")
    
    rate_limiter = get_rate_limiter("test_provider")
    
    # Cause multiple failures to trigger circuit breaker
    for i in range(6):  # More than failure threshold (5)
        try:
            await rate_limiter.execute_with_rate_limiting(
                simulate_api_call_service_overload,
                estimated_tokens=500
            )
        except Exception as e:
            print(f"Attempt {i+1}: {e}")
    
    # Check circuit breaker state
    stats = rate_limiter.get_usage_stats()
    print(f"🔄 Circuit Breaker State: {stats['circuit_breaker']['state']}")
    print(f"🔄 Failure Count: {stats['circuit_breaker']['failure_count']}")

async def test_quota_exhaustion():
    """Test daily quota exhaustion handling"""
    print("\n🧪 Testing Daily Quota Exhaustion...")
    
    rate_limiter = get_rate_limiter("quota_test")
    
    try:
        result = await rate_limiter.execute_with_rate_limiting(
            simulate_api_call_quota_exceeded,
            estimated_tokens=10000
        )
        print("✅ Quota handling:", result)
        
    except Exception as e:
        print(f"⚠️ Quota exhaustion (expected): {e}")

async def test_usage_monitoring():
    """Test usage statistics monitoring"""
    print("\n🧪 Testing Usage Monitoring...")
    
    # Make several API calls to generate usage data
    rate_limiter = get_rate_limiter("monitoring_test")
    
    for i in range(3):
        try:
            await rate_limiter.execute_with_rate_limiting(
                simulate_api_call_success,
                estimated_tokens=1500 + (i * 500)
            )
            print(f"API call {i+1} completed")
        except Exception as e:
            print(f"API call {i+1} failed: {e}")
    
    # Get comprehensive usage stats
    all_stats = get_all_usage_stats()
    print("\n📊 All Provider Usage Statistics:")
    print(json.dumps(all_stats, indent=2, default=str))

async def demonstrate_exponential_backoff():
    """Demonstrate exponential backoff with retries"""
    print("\n🧪 Demonstrating Exponential Backoff...")
    
    rate_limiter = get_rate_limiter("backoff_test")
    
    # Create a function that fails a few times then succeeds
    attempt_count = 0
    
    async def flaky_api_call():
        nonlocal attempt_count
        attempt_count += 1
        await asyncio.sleep(0.1)
        
        if attempt_count <= 2:  # Fail first 2 attempts
            raise Exception("Temporary service error - please retry")
        else:
            return {"status": "success", "attempt": attempt_count}
    
    try:
        start_time = time.time()
        result = await rate_limiter.execute_with_rate_limiting(
            flaky_api_call,
            estimated_tokens=800
        )
        end_time = time.time()
        
        print(f"✅ Success after {attempt_count} attempts in {end_time - start_time:.2f}s")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Failed after retries: {e}")

async def main():
    """Run all rate limiting tests"""
    print("🚦 AI Rate Limiting Test Suite")
    print("=" * 50)
    
    try:
        await test_basic_rate_limiting()
        await test_rate_limit_handling()
        await test_circuit_breaker()
        await test_quota_exhaustion()
        await test_usage_monitoring()
        await demonstrate_exponential_backoff()
        
        print("\n🎉 Rate Limiting Test Suite Complete!")
        print("\n💡 Usage Tips:")
        print("   • Monitor circuit breaker states for service health")
        print("   • Use /rate-limits endpoint for real-time monitoring")
        print("   • Adjust rate limits based on your API tier")
        print("   • Plan capacity using daily quota tracking")
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 