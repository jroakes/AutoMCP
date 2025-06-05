import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.openapi.utils import RateLimiter, RetryHandler, PaginationHandler
from src.openapi.models import RateLimitConfig, RetryConfig, PaginationConfig


class TestRateLimiter(unittest.TestCase):
    def test_rate_limiting_enabled(self):
        """Test rate limiting when enabled."""
        config = RateLimitConfig(requests_per_minute=60, enabled=True)
        limiter = RateLimiter(config)
        
        # First request should be allowed
        self.assertTrue(limiter.can_request())
        
    def test_rate_limiting_disabled(self):
        """Test that disabled rate limiting allows all requests."""
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)
        
        # Should always be allowed when disabled
        self.assertTrue(limiter.can_request())

    def test_wait_time_calculation(self):
        """Test wait time calculation for rate limiting."""
        config = RateLimitConfig(requests_per_minute=1, enabled=True)
        limiter = RateLimiter(config)
        
        # Consume all tokens
        limiter.consume_token()
        
        # Should have a positive wait time
        wait_time = limiter.wait_time_seconds()
        self.assertGreaterEqual(wait_time, 0)


class TestRetryHandler(unittest.TestCase):
    def test_retry_enabled_with_retryable_status(self):
        """Test that retry is enabled for retryable status codes."""
        config = RetryConfig(retry_on_status_codes=[429, 500], enabled=True)
        handler = RetryHandler(config)
        
        self.assertTrue(handler.should_retry(429, 0))
        self.assertTrue(handler.should_retry(500, 0))
        
    def test_retry_disabled(self):
        """Test that retry is disabled when configuration is disabled."""
        config = RetryConfig(enabled=False)
        handler = RetryHandler(config)
        
        # Should not retry even for normally retryable status codes
        self.assertFalse(handler.should_retry(429, 0))
        self.assertFalse(handler.should_retry(500, 0))

    def test_non_retryable_status_codes(self):
        """Test that non-retryable status codes don't trigger retries."""
        config = RetryConfig(retry_on_status_codes=[429, 500], enabled=True)
        handler = RetryHandler(config)
        
        self.assertFalse(handler.should_retry(200, 0))
        self.assertFalse(handler.should_retry(404, 0))
        self.assertFalse(handler.should_retry(401, 0))

    def test_max_retries_limit(self):
        """Test that max retries limit is respected."""
        config = RetryConfig(retry_on_status_codes=[429], max_retries=2, enabled=True)
        handler = RetryHandler(config)
        
        # Should retry on first attempts
        self.assertTrue(handler.should_retry(429, 0))
        self.assertTrue(handler.should_retry(429, 1))
        
        # Should not retry after max attempts
        self.assertFalse(handler.should_retry(429, 2))

    def test_backoff_time_calculation(self):
        """Test exponential backoff time calculation."""
        config = RetryConfig(backoff_factor=0.5, enabled=True)
        handler = RetryHandler(config)
        
        # Test exponential backoff
        self.assertEqual(handler.get_backoff_time(0), 0.5)  # 0.5 * 2^0
        self.assertEqual(handler.get_backoff_time(1), 1.0)  # 0.5 * 2^1
        self.assertEqual(handler.get_backoff_time(2), 2.0)  # 0.5 * 2^2


class TestPaginationHandler(unittest.TestCase):
    def test_link_header_parsing(self):
        """Test parsing of Link header for pagination."""
        config = PaginationConfig(enabled=True)
        handler = PaginationHandler(config)
        
        # Test GitHub-style Link header
        link_header = '<https://api.github.com/user/repos?page=2>; rel="next", <https://api.github.com/user/repos?page=5>; rel="last"'
        links = handler.parse_link_header(link_header)
        
        self.assertIn("next", links)
        self.assertIn("https://api.github.com/user/repos?page=2", links["next"])

    def test_cursor_extraction(self):
        """Test cursor extraction from response data."""
        config = PaginationConfig(cursor_response_field="data.nextToken", enabled=True)
        handler = PaginationHandler(config)
        
        # Test nested cursor extraction
        response_data = {"data": {"nextToken": "abc123", "items": []}}
        cursor = handler.extract_next_cursor(response_data)
        
        self.assertEqual(cursor, "abc123")

    def test_results_combination(self):
        """Test combining results from multiple pages."""
        config = PaginationConfig(results_field="items", enabled=True)
        handler = PaginationHandler(config)
        
        responses = [
            {"items": [1, 2, 3]},
            {"items": [4, 5, 6]},
            {"items": [7, 8, 9]}
        ]
        
        combined = handler.combine_results(responses)
        
        self.assertEqual(len(combined["items"]), 9)
        self.assertEqual(combined["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])


if __name__ == '__main__':
    unittest.main() 