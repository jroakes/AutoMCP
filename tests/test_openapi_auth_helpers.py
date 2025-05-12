import unittest
from unittest.mock import patch
import base64
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Corrected path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import httpx # For testing build_httpx_auth

from src.openapi.auth.auth_helpers import (
    AuthScheme,
    AuthCredential,
    AuthSchemeType,
    AuthCredentialTypes,
    HttpScheme,
    APIKeyIn,
    token_to_scheme_credential,
    credential_to_param,
    build_httpx_auth,
    INTERNAL_AUTH_PREFIX,
)
from src.openapi.models import ApiParameter, ApiAuthConfig # ApiAuthConfig for build_httpx_auth
from fastapi.openapi.models import APIKey # For AuthScheme.from_api_key


class TestAuthScheme(unittest.TestCase):
    def test_from_api_key(self):
        api_key_model = APIKey(name="X-API-Token", **{"in": APIKeyIn.header}, type="apiKey", description="Test Key")
        scheme = AuthScheme.from_api_key(api_key_model)
        self.assertEqual(scheme.type_, AuthSchemeType.apiKey)
        self.assertEqual(scheme.name, "X-API-Token")
        self.assertEqual(scheme.in_, APIKeyIn.header)
        self.assertEqual(scheme.description, "Test Key")

    def test_from_http_bearer(self):
        scheme = AuthScheme.from_http(HttpScheme.bearer, description="Bearer Auth")
        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer)
        self.assertEqual(scheme.description, "Bearer Auth")

    def test_from_http_basic_default_description(self):
        scheme = AuthScheme.from_http(HttpScheme.basic)
        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.basic)
        self.assertEqual(scheme.description, f"HTTP {HttpScheme.basic} authentication")

    def test_from_oauth2(self):
        scheme = AuthScheme.from_oauth2(description="OAuth2 Flow")
        self.assertEqual(scheme.type_, AuthSchemeType.oauth2)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer) # OAuth2 uses Bearer
        self.assertEqual(scheme.description, "OAuth2 Flow")

class TestAuthCredential(unittest.TestCase):
    def test_basic_auth_value_username_password(self):
        cred = AuthCredential(auth_type=AuthCredentialTypes.BASIC, username="user", password="pass")
        self.assertEqual(cred.basic_auth_value, "user:pass")

    def test_basic_auth_value_token(self):
        cred = AuthCredential(auth_type=AuthCredentialTypes.BASIC, token="dXNlcjpwYXNz") # user:pass base64
        self.assertEqual(cred.basic_auth_value, "dXNlcjpwYXNz")

    def test_bearer_token_bearer_type(self):
        cred = AuthCredential(auth_type=AuthCredentialTypes.BEARER, token="mybearertoken")
        self.assertEqual(cred.bearer_token, "mybearertoken")

    def test_bearer_token_oauth2_type(self):
        cred = AuthCredential(auth_type=AuthCredentialTypes.OAUTH2, token="myoauthtoken")
        self.assertEqual(cred.bearer_token, "myoauthtoken")

    def test_property_none_when_not_applicable(self):
        cred_apikey = AuthCredential(auth_type=AuthCredentialTypes.API_KEY, api_key="key")
        self.assertIsNone(cred_apikey.basic_auth_value)
        self.assertIsNone(cred_apikey.bearer_token)

        cred_bearer = AuthCredential(auth_type=AuthCredentialTypes.BEARER, token="token")
        self.assertIsNone(cred_bearer.basic_auth_value)

