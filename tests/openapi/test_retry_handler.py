import unittest

from src.openapi.utils import RetryHandler
from src.openapi.models import RetryConfig


class TestRetryHandler(unittest.TestCase):
    """Tests for the RetryHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.default_config = RetryConfig()
        self.retry_handler = RetryHandler(self.default_config)

    def test_init(self):
        """Test initialization of RetryHandler."""
        # Test with default config
        self.assertEqual(self.retry_handler.config.max_retries, 3)
        self.assertEqual(self.retry_handler.config.backoff_factor, 0.5)
        self.assertEqual(
            self.retry_handler.config.retry_on_status_codes, [429, 500, 502, 503, 504]
        )
        self.assertTrue(self.retry_handler.config.enabled)

        # Test with custom config
        custom_config = RetryConfig(
            max_retries=5,
            backoff_factor=1.0,
            retry_on_status_codes=[429, 500],
            enabled=False,
        )
        retry_handler = RetryHandler(custom_config)
        self.assertEqual(retry_handler.config.max_retries, 5)
        self.assertEqual(retry_handler.config.backoff_factor, 1.0)
        self.assertEqual(retry_handler.config.retry_on_status_codes, [429, 500])
        self.assertFalse(retry_handler.config.enabled)

    def test_should_retry_with_retryable_status(self):
        """Test should_retry method with status codes that should be retried."""
        # Test with each retryable status code
        for status_code in self.default_config.retry_on_status_codes:
            self.assertTrue(
                self.retry_handler.should_retry(status_code=status_code, attempt=0),
                f"Failed for status code {status_code}",
            )

    def test_should_retry_with_non_retryable_status(self):
        """Test should_retry method with status codes that should not be retried."""
        non_retryable_status_codes = [400, 401, 403, 404, 405, 200, 201, 204]
        for status_code in non_retryable_status_codes:
            self.assertFalse(
                self.retry_handler.should_retry(status_code=status_code, attempt=0),
                f"Failed for status code {status_code}",
            )

    def test_should_retry_based_on_attempt_count(self):
        """Test should_retry method with different attempt counts."""
        # With attempt < max_retries
        self.assertTrue(self.retry_handler.should_retry(status_code=500, attempt=0))
        self.assertTrue(self.retry_handler.should_retry(status_code=500, attempt=1))
        self.assertTrue(self.retry_handler.should_retry(status_code=500, attempt=2))

        # With attempt >= max_retries
        self.assertFalse(self.retry_handler.should_retry(status_code=500, attempt=3))
        self.assertFalse(self.retry_handler.should_retry(status_code=500, attempt=4))

    def test_should_retry_when_disabled(self):
        """Test should_retry method when retries are disabled."""
        # Create a retry handler with disabled retries
        disabled_config = RetryConfig(enabled=False)
        retry_handler = RetryHandler(disabled_config)

        # Test with retryable status code
        self.assertFalse(retry_handler.should_retry(status_code=500, attempt=0))

    def test_get_backoff_time(self):
        """Test get_backoff_time method."""
        # Test with different attempt values
        self.assertEqual(self.retry_handler.get_backoff_time(0), 0.5)  # 0.5 * (2 ** 0)
        self.assertEqual(self.retry_handler.get_backoff_time(1), 1.0)  # 0.5 * (2 ** 1)
        self.assertEqual(self.retry_handler.get_backoff_time(2), 2.0)  # 0.5 * (2 ** 2)
        self.assertEqual(self.retry_handler.get_backoff_time(3), 4.0)  # 0.5 * (2 ** 3)

        # Test with a different backoff factor
        custom_config = RetryConfig(backoff_factor=1.0)
        retry_handler = RetryHandler(custom_config)
        self.assertEqual(retry_handler.get_backoff_time(0), 1.0)  # 1.0 * (2 ** 0)
        self.assertEqual(retry_handler.get_backoff_time(1), 2.0)  # 1.0 * (2 ** 1)
        self.assertEqual(retry_handler.get_backoff_time(2), 4.0)  # 1.0 * (2 ** 2)


if __name__ == "__main__":
    unittest.main()
