"""Unit tests for the OpenAPI utility classes."""

import unittest
from unittest.mock import patch, MagicMock, call
import requests
import time

from src.openapi.utils import RetryHandler, RateLimiter
from src.openapi.models import RateLimitConfig, RetryConfig


class TestRateLimiter(unittest.TestCase):
    """Tests for the RateLimiter class."""

    def setUp(self):
        """Set up the test fixture."""
        self.config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            requests_per_hour=None,
            requests_per_day=None,
        )
        self.rate_limiter = RateLimiter(self.config)

    @patch("time.sleep")
    def test_rate_limiting(self, mock_sleep):
        """Test that rate limiting works when enabled."""
        # Reset the rate limiter state
        self.rate_limiter.minute_tokens = 5  # Set remaining tokens to 5

        # Make requests that would exceed the rate limit
        for _ in range(10):
            # Directly call the rate limiting logic that would be used before making a request
            if not self.rate_limiter.can_request():
                wait_time = self.rate_limiter.wait_time_seconds()
                time.sleep(wait_time)
            self.rate_limiter.consume_token()

        # Verify sleep was called to enforce rate limiting
        self.assertTrue(mock_sleep.called)

    def test_disabled_rate_limiting(self):
        """Test that rate limiting is skipped when disabled."""
        # Disable rate limiting
        self.rate_limiter.config.enabled = False

        # Set tokens to 0
        self.rate_limiter.minute_tokens = 0

        # Patch sleep to verify it's not called
        with patch("time.sleep") as mock_sleep:
            # Even with 0 tokens, can_request should return True when disabled
            self.assertTrue(self.rate_limiter.can_request())

            # Wait time should be 0 when disabled
            self.assertEqual(self.rate_limiter.wait_time_seconds(), 0)

            # Verify sleep was not called
            mock_sleep.assert_not_called()

    def test_token_tracking(self):
        """Test that tokens are properly tracked."""
        # Initialize tokens
        self.rate_limiter.minute_tokens = 10

        # Consume tokens
        for _ in range(5):
            self.rate_limiter.consume_token()

        # Verify tokens were decremented
        self.assertEqual(self.rate_limiter.minute_tokens, 5)


class TestRetryHandler(unittest.TestCase):
    """Tests for the RetryHandler class."""

    def setUp(self):
        """Set up the test fixture."""
        self.config = RetryConfig(
            enabled=True,
            max_retries=3,
            retry_on_status_codes=[429, 500, 502, 503, 504],
            backoff_factor=0.5,
        )
        self.retry_handler = RetryHandler(self.config)

    def test_should_retry(self):
        """Test the should_retry method."""
        # Should retry for 500 status with attempt < max_retries
        self.assertTrue(self.retry_handler.should_retry(status_code=500, attempt=1))

        # Should not retry after max_retries is reached
        self.assertFalse(self.retry_handler.should_retry(status_code=500, attempt=3))

        # Should not retry for non-retryable status code
        self.assertFalse(self.retry_handler.should_retry(status_code=400, attempt=1))

    def test_get_backoff_time(self):
        """Test calculation of backoff time between retries."""
        # First retry: backoff_factor * (2 ** 0)
        self.assertEqual(self.retry_handler.get_backoff_time(0), 0.5)

        # Second retry: backoff_factor * (2 ** 1)
        self.assertEqual(self.retry_handler.get_backoff_time(1), 1.0)

        # Third retry: backoff_factor * (2 ** 2)
        self.assertEqual(self.retry_handler.get_backoff_time(2), 2.0)


if __name__ == "__main__":
    unittest.main()
