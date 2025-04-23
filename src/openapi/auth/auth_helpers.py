"""Authentication helpers for OpenAPI.

Simplified version of Google ADK's auth_helpers focusing on API key authentication.
"""

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


class AuthCredentialTypes(str, Enum):
    """Types of authentication credentials."""

    API_KEY = "API_KEY"


class AuthScheme(BaseModel):
    """Base class for authentication schemes."""

    type_: AuthSchemeType
    description: Optional[str] = None
    name: Optional[str] = None
    in_: Optional[APIKeyIn] = None

    @classmethod
    def from_api_key(cls, api_key: APIKey) -> "AuthScheme":
        """Create an AuthScheme from an APIKey."""
        return cls(
            type_=AuthSchemeType.apiKey,
            description=api_key.description,
            name=api_key.name,
            in_=api_key.in_,
        )


class AuthCredential(BaseModel):
    """Authentication credential.

    Args:
        auth_type: Type of authentication
        api_key: API key value
    """

    auth_type: AuthCredentialTypes
    api_key: Optional[str] = None


def token_to_scheme_credential(
    token_type: Literal["apikey"],
    location: Optional[Literal["header", "query"]] = None,
    name: Optional[str] = None,
    credential_value: Optional[str] = None,
) -> Tuple[AuthScheme, Optional[AuthCredential]]:
    """Creates AuthScheme and AuthCredential for API key.

    Args:
        token_type: Must be "apikey"
        location: "header" or "query"
        name: Name of the header or query parameter
        credential_value: Value of the API key

    Returns:
        Tuple: (AuthScheme, AuthCredential)

    Raises:
        ValueError: For invalid type or location
    """
    if token_type != "apikey":
        raise ValueError(f"Invalid security scheme type: {token_type}")

    in_: APIKeyIn
    if location == "header":
        in_ = APIKeyIn.header
    elif location == "query":
        in_ = APIKeyIn.query
    else:
        raise ValueError(f"Invalid location for apiKey: {location}")

    api_key = APIKey(type="apiKey", in_=in_, name=name)
    auth_scheme = AuthScheme.from_api_key(api_key)

    if credential_value:
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.API_KEY, api_key=credential_value
        )
    else:
        auth_credential = None

    return auth_scheme, auth_credential


def credential_to_param(
    auth_scheme: AuthScheme,
    auth_credential: AuthCredential,
) -> Tuple[Optional[ApiParameter], Optional[Dict[str, Any]]]:
    """Converts AuthCredential and AuthScheme to a Parameter and a dictionary for additional kwargs.

    Args:
        auth_scheme: The AuthScheme object (APIKey)
        auth_credential: The AuthCredential object

    Returns:
        Tuple: (ApiParameter, Dict[str, Any])
    """
    if not auth_credential or not auth_credential.api_key:
        return None, None

    if auth_scheme.type_ == AuthSchemeType.apiKey:
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
            schema={"type": "string"},
            description=auth_scheme.description or "",
        )

        kwargs = {python_name: auth_credential.api_key}
        return param, kwargs
    else:
        raise ValueError("Invalid security scheme and credential combination")
