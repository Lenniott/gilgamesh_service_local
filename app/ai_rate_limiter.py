#!/usr/bin/env python3
"""
AI API Rate Limiter with Circuit Breaker and Quota Management

Handles rate limiting for OpenAI and Gemini APIs with:
- Exponential backoff with jitter
- Circuit breaker patterns
- Daily/hourly quota tracking
- Provider switching on quota exhaustion
- Token usage monitoring
"""

import asyncio
import time
import random
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Types of rate limiting scenarios"""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    TOKENS_PER_MINUTE = "tokens_per_minute"
    DAILY_QUOTA = "daily_quota"
    CONCURRENT_REQUESTS = "concurrent_requests"
    TEMPORARY_OVERLOAD = "temporary_overload"

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Request limits
    requests_per_minute: int = 60
    tokens_per_minute: int = 150000
    daily_quota: int = 100000
    concurrent_requests: int = 10
    
    # Backoff settings
    initial_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    max_retries: int = 5
    
    # Circuit breaker settings
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 300  # 5 minutes

@dataclass
class UsageStats:
    """Track API usage statistics"""
    requests_count: int = 0
    tokens_used: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    daily_requests: int = 0
    daily_tokens: int = 0
    daily_reset: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

class CircuitBreaker:
    """Circuit breaker for AI API calls"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
    
    def can_proceed(self) -> bool:
        """Check if request can proceed based on circuit breaker state"""
        now = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful API call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed API call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.timeout_seconds)
            logger.warning(f"Circuit breaker opened - too many failures ({self.failure_count})")

