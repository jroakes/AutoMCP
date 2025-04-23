"""Utility classes for OpenAPI tools."""

import time
import logging
from typing import Dict, List, Optional, Any
import threading

from .models import RateLimitConfig, RetryConfig, PaginationConfig

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""

    def __init__(self, config: RateLimitConfig):
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.tokens_per_minute = config.requests_per_minute
        self.tokens_per_hour = (
            config.requests_per_hour or config.requests_per_minute * 60
        )
        self.tokens_per_day = (
            config.requests_per_day or config.requests_per_hour * 24
            if config.requests_per_hour
            else config.requests_per_minute * 60 * 24
        )

        # Initialize token buckets
        self.minute_tokens = self.tokens_per_minute
        self.hour_tokens = self.tokens_per_hour
        self.day_tokens = self.tokens_per_day

        # Last refill timestamps
        self.last_minute_refill = time.time()
        self.last_hour_refill = time.time()
        self.last_day_refill = time.time()

        # Lock for thread safety
        self.lock = threading.RLock()

    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()

        # Refill minute tokens
        elapsed_minutes = (now - self.last_minute_refill) / 60
        if elapsed_minutes > 0:
            self.minute_tokens = min(
                self.tokens_per_minute,
                self.minute_tokens + int(elapsed_minutes * self.tokens_per_minute),
            )
            self.last_minute_refill = now

        # Refill hour tokens
        elapsed_hours = (now - self.last_hour_refill) / 3600
        if elapsed_hours > 0:
            self.hour_tokens = min(
                self.tokens_per_hour,
                self.hour_tokens + int(elapsed_hours * self.tokens_per_hour),
            )
            self.last_hour_refill = now

        # Refill day tokens
        elapsed_days = (now - self.last_day_refill) / 86400
        if elapsed_days > 0:
            self.day_tokens = min(
                self.tokens_per_day,
                self.day_tokens + int(elapsed_days * self.tokens_per_day),
            )
            self.last_day_refill = now

    def can_request(self) -> bool:
        """Check if a request can be made based on rate limits.

        Returns:
            True if request is allowed, False otherwise
        """
        if not self.config.enabled:
            return True

        with self.lock:
            self._refill_tokens()

            if self.minute_tokens < 1 or self.hour_tokens < 1 or self.day_tokens < 1:
                return False

            return True

    def consume_token(self):
        """Consume a token for a request."""
        if not self.config.enabled:
            return

        with self.lock:
            self.minute_tokens -= 1
            self.hour_tokens -= 1
            self.day_tokens -= 1

    def wait_time_seconds(self) -> float:
        """Calculate wait time until next token is available.

        Returns:
            Seconds to wait before next request
        """
        if not self.config.enabled:
            return 0

        with self.lock:
            self._refill_tokens()

            if self.can_request():
                return 0

            # Calculate time until next token becomes available
            time_to_next_minute_token = (
                0 if self.minute_tokens > 0 else 60 / self.tokens_per_minute
            )
            time_to_next_hour_token = (
                0 if self.hour_tokens > 0 else 3600 / self.tokens_per_hour
            )
            time_to_next_day_token = (
                0 if self.day_tokens > 0 else 86400 / self.tokens_per_day
            )

            return max(
                time_to_next_minute_token,
                time_to_next_hour_token,
                time_to_next_day_token,
            )


class RetryHandler:
    """Handler for retrying API requests with exponential backoff."""

    def __init__(self, config: RetryConfig):
        """Initialize the retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config

    def should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if a request should be retried.

        Args:
            status_code: HTTP status code from the response
            attempt: Current attempt number (0-based)

        Returns:
            True if request should be retried, False otherwise
        """
        if not self.config.enabled:
            return False

        if attempt >= self.config.max_retries:
            return False

        return status_code in self.config.retry_on_status_codes

    def get_backoff_time(self, attempt: int) -> float:
        """Calculate backoff time for a retry attempt.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Time to wait in seconds before the next attempt
        """
        return self.config.backoff_factor * (2**attempt)


