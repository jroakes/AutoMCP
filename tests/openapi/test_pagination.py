"""Tests for the OpenAPI pagination functionality."""

import unittest
from unittest.mock import patch, Mock

from src.openapi.models import PaginationConfig, ApiEndpoint, ApiParameter
from src.openapi.utils import PaginationHandler
from src.openapi.tools import RestApiTool


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

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock endpoint for testing
        self.endpoint = ApiEndpoint(
            operation_id="list_items",
            method="get",
            path="/items",
            parameters=[
                ApiParameter(
                    name="page",
                    location="query",
                    schema_definition={"type": "integer"},
                ),
                ApiParameter(
                    name="limit",
                    location="query",
                    schema_definition={"type": "integer"},
                ),
                ApiParameter(
                    name="offset",
                    location="query",
                    schema_definition={"type": "integer"},
                ),
                ApiParameter(
                    name="cursor",
                    location="query",
                    schema_definition={"type": "string"},
                ),
            ],
        )
        self.base_url = "https://api.example.com"

    @patch("src.openapi.tools.requests.get")
    def test_link_header_pagination(self, mock_get):
        """Test pagination with Link headers."""
        # Configure pagination
        pagination_config = PaginationConfig(
            enabled=True,
            mechanism="link",
            max_pages=3,
            results_field="items",
        )

        # Create the API tool
        api_tool = RestApiTool(
            name="list_items",
            description="List items",
            endpoint=self.endpoint,
            base_url=self.base_url,
            pagination_config=pagination_config,
        )

        # Create mock responses for multiple pages
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {
            "link": '<https://api.example.com/items?page=2>; rel="next"'
        }
        mock_response1.json.return_value = {"items": [1, 2, 3]}

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {
            "link": '<https://api.example.com/items?page=3>; rel="next"'
        }
        mock_response2.json.return_value = {"items": [4, 5, 6]}

        mock_response3 = Mock()
        mock_response3.status_code = 200
        mock_response3.headers = {}  # No more pages
        mock_response3.json.return_value = {"items": [7, 8, 9]}

        # Set up the mock to return different responses for each call
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]

        # Execute the request
        result = api_tool.execute()

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])

    @patch("src.openapi.tools.requests.get")
    def test_cursor_pagination(self, mock_get):
        """Test pagination with cursors."""
        # Configure pagination
        pagination_config = PaginationConfig(
            enabled=True,
            mechanism="cursor",
            max_pages=3,
            results_field="items",
            cursor_param="cursor",
            cursor_response_field="next_cursor",
        )

        # Create the API tool
        api_tool = RestApiTool(
            name="list_items",
            description="List items",
            endpoint=self.endpoint,
            base_url=self.base_url,
            pagination_config=pagination_config,
        )

        # Create mock responses for multiple pages
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {}
        mock_response1.json.return_value = {
            "items": [1, 2, 3],
            "next_cursor": "cursor_page2",
        }

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {}
        mock_response2.json.return_value = {
            "items": [4, 5, 6],
            "next_cursor": "cursor_page3",
        }

        mock_response3 = Mock()
        mock_response3.status_code = 200
        mock_response3.headers = {}
        mock_response3.json.return_value = {
            "items": [7, 8, 9],
            "next_cursor": None,  # No more pages
        }

        # Set up the mock to return different responses for each call
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]

        # Execute the request
        result = api_tool.execute()

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])

        # Check that cursor was properly passed to subsequent requests
        calls = mock_get.call_args_list
        self.assertEqual(len(calls), 3)

        # First call should have no cursor
        self.assertEqual(calls[0][1].get("params", {}).get("cursor", None), None)

        # Second call should use cursor_page2
        self.assertEqual(calls[1][1].get("params", {}).get("cursor"), "cursor_page2")

        # Third call should use cursor_page3
        self.assertEqual(calls[2][1].get("params", {}).get("cursor"), "cursor_page3")

    @patch("src.openapi.tools.requests.get")
    def test_offset_pagination(self, mock_get):
        """Test pagination with offset/limit."""
        # Configure pagination
        pagination_config = PaginationConfig(
            enabled=True,
            mechanism="offset",
            max_pages=3,
            results_field="items",
            offset_param="offset",
            limit_param="limit",
        )

        # Create the API tool
        api_tool = RestApiTool(
            name="list_items",
            description="List items",
            endpoint=self.endpoint,
            base_url=self.base_url,
            pagination_config=pagination_config,
        )

        # Create mock responses for multiple pages
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {}
        mock_response1.json.return_value = {"items": [1, 2, 3]}

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {}
        mock_response2.json.return_value = {"items": [4, 5, 6]}

        mock_response3 = Mock()
        mock_response3.status_code = 200
        mock_response3.headers = {}
        mock_response3.json.return_value = {"items": [7, 8, 9]}

        # Set up the mock to return different responses for each call
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]

        # Execute the request with initial offset and limit
        result = api_tool.execute(offset="0", limit="3")

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])

        # Check that offset was properly incremented
        calls = mock_get.call_args_list
        self.assertEqual(len(calls), 3)

        # First call should have offset="0"
        self.assertEqual(calls[0][1].get("params", {}).get("offset"), "0")
        self.assertEqual(calls[0][1].get("params", {}).get("limit"), "3")

        # Second call should have offset="3"
        self.assertEqual(calls[1][1].get("params", {}).get("offset"), "3")
        self.assertEqual(calls[1][1].get("params", {}).get("limit"), "3")

        # Third call should have offset="6"
        self.assertEqual(calls[2][1].get("params", {}).get("offset"), "6")
        self.assertEqual(calls[2][1].get("params", {}).get("limit"), "3")

    @patch("src.openapi.tools.requests.get")
    def test_page_pagination(self, mock_get):
        """Test pagination with page numbers."""
        # Configure pagination
        pagination_config = PaginationConfig(
            enabled=True,
            mechanism="page",
            max_pages=3,
            results_field="items",
            page_param="page",
            page_size_param="limit",
        )

        # Create the API tool
        api_tool = RestApiTool(
            name="list_items",
            description="List items",
            endpoint=self.endpoint,
            base_url=self.base_url,
            pagination_config=pagination_config,
        )

        # Create mock responses for multiple pages
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {}
        mock_response1.json.return_value = {
            "items": [1, 2, 3],
            "page": 1,
            "total_pages": 3,
        }

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {}
        mock_response2.json.return_value = {
            "items": [4, 5, 6],
            "page": 2,
            "total_pages": 3,
        }

        mock_response3 = Mock()
        mock_response3.status_code = 200
        mock_response3.headers = {}
        mock_response3.json.return_value = {
            "items": [7, 8, 9],
            "page": 3,
            "total_pages": 3,
        }

        # Set up the mock to return different responses for each call
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]

        # Execute the request with initial page (pass as string)
        result = api_tool.execute(page="1", limit="3")

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6, 7, 8, 9])

        # Check that page was properly incremented
        calls = mock_get.call_args_list
        self.assertEqual(len(calls), 3)

        # First call should have page="1"
        self.assertEqual(calls[0][1].get("params", {}).get("page"), "1")
        self.assertEqual(calls[0][1].get("params", {}).get("limit"), "3")

        # Second call should have page="2"
        self.assertEqual(calls[1][1].get("params", {}).get("page"), "2")
        self.assertEqual(calls[1][1].get("params", {}).get("limit"), "3")

        # Third call should have page="3"
        self.assertEqual(calls[2][1].get("params", {}).get("page"), "3")
        self.assertEqual(calls[2][1].get("params", {}).get("limit"), "3")

    @patch("src.openapi.tools.requests.get")
    def test_auto_pagination_detection(self, mock_get):
        """Test auto-detection of pagination mechanism."""
        # Configure pagination with auto-detection
        pagination_config = PaginationConfig(
            enabled=True,
            mechanism="auto",
            max_pages=2,  # Reduce to 2 pages to simplify test
            results_field="items",
            cursor_param="cursor",
            cursor_response_field="next_cursor",
            offset_param="offset",
            limit_param="limit",
            page_param="page",
        )

        # Create the API tool
        api_tool = RestApiTool(
            name="list_items",
            description="List items",
            endpoint=self.endpoint,
            base_url=self.base_url,
            pagination_config=pagination_config,
        )

        # --- Test Link header detection ---

        # Reset mock
        mock_get.reset_mock()
        mock_get.side_effect = None

        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {
            "link": '<https://api.example.com/items?page=2>; rel="next"'
        }
        mock_response1.json.return_value = {"items": [1, 2, 3]}

        mock_response2 = Mock()
        mock_response2.status_code = 200
        # No next link in the second response (end of pagination)
        mock_response2.headers = {}
        mock_response2.json.return_value = {"items": [4, 5, 6]}

        # Set up the mock with just two responses (max_pages=2)
        mock_get.side_effect = [mock_response1, mock_response2]

        # Execute the request
        result = api_tool.execute()

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6])

        # Second call should be to the full URL from the Link header
        self.assertEqual(
            mock_get.call_args_list[1][0][0], "https://api.example.com/items?page=2"
        )

        # --- Test cursor detection ---

        # Reset mock
        mock_get.reset_mock()
        mock_get.side_effect = None

        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {}
        mock_response1.json.return_value = {
            "items": [1, 2, 3],
            "next_cursor": "next_page",
        }

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {}
        mock_response2.json.return_value = {"items": [4, 5, 6], "next_cursor": None}

        # Set up the mock
        mock_get.side_effect = [mock_response1, mock_response2]

        # Execute the request
        result = api_tool.execute()

        # Verify pagination occurred and results were combined
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(result["items"], [1, 2, 3, 4, 5, 6])

        # Second call should include the cursor
        self.assertEqual(mock_get.call_args_list[1][1]["params"]["cursor"], "next_page")