class TestTokenToSchemeCredential(unittest.TestCase):
    def test_apikey_header(self):
        scheme, cred = token_to_scheme_credential("apikey", location="header", name="X-Token", credential_value="key123")
        self.assertEqual(scheme.type_, AuthSchemeType.apiKey)
        self.assertEqual(scheme.in_, APIKeyIn.header)
        self.assertEqual(scheme.name, "X-Token")
        self.assertIsNotNone(cred)
        self.assertEqual(cred.auth_type, AuthCredentialTypes.API_KEY)
        self.assertEqual(cred.api_key, "key123")

    def test_apikey_query_no_credential(self):
        scheme, cred = token_to_scheme_credential("apikey", location="query", name="api_key")
        self.assertEqual(scheme.type_, AuthSchemeType.apiKey)
        self.assertEqual(scheme.in_, APIKeyIn.query)
        self.assertIsNone(cred)

    def test_bearer(self):
        scheme, cred = token_to_scheme_credential("bearer", credential_value="bearer_token_val")
        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.bearer)
        self.assertIsNotNone(cred)
        self.assertEqual(cred.auth_type, AuthCredentialTypes.BEARER)
        self.assertEqual(cred.token, "bearer_token_val")

    def test_basic_username_password(self):
        scheme, cred = token_to_scheme_credential("basic", username="myuser", password="mypass")
        self.assertEqual(scheme.type_, AuthSchemeType.http)
        self.assertEqual(scheme.http_scheme, HttpScheme.basic)
        self.assertIsNotNone(cred)
        self.assertEqual(cred.auth_type, AuthCredentialTypes.BASIC)
        self.assertEqual(cred.username, "myuser")
        self.assertEqual(cred.password, "mypass")

    def test_basic_credential_value(self):
        scheme, cred = token_to_scheme_credential("basic", credential_value="user:pass_encoded")
        self.assertIsNotNone(cred)
        self.assertEqual(cred.auth_type, AuthCredentialTypes.BASIC)
        self.assertEqual(cred.token, "user:pass_encoded") # Stores as token

    def test_oauth2(self):
        scheme, cred = token_to_scheme_credential("oauth2", credential_value="oauth_token_val")
        self.assertEqual(scheme.type_, AuthSchemeType.oauth2)
        self.assertIsNotNone(cred)
        self.assertEqual(cred.auth_type, AuthCredentialTypes.OAUTH2)
        self.assertEqual(cred.token, "oauth_token_val")

    def test_invalid_type(self):
        with self.assertRaisesRegex(ValueError, "Invalid security scheme type: unknown"):
            token_to_scheme_credential("unknown")

    def test_apikey_missing_location(self):
        with self.assertRaisesRegex(ValueError, "Location is required for apiKey"):
            token_to_scheme_credential("apikey", name="X-Token")

    def test_apikey_invalid_location(self):
        with self.assertRaisesRegex(ValueError, "Invalid location for apiKey: cookie"):
            token_to_scheme_credential("apikey", location="cookie", name="X-Token")

class TestCredentialToParam(unittest.TestCase):
    def test_apikey_header(self):
        scheme = AuthScheme(type_=AuthSchemeType.apiKey, name="X-Api-Key", in_=APIKeyIn.header)
        cred = AuthCredential(auth_type=AuthCredentialTypes.API_KEY, api_key="secret")
        param, kwargs = credential_to_param(scheme, cred)
        self.assertIsInstance(param, ApiParameter)
        self.assertEqual(param.name, "X-Api-Key")
        self.assertEqual(param.location, "header")
        self.assertIsNotNone(kwargs)
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "X-Api-Key"], "secret")

    def test_apikey_query(self):
        scheme = AuthScheme(type_=AuthSchemeType.apiKey, name="token", in_=APIKeyIn.query)
        cred = AuthCredential(auth_type=AuthCredentialTypes.API_KEY, api_key="q_secret")
        param, kwargs = credential_to_param(scheme, cred)
        self.assertEqual(param.location, "query")
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "token"], "q_secret")

    def test_http_bearer(self):
        scheme = AuthScheme(type_=AuthSchemeType.http, http_scheme=HttpScheme.bearer)
        cred = AuthCredential(auth_type=AuthCredentialTypes.BEARER, token="b_token")
        param, kwargs = credential_to_param(scheme, cred)
        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], "Bearer b_token")

    def test_http_basic_user_pass(self):
        scheme = AuthScheme(type_=AuthSchemeType.http, http_scheme=HttpScheme.basic)
        cred = AuthCredential(auth_type=AuthCredentialTypes.BASIC, username="usr", password="pwd")
        param, kwargs = credential_to_param(scheme, cred)
        expected_encoded = base64.b64encode(b"usr:pwd").decode()
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], f"Basic {expected_encoded}")

    def test_http_basic_pre_encoded_token(self):
        scheme = AuthScheme(type_=AuthSchemeType.http, http_scheme=HttpScheme.basic)
        cred = AuthCredential(auth_type=AuthCredentialTypes.BASIC, token="dXNyOnB3ZA==") # usr:pwd
        param, kwargs = credential_to_param(scheme, cred)
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], "Basic dXNyOnB3ZA==")

    def test_oauth2(self):
        scheme = AuthScheme(type_=AuthSchemeType.oauth2)
        cred = AuthCredential(auth_type=AuthCredentialTypes.OAUTH2, token="oauth_tok")
        param, kwargs = credential_to_param(scheme, cred)
        self.assertEqual(param.name, "Authorization")
        self.assertEqual(param.location, "header")
        self.assertEqual(kwargs[INTERNAL_AUTH_PREFIX + "Authorization"], "Bearer oauth_tok")

    def test_no_credential(self):
        scheme = AuthScheme(type_=AuthSchemeType.apiKey, name="X-Key", in_=APIKeyIn.header)
        param, kwargs = credential_to_param(scheme, None) # No credential
        self.assertIsNone(param)
        self.assertIsNone(kwargs)

    def test_apikey_no_key_value(self):
        scheme = AuthScheme(type_=AuthSchemeType.apiKey, name="X-Key", in_=APIKeyIn.header)
        cred = AuthCredential(auth_type=AuthCredentialTypes.API_KEY, api_key=None) # No key value
        param, kwargs = credential_to_param(scheme, cred)
        self.assertIsNone(param)
        self.assertIsNone(kwargs)

