import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import time
import asyncio # For RateLimiter async tests
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import httpx # For RetryHandler tenacity_kwargs test with httpx.HTTPStatusError
import tenacity # For RetryHandler tenacity_kwargs test

from src.openapi.utils import RateLimiter, RetryHandler, PaginationHandler
from src.openapi.models import RateLimitConfig, RetryConfig, PaginationConfig


class TestRateLimiter(unittest.IsolatedAsyncioTestCase): # IsolatedAsyncioTestCase for async methods

    def test_init_defaults_from_config(self):
        config = RateLimitConfig(requests_per_minute=30, requests_per_hour=300, requests_per_day=3000)
        limiter = RateLimiter(config)
        self.assertEqual(limiter.tokens_per_minute, 30)
        self.assertEqual(limiter.tokens_per_hour, 300)
        self.assertEqual(limiter.tokens_per_day, 3000)
        self.assertEqual(limiter.minute_tokens, 30)
        self.assertEqual(limiter.hour_tokens, 300)
        self.assertEqual(limiter.day_tokens, 3000)

    def test_init_calculates_missing_hourly_daily(self):
        config = RateLimitConfig(requests_per_minute=10) # Hour/Day should be calculated
        limiter = RateLimiter(config)
        self.assertEqual(limiter.tokens_per_hour, 10 * 60)
        self.assertEqual(limiter.tokens_per_day, 10 * 60 * 24)

    @patch('time.time')
    def test_refill_tokens(self, mock_time):
        config = RateLimitConfig(requests_per_minute=60)
        limiter = RateLimiter(config)
        initial_time = 1000.0
        limiter.last_minute_refill = initial_time
        limiter.last_hour_refill = initial_time
        limiter.last_day_refill = initial_time
        limiter.minute_tokens = 0
        limiter.hour_tokens = 0
        limiter.day_tokens = 0

        # Simulate 1 minute passing
        # Ensure mock_time returns sequential values for calculations within _refill_tokens
        mock_time.side_effect = [initial_time + 60.0] # Need value for 'now' calculation
        limiter._refill_tokens()
        self.assertEqual(limiter.minute_tokens, 60)

    def test_can_request_and_consume(self):
        config = RateLimitConfig(requests_per_minute=1, enabled=True)
        limiter = RateLimiter(config)

        self.assertTrue(limiter.can_request())
        limiter.consume_token()
        self.assertEqual(limiter.minute_tokens, 0)
        self.assertFalse(limiter.can_request()) # No more tokens for the minute

    def test_disabled_limiter(self):
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)
        self.assertTrue(limiter.can_request())
        limiter.consume_token() # Should do nothing
        self.assertTrue(limiter.can_request()) # Still can request
        self.assertEqual(limiter.wait_time_seconds(), 0)

    async def test_consume_token_async_disabled(self):
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)
        mock_sleep = AsyncMock()
        with patch('asyncio.sleep', mock_sleep):
            await limiter.consume_token_async()
            mock_sleep.assert_not_awaited()
        # Tokens shouldn't change for disabled limiter
        self.assertEqual(limiter.minute_tokens, config.requests_per_minute)