class AIRateLimiter:
    """Comprehensive rate limiter for AI APIs"""
    
    def __init__(self, provider: str, config: Optional[RateLimitConfig] = None):
        self.provider = provider
        self.config = config or RateLimitConfig()
        self.usage_stats = UsageStats()
        self.circuit_breaker = CircuitBreaker(self.config)
        self.semaphore = asyncio.Semaphore(self.config.concurrent_requests)
        self.request_timestamps = []
        self.token_usage = []
        
        # Provider-specific configurations
        self._setup_provider_config()
    
    def _setup_provider_config(self):
        """Setup provider-specific rate limiting configurations"""
        if self.provider == "openai":
            # OpenAI GPT-4 Vision limits
            self.config.requests_per_minute = 60
            self.config.tokens_per_minute = 150000
            self.config.daily_quota = 100000
        elif self.provider == "gemini":
            # Gemini Flash limits (adjust based on actual limits)
            self.config.requests_per_minute = 100
            self.config.tokens_per_minute = 300000
            self.config.daily_quota = 1000000
    
    def _reset_counters_if_needed(self):
        """Reset counters if time windows have passed"""
        now = datetime.now()
        
        # Reset minute counters
        if now - self.usage_stats.last_reset > timedelta(minutes=1):
            self.usage_stats.requests_count = 0
            self.usage_stats.tokens_used = 0
            self.usage_stats.last_reset = now
            self.request_timestamps.clear()
            self.token_usage.clear()
        
        # Reset daily counters
        if now >= self.usage_stats.daily_reset + timedelta(days=1):
            self.usage_stats.daily_requests = 0
            self.usage_stats.daily_tokens = 0
            self.usage_stats.daily_reset = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _check_rate_limits(self) -> Optional[RateLimitType]:
        """Check if any rate limits would be exceeded"""
        self._reset_counters_if_needed()
        
        # Check daily quota
        if self.usage_stats.daily_requests >= self.config.daily_quota:
            return RateLimitType.DAILY_QUOTA
        
        # Check requests per minute
        if self.usage_stats.requests_count >= self.config.requests_per_minute:
            return RateLimitType.REQUESTS_PER_MINUTE
        
        # Check tokens per minute
        if self.usage_stats.tokens_used >= self.config.tokens_per_minute:
            return RateLimitType.TOKENS_PER_MINUTE
        
        return None
    
    def _calculate_backoff_delay(self, attempt: int, base_delay: float = None) -> float:
        """Calculate exponential backoff delay with jitter"""
        if base_delay is None:
            base_delay = self.config.initial_delay
        
        # Exponential backoff with jitter
        delay = min(
            base_delay * (self.config.backoff_multiplier ** attempt),
            self.config.max_delay
        )
        
        # Add jitter (±25% of delay)
        jitter = delay * 0.25 * (random.random() - 0.5)
        return max(0.1, delay + jitter)
    
    def _detect_rate_limit_error(self, error: Exception) -> Optional[RateLimitType]:
        """Detect type of rate limiting error from exception"""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "too many requests" in error_str:
            if "per minute" in error_str:
                return RateLimitType.REQUESTS_PER_MINUTE
            elif "daily" in error_str or "quota" in error_str:
                return RateLimitType.DAILY_QUOTA
            else:
                return RateLimitType.TEMPORARY_OVERLOAD
        
        if "token" in error_str and "limit" in error_str:
            return RateLimitType.TOKENS_PER_MINUTE
        
        if "overload" in error_str or "capacity" in error_str:
            return RateLimitType.TEMPORARY_OVERLOAD
        
        return None
    
    def _get_backoff_delay_for_error(self, rate_limit_type: RateLimitType) -> float:
        """Get appropriate backoff delay for specific rate limit type"""
        if rate_limit_type == RateLimitType.DAILY_QUOTA:
            # Wait until next day
            now = datetime.now()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return (tomorrow - now).total_seconds()
        
        elif rate_limit_type == RateLimitType.REQUESTS_PER_MINUTE:
            # Wait until next minute
            now = datetime.now()
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            return (next_minute - now).total_seconds()
        
        elif rate_limit_type == RateLimitType.TOKENS_PER_MINUTE:
            # Wait until next minute
            now = datetime.now()
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            return (next_minute - now).total_seconds()
        
        else:
            # Temporary overload - use exponential backoff
            return self._calculate_backoff_delay(1, 30.0)  # Start with 30 seconds
    
    async def execute_with_rate_limiting(self, 
                                       api_func: Callable,
                                       *args,
                                       estimated_tokens: int = 1000,
                                       **kwargs) -> Any:
        """
        Execute API function with comprehensive rate limiting
        
        Args:
            api_func: The API function to call
            *args: Arguments for the API function
            estimated_tokens: Estimated token usage for this request
            **kwargs: Keyword arguments for the API function
            
        Returns:
            Result from the API function
            
        Raises:
            Exception: If all retries exhausted or daily quota exceeded
        """
        
        # Check circuit breaker
        if not self.circuit_breaker.can_proceed():
            raise Exception(f"Circuit breaker is OPEN for {self.provider} - service temporarily unavailable")
        
        # Check rate limits before attempting
        rate_limit_violation = self._check_rate_limits()
        if rate_limit_violation == RateLimitType.DAILY_QUOTA:
            raise Exception(f"Daily quota exceeded for {self.provider} - try again tomorrow")
        
        async with self.semaphore:  # Limit concurrent requests
            for attempt in range(self.config.max_retries + 1):
                try:
                    # Pre-flight checks
                    rate_limit_violation = self._check_rate_limits()
                    if rate_limit_violation:
                        delay = self._get_backoff_delay_for_error(rate_limit_violation)
                        if delay > 60:  # If delay is more than 1 minute, fail fast
                            raise Exception(f"Rate limit exceeded for {self.provider}: {rate_limit_violation.value}")
                        
                        logger.warning(f"Rate limit pre-check failed, waiting {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    
                    # Make the API call
                    start_time = time.time()
                    result = await api_func(*args, **kwargs)
                    
                    # Record successful usage
                    self.usage_stats.requests_count += 1
                    self.usage_stats.daily_requests += 1
                    self.usage_stats.tokens_used += estimated_tokens
                    self.usage_stats.daily_tokens += estimated_tokens
                    
                    self.circuit_breaker.record_success()
                    
                    logger.info(f"API call successful ({self.provider}): {time.time() - start_time:.2f}s")
                    return result
                
                except Exception as e:
                    # Detect rate limiting errors
                    rate_limit_type = self._detect_rate_limit_error(e)
                    
                    if rate_limit_type:
                        logger.warning(f"Rate limit hit ({self.provider}): {rate_limit_type.value}")
                        
                        if rate_limit_type == RateLimitType.DAILY_QUOTA:
                            self.circuit_breaker.record_failure()
                            raise Exception(f"Daily quota exceeded for {self.provider} - try again tomorrow")
                        
                        if attempt < self.config.max_retries:
                            delay = self._get_backoff_delay_for_error(rate_limit_type)
                            logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.config.max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            self.circuit_breaker.record_failure()
                            raise Exception(f"Max retries exceeded for {self.provider} rate limit: {rate_limit_type.value}")
                    
                    else:
                        # Non-rate-limit error
                        if attempt < self.config.max_retries:
                            delay = self._calculate_backoff_delay(attempt)
                            logger.info(f"API error, retrying in {delay:.1f}s: {str(e)}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            self.circuit_breaker.record_failure()
                            raise e
            
            # Should not reach here
            raise Exception(f"All retries exhausted for {self.provider}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        self._reset_counters_if_needed()
        
        return {
            "provider": self.provider,
            "current_usage": {
                "requests_this_minute": self.usage_stats.requests_count,
                "tokens_this_minute": self.usage_stats.tokens_used,
                "daily_requests": self.usage_stats.daily_requests,
                "daily_tokens": self.usage_stats.daily_tokens,
            },
            "limits": {
                "requests_per_minute": self.config.requests_per_minute,
                "tokens_per_minute": self.config.tokens_per_minute,
                "daily_quota": self.config.daily_quota,
            },
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "success_count": self.circuit_breaker.success_count,
            },
            "availability": {
                "can_proceed": self.circuit_breaker.can_proceed(),
                "next_reset": self.usage_stats.daily_reset + timedelta(days=1),
            }
        }

# Global rate limiters
_rate_limiters: Dict[str, AIRateLimiter] = {}

def get_rate_limiter(provider: str) -> AIRateLimiter:
    """Get or create rate limiter for provider"""
    if provider not in _rate_limiters:
        _rate_limiters[provider] = AIRateLimiter(provider)
    return _rate_limiters[provider]

def get_all_usage_stats() -> Dict[str, Any]:
    """Get usage statistics for all providers"""
    return {
        provider: limiter.get_usage_stats() 
        for provider, limiter in _rate_limiters.items()
    } 