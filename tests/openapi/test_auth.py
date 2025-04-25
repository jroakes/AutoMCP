"""Tests for the OpenAPI authentication functionality."""

import unittest
import base64
from unittest.mock import patch, Mock

from fastapi.openapi.models import APIKeyIn
from src.openapi.auth.auth_helpers import (
    token_to_scheme_credential,
    credential_to_param,
    AuthSchemeType,
    AuthCredentialTypes,
    HttpScheme,
    INTERNAL_AUTH_PREFIX,
)
from src.openapi.models import ApiAuthConfig
from src.openapi.tools import RestApiTool, ApiEndpoint


class TestAuthHelpers(unittest.TestCase):
    """Test cases for the authentication helpers."""

    def test_apikey_token_scheme_credential(self):
        """Test creating ApiKey scheme and credential."""
        # Header-based API key
        scheme, credential = token_to_scheme_credential(
            token_type="apikey",
            location="header",
            name="X-API-Key",
            credential_value="abc123",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.apiKey)
        self.assertEqual(scheme.in_, APIKeyIn.header)
        self.assertEqual(scheme.name, "X-API-Key")

        self.assertEqual(credential.auth_type, AuthCredentialTypes.API_KEY)
        self.assertEqual(credential.api_key, "abc123")

        # Query-based API key
        scheme, credential = token_to_scheme_credential(
            token_type="apikey",
            location="query",
            name="api_key",
            credential_value="xyz789",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.apiKey)
        self.assertEqual(scheme.in_, APIKeyIn.query)
        self.assertEqual(scheme.name, "api_key")

        self.assertEqual(credential.auth_type, AuthCredentialTypes.API_KEY)
        self.assertEqual(credential.api_key, "xyz789")

        # Missing location
        with self.assertRaises(ValueError):
            token_to_scheme_credential(
                token_type="apikey",
                name="api_key",
                credential_value="xyz789",
            )

        # Invalid location
        with self.assertRaises(ValueError):
            token_to_scheme_credential(
                token_type="apikey",
                location="invalid",
                name="api_key",
                credential_value="xyz789",
            )

    def test_bearer_token_scheme_credential(self):
        """Test creating Bearer scheme and credential."""
        scheme, credential = token_to_scheme_credential(
            token_type="bearer",
            credential_value="token123",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer)

        self.assertEqual(credential.auth_type, AuthCredentialTypes.BEARER)
        self.assertEqual(credential.token, "token123")

        # Without token
        scheme, credential = token_to_scheme_credential(
            token_type="bearer",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer)
        self.assertIsNone(credential)

    def test_basic_token_scheme_credential(self):
        """Test creating Basic auth scheme and credential."""
        # With username and password
        scheme, credential = token_to_scheme_credential(
            token_type="basic",
            username="user",
            password="pass",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.basic)

        self.assertEqual(credential.auth_type, AuthCredentialTypes.BASIC)
        self.assertEqual(credential.username, "user")
        self.assertEqual(credential.password, "pass")
        self.assertEqual(credential.basic_auth_value, "user:pass")

        # With credential value
        scheme, credential = token_to_scheme_credential(
            token_type="basic",
            credential_value="user:pass",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.basic)

        self.assertEqual(credential.auth_type, AuthCredentialTypes.BASIC)
        self.assertEqual(credential.token, "user:pass")
        self.assertEqual(credential.basic_auth_value, "user:pass")

    def test_oauth2_token_scheme_credential(self):
        """Test creating OAuth2 scheme and credential."""
        scheme, credential = token_to_scheme_credential(
            token_type="oauth2",
            credential_value="oauth_token_xyz",
        )

        self.assertEqual(scheme.type_, AuthSchemeType.oauth2)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer)

        self.assertEqual(credential.auth_type, AuthCredentialTypes.OAUTH2)
        self.assertEqual(credential.token, "oauth_token_xyz")
        self.assertEqual(credential.bearer_token, "oauth_token_xyz")

    def test_invalid_token_type(self):
        """Test invalid token type."""
        with self.assertRaises(ValueError):
            token_to_scheme_credential(
                token_type="invalid",
                credential_value="abc123",
            )

    def test_apikey_credential_to_param(self):
        """Test converting API key credential to parameter."""
        # Header-based API key
        scheme, credential = token_to_scheme_credential(
            token_type="apikey",
            location="header",
            name="X-API-Key",
            credential_value="abc123",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "X-API-Key")
        self.assertEqual(param.location, "header")
        self.assertEqual(kwargs[f"{INTERNAL_AUTH_PREFIX}X-API-Key"], "abc123")

        # Query-based API key
        scheme, credential = token_to_scheme_credential(
            token_type="apikey",
            location="query",
            name="api_key",
            credential_value="xyz789",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "api_key")
        self.assertEqual(param.location, "query")
        self.assertEqual(kwargs[f"{INTERNAL_AUTH_PREFIX}api_key"], "xyz789")

    def test_bearer_credential_to_param(self):
        """Test converting Bearer credential to parameter."""
        scheme, credential = token_to_scheme_credential(
            token_type="bearer",
            credential_value="token123",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(
            kwargs[f"{INTERNAL_AUTH_PREFIX}Authorization"], "Bearer token123"
        )

    def test_basic_credential_to_param(self):
        """Test converting Basic auth credential to parameter."""
        # With username and password
        scheme, credential = token_to_scheme_credential(
            token_type="basic",
            username="user",
            password="pass",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        # The header should be "Basic " + base64("user:pass")
        encoded = base64.b64encode(b"user:pass").decode()
        self.assertEqual(
            kwargs[f"{INTERNAL_AUTH_PREFIX}Authorization"], f"Basic {encoded}"
        )

        # With token directly
        scheme, credential = token_to_scheme_credential(
            token_type="basic",
            credential_value="already-base64-encoded",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(
            kwargs[f"{INTERNAL_AUTH_PREFIX}Authorization"],
            "Basic already-base64-encoded",
        )

    def test_oauth2_credential_to_param(self):
        """Test converting OAuth2 credential to parameter."""
        scheme, credential = token_to_scheme_credential(
            token_type="oauth2",
            credential_value="oauth_token_xyz",
        )

        param, kwargs = credential_to_param(scheme, credential)

        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(
            kwargs[f"{INTERNAL_AUTH_PREFIX}Authorization"], "Bearer oauth_token_xyz"
        )

    def test_no_auth_credential(self):
        """Test with no auth credential."""
        # Create a scheme but no credential
        scheme, _ = token_to_scheme_credential(
            token_type="bearer",
        )

        param, kwargs = credential_to_param(scheme, None)

        self.assertIsNone(param)
        self.assertIsNone(kwargs)


class TestRestApiToolAuth(unittest.TestCase):
    """Test the authentication functionality in RestApiTool."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock endpoint for testing
        self.endpoint = ApiEndpoint(
            operation_id="get_data",
            method="get",
            path="/data",
            parameters=[],
        )
        self.base_url = "https://api.example.com"

    @patch("src.openapi.tools.requests.get")
    def test_apikey_auth_header(self, mock_get):
        """Test API key authentication in header."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        # Create API Key auth config
        auth_config = ApiAuthConfig(
            type="apiKey",
            in_field="header",
            name="X-API-Key",
            value="test-api-key",
        )

        # Create and execute the tool
        tool = RestApiTool(
            name="get_data",
            description="Get data",
            endpoint=self.endpoint,
            base_url=self.base_url,
            auth_config=auth_config,
        )

        tool.execute()

        # Verify the header was set correctly
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        self.assertEqual(headers["X-API-Key"], "test-api-key")

    @patch("src.openapi.tools.requests.get")
    def test_apikey_auth_query(self, mock_get):
        """Test API key authentication in query parameter."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        # Create API Key auth config
        auth_config = ApiAuthConfig(
            type="apiKey",
            in_field="query",
            name="api_key",
            value="test-api-key",
        )

        # Create and execute the tool
        tool = RestApiTool(
            name="get_data",
            description="Get data",
            endpoint=self.endpoint,
            base_url=self.base_url,
            auth_config=auth_config,
        )

        tool.execute()

        # Verify the query parameter was set correctly
        mock_get.assert_called_once()
        params = mock_get.call_args[1]["params"]
        self.assertEqual(params["api_key"], "test-api-key")

    @patch("src.openapi.tools.requests.get")
    def test_bearer_auth(self, mock_get):
        """Test Bearer token authentication."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        # Create Bearer auth config
        auth_config = ApiAuthConfig(
            type="http",
            scheme="bearer",
            value="test-bearer-token",
        )

        # Create and execute the tool
        tool = RestApiTool(
            name="get_data",
            description="Get data",
            endpoint=self.endpoint,
            base_url=self.base_url,
            auth_config=auth_config,
        )

        tool.execute()

        # Verify the Authorization header was set correctly
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-bearer-token")

    @patch("src.openapi.tools.requests.get")
    def test_basic_auth(self, mock_get):
        """Test Basic authentication."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        # Create Basic auth config with username and password
        auth_config = ApiAuthConfig(
            type="http",
            scheme="basic",
            username="testuser",
            password="testpass",
        )

        # Create and execute the tool
        tool = RestApiTool(
            name="get_data",
            description="Get data",
            endpoint=self.endpoint,
            base_url=self.base_url,
            auth_config=auth_config,
        )

        tool.execute()

        # Verify the Authorization header was set correctly
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]

        # The header should be "Basic " + base64("testuser:testpass")
        encoded = base64.b64encode(b"testuser:testpass").decode()
        self.assertEqual(headers["Authorization"], f"Basic {encoded}")

    @patch("src.openapi.tools.requests.get")
    def test_oauth2_auth(self, mock_get):
        """Test OAuth2 authentication."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        # Create OAuth2 auth config
        auth_config = ApiAuthConfig(
            type="oauth2",
            value="test-oauth-token",
        )

        # Create and execute the tool
        tool = RestApiTool(
            name="get_data",
            description="Get data",
            endpoint=self.endpoint,
            base_url=self.base_url,
            auth_config=auth_config,
        )

        tool.execute()

        # Verify the Authorization header was set correctly
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-oauth-token")