class TestRetryHandler(unittest.TestCase):
    def test_should_retry_true(self):
        config = RetryConfig(max_retries=3, retry_on_status_codes=[500, 503])
        handler = RetryHandler(config)
        self.assertTrue(handler.should_retry(status_code=500, attempt=0))
        self.assertTrue(handler.should_retry(status_code=503, attempt=2))

    def test_should_retry_false(self):
        config = RetryConfig(max_retries=3, retry_on_status_codes=[500])
        handler = RetryHandler(config)
        self.assertFalse(handler.should_retry(status_code=404, attempt=0)) # Wrong status code
        self.assertFalse(handler.should_retry(status_code=500, attempt=3)) # Exceeded max_retries
        # Test with a new handler for enabled=False
        disabled_handler = RetryHandler(RetryConfig(enabled=False))
        self.assertFalse(disabled_handler.should_retry(status_code=500, attempt=0))

    def test_get_backoff_time(self):
        config = RetryConfig(backoff_factor=0.5)
        handler = RetryHandler(config)
        self.assertEqual(handler.get_backoff_time(attempt=0), 0.5 * (2**0)) # 0.5s
        self.assertEqual(handler.get_backoff_time(attempt=1), 0.5 * (2**1)) # 1.0s
        self.assertEqual(handler.get_backoff_time(attempt=2), 0.5 * (2**2)) # 2.0s

    def test_tenacity_kwargs_disabled(self):
        handler = RetryHandler(RetryConfig(enabled=False))
        kwargs = handler.tenacity_kwargs()
        self.assertIsInstance(kwargs['stop'], tenacity.stop_after_attempt)
        self.assertEqual(kwargs['stop'].max_attempt_number, 1)
        self.assertTrue(kwargs['reraise'])

    def test_tenacity_kwargs_enabled(self):
        config = RetryConfig(enabled=True, max_retries=5, backoff_factor=0.2, retry_on_status_codes=[429, 503])
        handler = RetryHandler(config)
        kwargs = handler.tenacity_kwargs()
        
        self.assertIsInstance(kwargs['stop'], tenacity.stop_after_attempt)
        self.assertEqual(kwargs['stop'].max_attempt_number, 5)
        
        self.assertIsInstance(kwargs['wait'], tenacity.wait_exponential)
        self.assertEqual(kwargs['wait'].multiplier, 0.2)

        self.assertTrue(kwargs['reraise'])
        self.assertTrue(callable(kwargs['retry'].predicate))

        # Test the retry predicate
        retry_predicate = kwargs['retry'].predicate
        mock_exc_retryable = MagicMock(spec=httpx.HTTPStatusError)
        mock_exc_retryable.response = MagicMock(status_code=429)
        self.assertTrue(retry_predicate(mock_exc_retryable))

        mock_exc_not_retryable_status = MagicMock(spec=httpx.HTTPStatusError)
        mock_exc_not_retryable_status.response = MagicMock(status_code=404)
        self.assertFalse(retry_predicate(mock_exc_not_retryable_status))

        mock_exc_other = ValueError("Some other error")
        self.assertFalse(retry_predicate(mock_exc_other))

