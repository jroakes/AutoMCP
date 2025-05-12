"""Authentication helpers for OpenAPI.

Simplified version of Google ADK's auth_helpers focusing on API key authentication.
"""

import base64
from typing import Dict, Any, Optional, Tuple, Literal
from enum import Enum

from fastapi.openapi.models import APIKey, APIKeyIn
from pydantic import BaseModel
from ..models import ApiParameter


# Internal prefix for auth parameters
INTERNAL_AUTH_PREFIX = "_auth_prefix_"


class AuthSchemeType(str, Enum):
    """Types of authentication schemes."""

    apiKey = "apiKey"
    http = "http"
    oauth2 = "oauth2"


class AuthCredentialTypes(str, Enum):
    """Types of authentication credentials."""

    API_KEY = "API_KEY"
    BEARER = "BEARER"
    BASIC = "BASIC"
    OAUTH2 = "OAUTH2"


class HttpScheme(str, Enum):
    """HTTP authentication schemes."""

    bearer = "bearer"
    basic = "basic"


class AuthScheme(BaseModel):
    """Base class for authentication schemes."""

    type_: AuthSchemeType
    description: Optional[str] = None
    name: Optional[str] = None
    in_: Optional[APIKeyIn] = None
    http_scheme: Optional[HttpScheme] = None

    @classmethod
    def from_api_key(cls, api_key: APIKey) -> "AuthScheme":
        """Create an AuthScheme from an APIKey."""
        return cls(
            type_=AuthSchemeType.apiKey,
            description=api_key.description,
            name=api_key.name,
            in_=api_key.in_,
        )

    @classmethod
    def from_http(
        cls, scheme: HttpScheme, description: Optional[str] = None
    ) -> "AuthScheme":
        """Create an AuthScheme for HTTP authentication."""
        return cls(
            type_=AuthSchemeType.http,
            description=description or f"HTTP {scheme} authentication",
            http_scheme=scheme,
        )

    @classmethod
    def from_oauth2(cls, description: Optional[str] = None) -> "AuthScheme":
        """Create an AuthScheme for OAuth2 authentication."""
        return cls(
            type_=AuthSchemeType.oauth2,
            description=description or "OAuth2 authentication",
            http_scheme=HttpScheme.bearer,  # OAuth2 uses bearer tokens
        )


class AuthCredential(BaseModel):
    """Authentication credential.

    Args:
        auth_type: Type of authentication
        api_key: API key value for API_KEY auth
        token: Token value for BEARER or OAUTH2 auth
        username: Username for BASIC auth
        password: Password for BASIC auth
    """

    auth_type: AuthCredentialTypes
    api_key: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def basic_auth_value(self) -> Optional[str]:
        """Get the Basic auth value as 'username:password' for HTTP Basic auth."""
        if (
            self.auth_type == AuthCredentialTypes.BASIC
            and self.username
            and self.password
        ):
            return f"{self.username}:{self.password}"
        if self.auth_type == AuthCredentialTypes.BASIC and self.token:
            return self.token
        return None

    @property
    def bearer_token(self) -> Optional[str]:
        """Get the bearer token for HTTP Bearer or OAuth2 auth."""
        if (
            self.auth_type in (AuthCredentialTypes.BEARER, AuthCredentialTypes.OAUTH2)
            and self.token
        ):
            return self.token
        return None


def token_to_scheme_credential(
    token_type: Literal["apikey", "bearer", "basic", "oauth2"],
    location: Optional[Literal["header", "query"]] = None,
    name: Optional[str] = None,
    credential_value: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Tuple[AuthScheme, Optional[AuthCredential]]:
    """Creates AuthScheme and AuthCredential for various authentication types.

    Args:
        token_type: "apikey", "bearer", "basic", or "oauth2"
        location: "header" or "query" (for apikey only)
        name: Name of the header or query parameter (for apikey only)
        credential_value: Value of the API key, token, or combined "username:password"
        username: Username for basic auth (alternative to credential_value)
        password: Password for basic auth (alternative to credential_value)

    Returns:
        Tuple: (AuthScheme, AuthCredential)

    Raises:
        ValueError: For invalid type or location
    """
    if token_type == "apikey":
        if not location:
            raise ValueError("Location is required for apiKey")

        in_: APIKeyIn
        if location == "header":
            in_ = APIKeyIn.header
        elif location == "query":
            in_ = APIKeyIn.query
        else:
            raise ValueError(f"Invalid location for apiKey: {location}")

        # FastAPI's APIKey model expects the field name "in" not "in_". Provide it via kwargs.
        api_key = APIKey(type="apiKey", **{"in": in_}, name=name)
        auth_scheme = AuthScheme.from_api_key(api_key)

        if credential_value:
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.API_KEY, api_key=credential_value
            )
        else:
            auth_credential = None

    elif token_type == "bearer":
        auth_scheme = AuthScheme.from_http(HttpScheme.bearer)
        if credential_value:
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.BEARER, token=credential_value
            )
        else:
            auth_credential = None

    elif token_type == "basic":
        auth_scheme = AuthScheme.from_http(HttpScheme.basic)

        # Handle username/password pair or pre-formatted value
        if username and password:
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.BASIC,
                username=username,
                password=password,
            )
        elif credential_value:
            # Assume credential_value is either "username:password" or already encoded
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.BASIC, token=credential_value
            )
        else:
            auth_credential = None

    elif token_type == "oauth2":
        auth_scheme = AuthScheme.from_oauth2()
        if credential_value:
            auth_credential = AuthCredential(
                auth_type=AuthCredentialTypes.OAUTH2, token=credential_value
            )
        else:
            auth_credential = None

    else:
        raise ValueError(f"Invalid security scheme type: {token_type}")

    return auth_scheme, auth_credential