class TestBuildHttpxAuth(unittest.TestCase):
    def test_no_auth_config(self):
        headers, auth_obj = build_httpx_auth(None)
        self.assertEqual(headers, {})
        self.assertIsNone(auth_obj)

    def test_apikey_header(self):
        auth_conf = ApiAuthConfig(type="apiKey", name="X-My-Key", in_field="header", value="key_value")
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {"X-My-Key": "key_value"})
        self.assertIsNone(auth_obj)

    def test_apikey_query(self):
        # Query API keys are handled per-request, not in client defaults
        auth_conf = ApiAuthConfig(type="apiKey", name="api_token", in_field="query", value="query_val")
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {}) # No default headers for query type
        self.assertIsNone(auth_obj)

    def test_http_basic_user_pass(self):
        auth_conf = ApiAuthConfig(type="http", scheme="basic", username="testuser", password="testpass")
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {})
        self.assertIsInstance(auth_obj, httpx.BasicAuth)
        self.assertEqual(auth_obj._auth_header, f"Basic {base64.b64encode(b'testuser:testpass').decode()}")

    def test_http_basic_value_user_pass_format(self):
        auth_conf = ApiAuthConfig(type="http", scheme="basic", value="user1:pass1")
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {})
        self.assertIsInstance(auth_obj, httpx.BasicAuth)
        self.assertEqual(auth_obj._auth_header, f"Basic {base64.b64encode(b'user1:pass1').decode()}")

    def test_http_basic_value_pre_encoded(self):
        """Test handling of a pre-encoded token for HTTP Basic auth.
        
        The build_httpx_auth function creates direct Authorization headers 
        when given a pre-encoded value that doesn't contain a colon.
        """
        # This is a base64 encoded token that doesn't follow username:password format
        # In real code, this token would be an opaque value provided by the API
        encoded_token = base64.b64encode(b"direct:value").decode()
        
        # When the auth config has type=http, scheme=basic, and a value without a colon,
        # build_httpx_auth should create a direct Authorization header
        auth_conf = ApiAuthConfig(type="http", scheme="basic", value=encoded_token)
        headers, auth_obj = build_httpx_auth(auth_conf)
        
        # The function should place the token directly in the Authorization header
        # with the "Basic" prefix and NOT create an httpx.BasicAuth object
        self.assertEqual(headers, {"Authorization": f"Basic {encoded_token}"})
        self.assertIsNone(auth_obj)

    def test_http_bearer(self):
        auth_conf = ApiAuthConfig(type="http", scheme="bearer", value="my_bearer_token")
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {"Authorization": "Bearer my_bearer_token"})
        self.assertIsNone(auth_obj)

    def test_oauth2(self):
        auth_conf = ApiAuthConfig(type="oauth2", value="my_oauth_token") # Assumes value is the token for OAuth2
        headers, auth_obj = build_httpx_auth(auth_conf)
        self.assertEqual(headers, {"Authorization": "Bearer my_oauth_token"})
        self.assertIsNone(auth_obj)

if __name__ == '__main__':
    unittest.main() 