class TestPaginationHandler(unittest.TestCase):
    def test_parse_link_header(self):
        handler = PaginationHandler(PaginationConfig())
        link_header = '<https://api.example.com/items?page=2>; rel="next", <https://api.example.com/items?page=1>; rel="prev"'
        links = handler.parse_link_header(link_header)
        self.assertEqual(links["next"], "https://api.example.com/items?page=2")
        self.assertEqual(links["prev"], "https://api.example.com/items?page=1")
        self.assertEqual(handler.parse_link_header(None), {})

    def test_extract_next_cursor(self):
        config_simple = PaginationConfig(cursor_response_field="nextPageToken")
        handler_simple = PaginationHandler(config_simple)
        response_simple = {"items": [], "nextPageToken": "token123"}
        self.assertEqual(handler_simple.extract_next_cursor(response_simple), "token123")

        config_nested = PaginationConfig(cursor_response_field="pagination.next_cursor")
        handler_nested = PaginationHandler(config_nested)
        response_nested = {"data": [], "pagination": {"next_cursor": "abc"}}
        self.assertEqual(handler_nested.extract_next_cursor(response_nested), "abc")
        self.assertIsNone(handler_nested.extract_next_cursor({"data": []})) # Field not found

    def test_combine_results(self):
        config = PaginationConfig(results_field="items")
        handler = PaginationHandler(config)
        responses = [
            {"items": [1, 2], "other_data": "A"},
            {"items": [3, 4], "other_data": "B"} # other_data from first response is kept
        ]
        combined = handler.combine_results(responses)
        self.assertEqual(combined["items"], [1, 2, 3, 4])
        self.assertEqual(combined["other_data"], "A") # from the first response
        self.assertEqual(handler.combine_results([]), {})

    def test_prepare_next_page_params_disabled(self):
        handler = PaginationHandler(PaginationConfig(enabled=False))
        next_params = handler.prepare_next_page_params({}, 0, {}, {})
        self.assertIsNone(next_params)

    def test_prepare_next_page_params_max_pages_reached(self):
        handler = PaginationHandler(PaginationConfig(max_pages=1))
        next_params = handler.prepare_next_page_params({}, 0, {}, {}) # current_page 0, max_pages 1, so next is page 1 >= max_pages
        self.assertIsNone(next_params)

    # --- Auto Detection Tests --- 
    def test_prepare_next_auto_link_header(self):
        config = PaginationConfig(mechanism="auto")
        handler = PaginationHandler(config)
        headers = {"link": '<http://next.url>; rel="next"'}
        next_params = handler.prepare_next_page_params({}, 0, {}, headers)
        self.assertEqual(next_params, {"_pagination_next_url": "http://next.url"})

    def test_prepare_next_auto_cursor(self):
        config = PaginationConfig(mechanism="auto", cursor_param="c", cursor_response_field="next_c")
        handler = PaginationHandler(config)
        response_data = {"next_c": "cursor_val"}
        next_params = handler.prepare_next_page_params({"c": "old"}, 0, response_data, {})
        self.assertEqual(next_params, {"c": "cursor_val"})

    def test_prepare_next_auto_offset_limit(self):
        config = PaginationConfig(mechanism="auto", offset_param="offset", limit_param="limit")
        handler = PaginationHandler(config)
        original_params = {"offset": "0", "limit": "10"}
        next_params = handler.prepare_next_page_params(original_params, 0, {}, {})
        self.assertEqual(next_params, {"offset": "10", "limit": "10"})

    def test_prepare_next_auto_page_param_exists(self):
        config = PaginationConfig(mechanism="auto", page_param="page_num")
        handler = PaginationHandler(config)
        original_params = {"page_num": "1"}
        next_params = handler.prepare_next_page_params(original_params, 0, {}, {})
        self.assertEqual(next_params, {"page_num": "2"})

    def test_prepare_next_auto_page_param_not_exists(self):
        config = PaginationConfig(mechanism="auto", page_param="page")
        handler = PaginationHandler(config)
        next_params = handler.prepare_next_page_params({}, 0, {}, {})
        self.assertEqual(next_params, {"page": "2"})
    
    # --- Explicit Mechanism Tests ---
    def test_prepare_next_explicit_link(self):
        config = PaginationConfig(mechanism="link")
        handler = PaginationHandler(config)
        headers = {"link": '<http://next.url>; rel="next"'}
        next_params = handler.prepare_next_page_params({}, 0, {}, headers)
        self.assertEqual(next_params, {"_pagination_next_url": "http://next.url"})
        self.assertIsNone(handler.prepare_next_page_params({}, 0, {}, {})) # No link header

    def test_prepare_next_explicit_cursor(self):
        config = PaginationConfig(mechanism="cursor", cursor_param="cursor", cursor_response_field="data.next_cursor")
        handler = PaginationHandler(config)
        response_data = {"data": {"next_cursor": "xyz"}}
        next_params = handler.prepare_next_page_params({}, 0, response_data, {})
        self.assertEqual(next_params, {"cursor": "xyz"})
        self.assertIsNone(handler.prepare_next_page_params({}, 0, {}, {})) # No cursor in response

    def test_prepare_next_explicit_offset(self):
        config = PaginationConfig(mechanism="offset", offset_param="start", limit_param="count")
        handler = PaginationHandler(config)
        original_params = {"start": "10", "count": "5"}
        next_params = handler.prepare_next_page_params(original_params, 0, {}, {})
        self.assertEqual(next_params, {"start": "15", "count": "5"})
        self.assertIsNone(handler.prepare_next_page_params({},0,{},{})) # Missing params

    def test_prepare_next_explicit_page(self):
        config = PaginationConfig(mechanism="page", page_param="p")
        handler = PaginationHandler(config)
        original_params = {"p": "3"}
        next_params = handler.prepare_next_page_params(original_params, 0, {}, {})
        self.assertEqual(next_params, {"p": "4"})
        # Test starting from no page param (assumes page 1 was fetched)
        next_params_start = handler.prepare_next_page_params({}, 0, {}, {})
        self.assertEqual(next_params_start, {"p": "2"})

if __name__ == '__main__':
    unittest.main() 