def credential_to_param(
    auth_scheme: AuthScheme,
    auth_credential: AuthCredential,
) -> Tuple[Optional[ApiParameter], Optional[Dict[str, Any]]]:
    """Converts AuthCredential and AuthScheme to a Parameter and a dictionary for additional kwargs.

    Args:
        auth_scheme: The AuthScheme object
        auth_credential: The AuthCredential object

    Returns:
        Tuple: (ApiParameter, Dict[str, Any])
    """
    if not auth_credential:
        return None, None

    if (
        auth_scheme.type_ == AuthSchemeType.apiKey
        and auth_credential.auth_type == AuthCredentialTypes.API_KEY
    ):
        if not auth_credential.api_key:
            return None, None

        param_name = auth_scheme.name or ""
        python_name = INTERNAL_AUTH_PREFIX + param_name

        if auth_scheme.in_ == APIKeyIn.header:
            param_location = "header"
        elif auth_scheme.in_ == APIKeyIn.query:
            param_location = "query"
        else:
            raise ValueError(f"Invalid API Key location: {auth_scheme.in_}")

        param = ApiParameter(
            name=param_name,
            location=param_location,
            schema_definition={"type": "string"},
            description=auth_scheme.description or "",
        )

        kwargs = {python_name: auth_credential.api_key}
        return param, kwargs

    elif auth_scheme.type_ == AuthSchemeType.http:
        # HTTP auth always goes in the Authorization header
        param = ApiParameter(
            name="Authorization",
            location="header",
            schema_definition={"type": "string"},
            description=auth_scheme.description or "",
        )

        if (
            auth_scheme.http_scheme == HttpScheme.bearer
            and auth_credential.bearer_token
        ):
            # Bearer authentication
            kwargs = {
                INTERNAL_AUTH_PREFIX
                + "Authorization": f"Bearer {auth_credential.bearer_token}"
            }
            return param, kwargs

        elif (
            auth_scheme.http_scheme == HttpScheme.basic
            and auth_credential.basic_auth_value
        ):
            # Basic authentication
            basic_auth = auth_credential.basic_auth_value
            # Encode as base64 if not already encoded
            if ":" in basic_auth:  # username:password format
                encoded_auth = base64.b64encode(basic_auth.encode()).decode()
                kwargs = {
                    INTERNAL_AUTH_PREFIX + "Authorization": f"Basic {encoded_auth}"
                }
                return param, kwargs
            else:
                # Assuming already formatted correctly
                kwargs = {INTERNAL_AUTH_PREFIX + "Authorization": f"Basic {basic_auth}"}
                return param, kwargs

    elif auth_scheme.type_ == AuthSchemeType.oauth2 and auth_credential.bearer_token:
        # OAuth2 uses Bearer token in Authorization header
        param = ApiParameter(
            name="Authorization",
            location="header",
            schema_definition={"type": "string"},
            description=auth_scheme.description or "",
        )

        kwargs = {
            INTERNAL_AUTH_PREFIX
            + "Authorization": f"Bearer {auth_credential.bearer_token}"
        }
        return param, kwargs

    return None, None


def build_httpx_auth(auth_config):
    """
    Converts ApiAuthConfig to httpx-compatible auth configuration.
    
    Args:
        auth_config: Authentication configuration
        
    Returns:
        tuple[dict, Any]: A tuple of (default_headers, httpx_auth_object_or_None)
        that can be passed directly to httpx.AsyncClient constructor.
    """
    import httpx
    
    if not auth_config:
        return {}, None
        
    headers = {}
    auth = None
    
    if auth_config.type == "apiKey":
        if auth_config.in_field == "header" and auth_config.name:
            # For header-based API keys, add to default headers
            headers[auth_config.name] = auth_config.value
        # For query-based API keys, we'll add them per-request
        
    elif auth_config.type == "http":
        if auth_config.scheme == "basic":
            # Check if username AND password are provided
            if hasattr(auth_config, "username") and auth_config.username is not None and \
               hasattr(auth_config, "password") and auth_config.password is not None:
                # Use httpx's BasicAuth class
                auth = httpx.BasicAuth(auth_config.username, auth_config.password)
            # Check if value is provided and looks like user:pass (for potential splitting)
            elif hasattr(auth_config, "value") and auth_config.value and ":" in auth_config.value:
                try:
                    username, password = auth_config.value.split(":", 1)
                    auth = httpx.BasicAuth(username, password)
                except ValueError:
                    # If splitting fails or format is unexpected, treat as pre-formatted header value
                    logger.warning("Basic auth value format unexpected, treating as pre-formatted header.")
                    headers["Authorization"] = f"Basic {auth_config.value}"
            # Check if only value is provided (assume pre-formatted/encoded)
            elif hasattr(auth_config, "value") and auth_config.value:
                headers["Authorization"] = f"Basic {auth_config.value}"
            # Else, invalid basic auth config provided
            else:
                 logger.warning("Invalid configuration for HTTP Basic Auth. Provide username/password or a value.")
                
        elif auth_config.scheme == "bearer":
            # Bearer token in Authorization header
            headers["Authorization"] = f"Bearer {auth_config.value}"
            
    elif auth_config.type == "oauth2":
        # OAuth2 uses Bearer format in Authorization header
        headers["Authorization"] = f"Bearer {auth_config.value}"
        
    return headers, auth
