import unittest
from typing import List, Dict, Any
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pydantic import ValidationError

from src.openapi.models import (
    ApiParameter,
    ApiEndpoint,
    RateLimitConfig,
    RetryConfig,
    PaginationConfig,
    ApiAuthConfig
)

class TestApiEndpoint(unittest.TestCase):
    def test_parameter_collection_handling(self):
        """Test endpoint properly handles collections of parameters."""
        params = [
            ApiParameter(name="id", location="path", required=True),
            ApiParameter(name="filter", location="query", required=False),
            ApiParameter(name="auth", location="header", required=True)
        ]
        
        endpoint = ApiEndpoint(
            operation_id="complex_operation",
            method="GET", 
            path="/items/{id}",
            parameters=params
        )
        
        self.assertEqual(len(endpoint.parameters), 3)
        required_params = [p for p in endpoint.parameters if p.required]
        self.assertEqual(len(required_params), 2)


class TestPaginationConfig(unittest.TestCase):
    def test_pagination_mechanism_validation(self):
        """Test pagination configuration for different mechanisms."""
        # Test cursor-based pagination
        cursor_config = PaginationConfig(
            mechanism="cursor",
            cursor_param="next_token",
            cursor_response_field="data.nextToken",
            max_pages=10
        )
        self.assertEqual(cursor_config.mechanism, "cursor")
        self.assertEqual(cursor_config.cursor_param, "next_token")
        
        # Test offset-based pagination  
        offset_config = PaginationConfig(
            mechanism="offset",
            offset_param="start",
            limit_param="count",
            results_field="items"
        )
        self.assertEqual(offset_config.mechanism, "offset")
        self.assertEqual(offset_config.results_field, "items")


class TestApiAuthConfig(unittest.TestCase):
    def test_missing_required_type_raises_validation_error(self):
        """Test that missing required 'type' field raises ValidationError."""
        with self.assertRaises(ValidationError):
            ApiAuthConfig(name="X-API-KEY", in_field="header")


if __name__ == '__main__':
    unittest.main() 