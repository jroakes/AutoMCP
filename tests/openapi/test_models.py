"""Unit tests for the OpenAPI models module."""

import unittest
from pydantic import ValidationError

from src.openapi.models import (
    ApiParameter,
    ApiEndpoint,
    ApiAuthConfig,
    RateLimitConfig,
    RetryConfig,
)


class TestApiParameter(unittest.TestCase):
    """Tests for the ApiParameter model."""

    def test_init_minimal(self):
        """Test initialization with minimal fields."""
        param = ApiParameter(name="test_param", location="query")
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.location, "query")
        self.assertEqual(param.description, "")
        self.assertFalse(param.required)
        self.assertEqual(param.schema, {})

    def test_init_full(self):
        """Test initialization with all fields."""
        param = ApiParameter(
            name="test_param",
            description="Test parameter",
            required=True,
            location="path",
            schema={"type": "string", "enum": ["value1", "value2"]},
        )
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.description, "Test parameter")
        self.assertTrue(param.required)
        self.assertEqual(param.location, "path")
        self.assertEqual(param.schema["type"], "string")
        self.assertEqual(param.schema["enum"], ["value1", "value2"])


class TestApiEndpoint(unittest.TestCase):
    """Tests for the ApiEndpoint model."""

    def test_init_minimal(self):
        """Test initialization with minimal fields."""
        endpoint = ApiEndpoint(operation_id="test_op", method="get", path="/test")
        self.assertEqual(endpoint.operation_id, "test_op")
        self.assertEqual(endpoint.method, "get")
        self.assertEqual(endpoint.path, "/test")
        self.assertEqual(endpoint.description, "")
        self.assertEqual(endpoint.summary, "")
        self.assertEqual(endpoint.parameters, [])
        self.assertIsNone(endpoint.response_schema)
        self.assertIsNone(endpoint.request_body)

    def test_init_with_parameters(self):
        """Test initialization with parameters."""
        param = ApiParameter(name="param1", location="query")
        endpoint = ApiEndpoint(
            operation_id="test_op", method="get", path="/test", parameters=[param]
        )
        self.assertEqual(len(endpoint.parameters), 1)
        self.assertEqual(endpoint.parameters[0].name, "param1")


class TestApiAuthConfig(unittest.TestCase):
    """Tests for the ApiAuthConfig model."""

    def test_init_api_key_header(self):
        """Test initialization with API key in header."""
        auth_config = ApiAuthConfig(
            type="apiKey", in_field="header", name="X-API-Key", value="test-key"
        )
        self.assertEqual(auth_config.type, "apiKey")
        self.assertEqual(auth_config.in_field, "header")
        self.assertEqual(auth_config.name, "X-API-Key")
        self.assertEqual(auth_config.value, "test-key")

    def test_init_api_key_query(self):
        """Test initialization with API key in query."""
        auth_config = ApiAuthConfig(
            type="apiKey", in_field="query", name="api_key", value="test-key"
        )
        self.assertEqual(auth_config.type, "apiKey")
        self.assertEqual(auth_config.in_field, "query")
        self.assertEqual(auth_config.name, "api_key")
        self.assertEqual(auth_config.value, "test-key")

    def test_init_bearer(self):
        """Test initialization with bearer token."""
        auth_config = ApiAuthConfig(type="http", scheme="bearer", value="test-token")
        self.assertEqual(auth_config.type, "http")
        self.assertEqual(auth_config.scheme, "bearer")
        self.assertEqual(auth_config.value, "test-token")


class TestRateLimitConfig(unittest.TestCase):
    """Tests for the RateLimitConfig model."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        config = RateLimitConfig()
        self.assertEqual(config.requests_per_minute, 60)
        self.assertIsNone(config.requests_per_hour)
        self.assertIsNone(config.requests_per_day)
        self.assertTrue(config.enabled)

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=1000,
            requests_per_day=5000,
            enabled=False,
        )
        self.assertEqual(config.requests_per_minute, 30)
        self.assertEqual(config.requests_per_hour, 1000)
        self.assertEqual(config.requests_per_day, 5000)
        self.assertFalse(config.enabled)


class TestRetryConfig(unittest.TestCase):
    """Tests for the RetryConfig model."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        retry_config = RetryConfig()

        # Check that default values are correctly set
        self.assertEqual(retry_config.max_retries, 3)
        self.assertEqual(retry_config.backoff_factor, 0.5)
        self.assertEqual(retry_config.retry_on_status_codes, [429, 500, 502, 503, 504])
        self.assertTrue(retry_config.enabled)

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        retry_config = RetryConfig(
            max_retries=5,
            backoff_factor=1.0,
            retry_on_status_codes=[500, 502],
            enabled=False,
        )

        # Check that custom values are correctly set
        self.assertEqual(retry_config.max_retries, 5)
        self.assertEqual(retry_config.backoff_factor, 1.0)
        self.assertEqual(retry_config.retry_on_status_codes, [500, 502])
        self.assertFalse(retry_config.enabled)

    def test_disable_retries(self):
        """Test disabling retries."""
        retry_config = RetryConfig()
        self.assertTrue(retry_config.enabled)

        # Disable retries
        retry_config.enabled = False
        self.assertFalse(retry_config.enabled)

    def test_modify_retry_status_codes(self):
        """Test modifying the retry status codes."""
        retry_config = RetryConfig()

        # Modify the retry status codes
        retry_config.retry_on_status_codes = [429, 503]

        # Check that the modification was successful
        self.assertEqual(retry_config.retry_on_status_codes, [429, 503])


if __name__ == "__main__":
    unittest.main()
