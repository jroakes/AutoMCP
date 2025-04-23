"""Common models for OpenAPI tools."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApiParameter(BaseModel):
    """Parameter for an API request."""

    name: str
    description: str = ""
    required: bool = False
    location: str  # path, query, header, cookie, body
    schema: Dict[str, Any] = {}


class ApiEndpoint(BaseModel):
    """Endpoint for an API request."""

    operation_id: str
    method: str  # get, post
    path: str
    summary: str = ""
    description: str = ""
    parameters: List[ApiParameter] = []
    response_schema: Optional[Dict[str, Any]] = None
    request_body: Optional[Dict[str, Any]] = None


class RateLimitConfig(BaseModel):
    """Rate limit configuration for API requests.

    This can be specified globally or per-endpoint.
    """

    requests_per_minute: int = Field(
        default=60, description="Maximum number of requests allowed per minute"
    )
    requests_per_hour: Optional[int] = Field(
        default=None, description="Maximum number of requests allowed per hour"
    )
    requests_per_day: Optional[int] = Field(
        default=None, description="Maximum number of requests allowed per day"
    )
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")


class RetryConfig(BaseModel):
    """Retry configuration for API requests.

    This can be specified globally or per-endpoint.
    """

    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    backoff_factor: float = Field(
        default=0.5,
        description="Exponential backoff factor (in seconds) between retries",
    )
    retry_on_status_codes: List[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger a retry",
    )
    enabled: bool = Field(default=True, description="Whether retries are enabled")


class PaginationConfig(BaseModel):
    """Pagination configuration for API requests.

    Handles different pagination mechanisms:
    - Link headers (RFC 5988)
    - Cursor-based pagination
    - Offset/limit-based pagination
    - Page-based pagination
    """

    enabled: bool = Field(default=True, description="Whether pagination is enabled")
    mechanism: str = Field(
        default="auto",
        description="Pagination mechanism: 'auto', 'link', 'cursor', 'offset', or 'page'",
    )
    max_pages: int = Field(
        default=5, description="Maximum number of pages to fetch when auto-paginating"
    )
    # For cursor-based pagination
    cursor_param: Optional[str] = Field(
        default=None, description="Name of the cursor/next token parameter"
    )
    cursor_response_field: Optional[str] = Field(
        default=None,
        description="Field in the response that contains the next cursor/token",
    )
    # For offset/limit pagination
    offset_param: Optional[str] = Field(
        default=None, description="Name of the offset parameter"
    )
    limit_param: Optional[str] = Field(
        default=None, description="Name of the limit parameter"
    )
    # For page-based pagination
    page_param: Optional[str] = Field(
        default=None, description="Name of the page parameter"
    )
    page_size_param: Optional[str] = Field(
        default=None, description="Name of the page size parameter"
    )
    # For response parsing
    results_field: Optional[str] = Field(
        default=None, description="Field in the response that contains the items array"
    )


class ApiAuthConfig(BaseModel):
    """Authentication configuration for an API."""

    type: str  # apiKey, http, oauth2, openIdConnect
    in_field: Optional[str] = None  # header, query
    name: Optional[str] = None
    scheme: Optional[str] = None  # bearer, basic
    value: Optional[str] = None  # actual credential
