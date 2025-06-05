import unittest
from unittest.mock import patch
import base64
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.openapi.auth.auth_helpers import (
    token_to_scheme_credential,
    credential_to_param,
    build_httpx_auth,
    INTERNAL_AUTH_PREFIX,
)
from src.openapi.models import ApiAuthConfig


class TestAuthIntegration(unittest.TestCase):
    """Integration tests for authentication functionality."""
    
    def test_api_key_auth_flow(self):
        """Test complete API key authentication flow."""
        scheme, cred = token_to_scheme_credential("apikey", location="header", name="X-Token", credential_value="key123")
        param, kwargs = credential_to_param(scheme, cred)
        
        self.assertEqual(param.name, "X-Token")
        self.assertEqual(param.location, "header")
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "X-Token"], "key123")

    def test_bearer_auth_flow(self):
        """Test complete Bearer authentication flow."""
        scheme, cred = token_to_scheme_credential("bearer", credential_value="bearer_token_val")
        param, kwargs = credential_to_param(scheme, cred)
        
        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], "Bearer bearer_token_val")

    def test_basic_auth_flow(self):
        """Test complete Basic authentication flow."""
        scheme, cred = token_to_scheme_credential("basic", username="user", password="pass")
        param, kwargs = credential_to_param(scheme, cred)
        
        expected_encoded = base64.b64encode(b"user:pass").decode()
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], f"Basic {expected_encoded}")

    def test_invalid_auth_type_raises_error(self):
        """Test that invalid authentication types raise appropriate errors."""
        with self.assertRaisesRegex(ValueError, "Invalid security scheme type: unknown"):
            token_to_scheme_credential("unknown")

    def test_httpx_auth_building(self):
        """Test building httpx auth objects."""
        # Test API key
        auth_config = ApiAuthConfig(type="apiKey", name="X-API-Key", in_field="header", value="secret123")
        auth_obj = build_httpx_auth(auth_config)
        self.assertIsNotNone(auth_obj)

        # Test Bearer token
        auth_config = ApiAuthConfig(type="http", scheme="bearer", value="token123")
        auth_obj = build_httpx_auth(auth_config)
        self.assertIsNotNone(auth_obj)

        # Test no auth
        headers, auth_obj = build_httpx_auth(None)
        self.assertEqual(headers, {})
        self.assertIsNone(auth_obj)


if __name__ == '__main__':
    unittest.main() 