class PaginationHandler:
    """Handles pagination for API responses.

    Supports multiple pagination mechanisms:
    - Link headers (RFC 5988)
    - Cursor-based pagination
    - Offset/limit-based pagination
    - Page-based pagination
    """

    def __init__(self, config: "PaginationConfig"):
        """Initialize the pagination handler.

        Args:
            config: Pagination configuration
        """
        self.config = config

    def parse_link_header(self, link_header: Optional[str]) -> Dict[str, str]:
        """Parse a Link header (RFC 5988) into a dictionary of relation types and URLs.

        Args:
            link_header: Link header value from HTTP response

        Returns:
            Dictionary of relation types (e.g., 'next', 'prev') to URLs
        """
        if not link_header:
            return {}

        links = {}
        for link in link_header.split(","):
            segments = link.split(";")
            if len(segments) < 2:
                continue

            url = segments[0].strip().strip("<>")
            for segment in segments[1:]:
                if "rel=" in segment:
                    rel = segment.split("=")[1].strip().strip("\"'")
                    links[rel] = url
                    break

        return links

    def extract_next_cursor(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extract the next cursor/token from a response for cursor-based pagination.

        Args:
            response_data: Response data from API

        Returns:
            Next cursor value or None if not found
        """
        if not self.config.cursor_response_field:
            return None

        # Handle nested fields with dot notation
        if "." in self.config.cursor_response_field:
            parts = self.config.cursor_response_field.split(".")
            value = response_data
            for part in parts:
                if not isinstance(value, dict) or part not in value:
                    return None
                value = value[part]
            return value

        # Simple case - direct field access
        return response_data.get(self.config.cursor_response_field)

    def combine_results(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine paginated responses into a single response.

        Args:
            responses: List of response data from paginated API calls

        Returns:
            Combined response with merged results
        """
        if not responses:
            return {}

        # Use the first response as the base
        combined_response = responses[0].copy()

        # If a results field is specified, merge the results arrays
        if self.config.results_field and self.config.results_field in combined_response:
            combined_results = []

            # Extract and combine results from all responses
            for response in responses:
                if isinstance(response, dict) and self.config.results_field in response:
                    results = response[self.config.results_field]
                    if isinstance(results, list):
                        combined_results.extend(results)

            # Replace the results in the combined response
            combined_response[self.config.results_field] = combined_results

        return combined_response

    def prepare_next_page_params(
        self,
        original_params: Dict[str, Any],
        current_page: int,
        response_data: Dict[str, Any],
        response_headers: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Prepare parameters for the next page based on pagination mechanism.

        Args:
            original_params: Original request parameters
            current_page: Current page number (0-based)
            response_data: Response data from current page
            response_headers: Response headers from current page

        Returns:
            Parameters for next page request or None if no next page
        """
        if not self.config.enabled or current_page >= self.config.max_pages - 1:
            return None

        params = original_params.copy()

        # Check pagination mechanism
        mechanism = self.config.mechanism.lower()

        # Auto-detect pagination mechanism
        if mechanism == "auto":
            # Try link header first
            if "link" in response_headers:
                links = self.parse_link_header(response_headers.get("link"))
                if "next" in links:
                    # Return the full URL instead of params, as it's a complete URL
                    return {"_pagination_next_url": links["next"]}

            # Try cursor-based pagination
            next_cursor = self.extract_next_cursor(response_data)
            if next_cursor and self.config.cursor_param:
                params[self.config.cursor_param] = next_cursor
                return params

            # Try offset/limit pagination
            if self.config.offset_param and self.config.limit_param:
                if (
                    self.config.offset_param in params
                    and self.config.limit_param in params
                ):
                    offset = int(params[self.config.offset_param])
                    limit = int(params[self.config.limit_param])
                    params[self.config.offset_param] = str(offset + limit)
                    return params

            # Try page-based pagination
            if self.config.page_param:
                if self.config.page_param in params:
                    params[self.config.page_param] = str(
                        int(params[self.config.page_param]) + 1
                    )
                    return params
                else:
                    params[self.config.page_param] = "2"  # Start with page 2
                    return params

            return None

        # Link header-based pagination (RFC 5988)
        elif mechanism == "link":
            if "link" in response_headers:
                links = self.parse_link_header(response_headers.get("link"))
                if "next" in links:
                    return {"_pagination_next_url": links["next"]}
            return None

        # Cursor-based pagination
        elif mechanism == "cursor":
            next_cursor = self.extract_next_cursor(response_data)
            if next_cursor and self.config.cursor_param:
                params[self.config.cursor_param] = next_cursor
                return params
            return None

        # Offset/limit-based pagination
        elif mechanism == "offset":
            if self.config.offset_param and self.config.limit_param:
                if (
                    self.config.offset_param in params
                    and self.config.limit_param in params
                ):
                    offset = int(params[self.config.offset_param])
                    limit = int(params[self.config.limit_param])
                    params[self.config.offset_param] = str(offset + limit)
                    return params
            return None

        # Page-based pagination
        elif mechanism == "page":
            if self.config.page_param:
                if self.config.page_param in params:
                    params[self.config.page_param] = str(
                        int(params[self.config.page_param]) + 1
                    )
                    return params
                else:
                    params[self.config.page_param] = "2"  # Start with page 2
                    return params
            return None

        return None
