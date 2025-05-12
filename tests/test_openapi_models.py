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

class TestApiParameter(unittest.TestCase):
    def test_instantiation(self):
        param = ApiParameter(
            name="test_param",
            location="query",
            description="A test parameter",
            required=True,
            schema_definition={"type": "string", "format": "uuid"}
        )
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.location, "query")
        self.assertTrue(param.required)
        self.assertEqual(param.schema_definition, {"type": "string", "format": "uuid"})
        self.assertEqual(param.description, "A test parameter")

    def test_default_values(self):
        param = ApiParameter(name="min_param", location="header")
        self.assertEqual(param.description, "")
        self.assertFalse(param.required)
        self.assertEqual(param.schema_definition, {})

class TestApiEndpoint(unittest.TestCase):
    def test_instantiation(self):
        param1 = ApiParameter(name="id", location="path", required=True)
        endpoint = ApiEndpoint(
            operation_id="getItem",
            method="GET",
            path="/items/{id}",
            summary="Get an item by ID",
            parameters=[param1],
            response_schema={"type": "object"},
            request_body=None
        )
        self.assertEqual(endpoint.operation_id, "getItem")
        self.assertEqual(endpoint.method, "GET")
        self.assertEqual(endpoint.path, "/items/{id}")
        self.assertEqual(endpoint.summary, "Get an item by ID")
        self.assertEqual(len(endpoint.parameters), 1)
        self.assertEqual(endpoint.parameters[0].name, "id")
        self.assertEqual(endpoint.response_schema, {"type": "object"})
        self.assertIsNone(endpoint.request_body)

    def test_default_values(self):
        endpoint = ApiEndpoint(operation_id="opId", method="POST", path="/create")
        self.assertEqual(endpoint.summary, "")
        self.assertEqual(endpoint.description, "")
        self.assertEqual(endpoint.parameters, [])
        self.assertIsNone(endpoint.response_schema)
        self.assertIsNone(endpoint.request_body)

class TestRateLimitConfig(unittest.TestCase):
    def test_instantiation_and_defaults(self):
        config = RateLimitConfig()
        self.assertEqual(config.requests_per_minute, 60)
        self.assertIsNone(config.requests_per_hour)
        self.assertIsNone(config.requests_per_day)
        self.assertTrue(config.enabled)

    def test_custom_values(self):
        config = RateLimitConfig(requests_per_minute=100, requests_per_hour=1000, enabled=False)
        self.assertEqual(config.requests_per_minute, 100)
        self.assertEqual(config.requests_per_hour, 1000)
        self.assertFalse(config.enabled)

class TestRetryConfig(unittest.TestCase):
    def test_instantiation_and_defaults(self):
        config = RetryConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.backoff_factor, 0.5)
        self.assertEqual(config.retry_on_status_codes, [429, 500, 502, 503, 504])
        self.assertTrue(config.enabled)

    def test_custom_values(self):
        config = RetryConfig(max_retries=5, backoff_factor=1.0, retry_on_status_codes=[503], enabled=False)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.backoff_factor, 1.0)
        self.assertEqual(config.retry_on_status_codes, [503])
        self.assertFalse(config.enabled)

class TestPaginationConfig(unittest.TestCase):
    def test_instantiation_and_defaults(self):
        config = PaginationConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.mechanism, "auto")
        self.assertEqual(config.max_pages, 5)
        self.assertIsNone(config.cursor_param)
        self.assertIsNone(config.cursor_response_field)
        self.assertIsNone(config.offset_param)
        self.assertIsNone(config.limit_param)
        self.assertIsNone(config.page_param)
        self.assertIsNone(config.page_size_param)
        self.assertIsNone(config.results_field)

    def test_custom_values(self):
        config = PaginationConfig(
            enabled=False,
            mechanism="cursor",
            max_pages=10,
            cursor_param="next_token",
            cursor_response_field="data.nextToken",
            results_field="data.items"
        )
        self.assertFalse(config.enabled)
        self.assertEqual(config.mechanism, "cursor")
        self.assertEqual(config.max_pages, 10)
        self.assertEqual(config.cursor_param, "next_token")
        self.assertEqual(config.cursor_response_field, "data.nextToken")
        self.assertEqual(config.results_field, "data.items")

class TestApiAuthConfig(unittest.TestCase):
    def test_apikey_auth(self):
        auth = ApiAuthConfig(type="apiKey", name="X-API-KEY", in_field="header", value="secretkey")
        self.assertEqual(auth.type, "apiKey")
        self.assertEqual(auth.name, "X-API-KEY")
        self.assertEqual(auth.in_field, "header")
        self.assertEqual(auth.value, "secretkey")

    def test_http_bearer_auth(self):
        auth = ApiAuthConfig(type="http", scheme="bearer", value="bearertoken")
        self.assertEqual(auth.type, "http")
        self.assertEqual(auth.scheme, "bearer")
        self.assertEqual(auth.value, "bearertoken")

    def test_http_basic_auth_user_pass(self):
        auth = ApiAuthConfig(type="http", scheme="basic", username="user", password="pass")
        self.assertEqual(auth.type, "http")
        self.assertEqual(auth.scheme, "basic")
        self.assertEqual(auth.username, "user")
        self.assertEqual(auth.password, "pass")

    def test_http_basic_auth_value(self):
        # This case might be where `value` holds a pre-encoded string or `user:pass`
        auth = ApiAuthConfig(type="http", scheme="basic", value="dXNlcjpwYXNz")
        self.assertEqual(auth.type, "http")
        self.assertEqual(auth.scheme, "basic")
        self.assertEqual(auth.value, "dXNlcjpwYXNz")

    def test_oauth2_auth(self):
        auth = ApiAuthConfig(
            type="oauth2", 
            value="oauthtoken", 
            client_id="cid", 
            client_secret="csec", 
            token_url="http://token.url", 
            scope="read write",
            auto_refresh=True
        )
        self.assertEqual(auth.type, "oauth2")
        self.assertEqual(auth.value, "oauthtoken") # Typically the access token
        self.assertEqual(auth.client_id, "cid")
        self.assertEqual(auth.client_secret, "csec")
        self.assertEqual(auth.token_url, "http://token.url")
        self.assertEqual(auth.scope, "read write")
        self.assertTrue(auth.auto_refresh)

    def test_minimal_required(self):
        # Only type is truly required by Pydantic if others are Optional
        auth = ApiAuthConfig(type="custom_type")
        self.assertEqual(auth.type, "custom_type")
        self.assertIsNone(auth.name)
        self.assertIsNone(auth.value)

    def test_validation_error_if_type_missing(self):
        # Pydantic should raise ValidationError if a required field (like 'type') is missing
        with self.assertRaises(ValidationError):
            ApiAuthConfig(name="X-API-KEY", in_field="header") # Missing 'type'

if __name__ == '__main__':
    unittest.main() 