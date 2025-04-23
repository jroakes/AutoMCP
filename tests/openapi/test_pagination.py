"""Tests for the OpenAPI pagination functionality."""

import unittest
from unittest.mock import MagicMock, patch

from src.openapi.models import PaginationConfig
from src.openapi.utils import PaginationHandler


class TestPaginationHandler(unittest.TestCase):
    """Tests for the PaginationHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = PaginationConfig()
        self.handler = PaginationHandler(self.config)

    def test_parse_link_header(self):
        """Test parsing Link headers."""
        # Simple link header
        link_header = '<https://api.example.com/items?page=2>; rel="next", <https://api.example.com/items?page=5>; rel="last"'
        parsed = self.handler.parse_link_header(link_header)
        self.assertEqual(parsed["next"], "https://api.example.com/items?page=2")
        self.assertEqual(parsed["last"], "https://api.example.com/items?page=5")

        # Empty link header
        self.assertEqual(self.handler.parse_link_header(""), {})
        self.assertEqual(self.handler.parse_link_header(None), {})

        # Malformed link header
        malformed = "<https://api.example.com/items?page=2>"  # Missing rel
        self.assertEqual(self.handler.parse_link_header(malformed), {})

    def test_extract_next_cursor(self):
        """Test extracting next cursor from response data."""
        # Simple cursor
        self.config.cursor_response_field = "next_cursor"
        response = {"next_cursor": "abc123", "items": []}
        self.assertEqual(self.handler.extract_next_cursor(response), "abc123")

        # Nested cursor
        self.config.cursor_response_field = "pagination.next_cursor"
        response = {"pagination": {"next_cursor": "def456"}, "items": []}
        self.assertEqual(self.handler.extract_next_cursor(response), "def456")

        # Missing cursor
        response = {"items": []}
        self.assertIsNone(self.handler.extract_next_cursor(response))

    def test_combine_results(self):
        """Test combining paginated results."""
        self.config.results_field = "items"

        # Multiple pages with items
        responses = [
            {"items": [1, 2, 3], "meta": {"page": 1}},
            {"items": [4, 5, 6], "meta": {"page": 2}},
            {"items": [7, 8, 9], "meta": {"page": 3}},
        ]
        combined = self.handler.combine_results(responses)
        self.assertEqual(combined["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(
            combined["meta"], {"page": 1}
        )  # Keeps first response's metadata

        # Empty list
        self.assertEqual(self.handler.combine_results([]), {})

        # No results field
        self.config.results_field = None
        combined = self.handler.combine_results(responses)
        self.assertEqual(combined, responses[0])

    def test_next_page_params_link(self):
        """Test preparing next page parameters for Link-based pagination."""
        self.config.mechanism = "link"

        # With Link header
        params = {}
        headers = {"link": '<https://api.example.com/items?page=2>; rel="next"'}
        next_params = self.handler.prepare_next_page_params(params, 0, {}, headers)
        self.assertEqual(
            next_params["_pagination_next_url"], "https://api.example.com/items?page=2"
        )

        # No next link
        headers = {"link": '<https://api.example.com/items?page=5>; rel="last"'}
        self.assertIsNone(self.handler.prepare_next_page_params(params, 0, {}, headers))

    def test_next_page_params_cursor(self):
        """Test preparing next page parameters for cursor-based pagination."""
        self.config.mechanism = "cursor"
        self.config.cursor_param = "cursor"
        self.config.cursor_response_field = "next_cursor"

        # With next cursor
        params = {"limit": "10"}
        response = {"next_cursor": "abc123", "items": []}
        next_params = self.handler.prepare_next_page_params(params, 0, response, {})
        self.assertEqual(next_params["cursor"], "abc123")
        self.assertEqual(next_params["limit"], "10")

        # No next cursor
        response = {"items": []}
        self.assertIsNone(
            self.handler.prepare_next_page_params(params, 0, response, {})
        )

    def test_next_page_params_offset(self):
        """Test preparing next page parameters for offset-based pagination."""
        self.config.mechanism = "offset"
        self.config.offset_param = "offset"
        self.config.limit_param = "limit"

        # With offset and limit
        params = {"offset": "0", "limit": "10"}
        next_params = self.handler.prepare_next_page_params(params, 0, {}, {})
        self.assertEqual(next_params["offset"], "10")
        self.assertEqual(next_params["limit"], "10")

        # Invalid offset/limit
        params = {"offset": "invalid", "limit": "10"}
        with self.assertRaises(ValueError):
            self.handler.prepare_next_page_params(params, 0, {}, {})

    def test_next_page_params_page(self):
        """Test preparing next page parameters for page-based pagination."""
        self.config.mechanism = "page"
        self.config.page_param = "page"

        # With page
        params = {"page": "1", "per_page": "10"}
        next_params = self.handler.prepare_next_page_params(params, 0, {}, {})
        self.assertEqual(next_params["page"], "2")
        self.assertEqual(next_params["per_page"], "10")

        # Without page (start with page 2)
        params = {"per_page": "10"}
        next_params = self.handler.prepare_next_page_params(params, 0, {}, {})
        self.assertEqual(next_params["page"], "2")
        self.assertEqual(next_params["per_page"], "10")

    def test_max_pages_limit(self):
        """Test that pagination respects the max_pages limit."""
        self.config.max_pages = 2

        # At page limit
        self.assertIsNone(self.handler.prepare_next_page_params({}, 1, {}, {}))

        # Before page limit
        self.config.mechanism = "page"
        self.config.page_param = "page"
        params = {"page": "1"}
        self.assertIsNotNone(self.handler.prepare_next_page_params(params, 0, {}, {}))


class TestRestApiToolPagination(unittest.TestCase):
    """Tests for the RestApiTool pagination functionality."""

    @patch("src.openapi.tools.requests.get")
    def test_execute_with_pagination(self, mock_get):
        """Test executing a request with pagination enabled."""
        # This would be a more comprehensive test implementation using mocks to
        # simulate a paginated API response and verify that the tool correctly
        # fetches and combines multiple pages.
        pass
