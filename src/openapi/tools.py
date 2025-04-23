"""Tools for interacting with OpenAPI-defined APIs."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi.openapi.models import APIKey, APIKeyIn

from .spec import OpenAPISpecParser
from .auth import auth_helpers
from .models import (
    ApiParameter,
    ApiEndpoint,
    ApiAuthConfig,
    RateLimitConfig,
    RetryConfig,
    PaginationConfig,
)
from .utils import RateLimiter, RetryHandler, PaginationHandler

logger = logging.getLogger(__name__)


class RestApiTool:
    """Tool for making requests to a REST API endpoint."""

    def __init__(
        self,
        name: str,
        description: str,
        endpoint: ApiEndpoint,
        base_url: str,
        auth_config: Optional[ApiAuthConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        pagination_config: Optional[PaginationConfig] = None,
    ):
        """Initialize a REST API tool.

        Args:
            name: Name of the tool
            description: Description of the tool
            endpoint: API endpoint details
            base_url: Base URL for the API
            auth_config: Authentication configuration
            rate_limit_config: Rate limiting configuration
            retry_config: Retry configuration
            pagination_config: Pagination configuration
        """
        self.name = name
        self.description = description
        self.endpoint = endpoint
        self.base_url = base_url
        self.auth_config = auth_config
        self.auth_scheme = None
        self.auth_credential = None

        # Set up rate limiting and retry handling
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.retry_config = retry_config or RetryConfig()
        self.pagination_config = pagination_config or PaginationConfig()
        self.rate_limiter = RateLimiter(self.rate_limit_config)
        self.retry_handler = RetryHandler(self.retry_config)
        self.pagination_handler = PaginationHandler(self.pagination_config)

        # Setup auth scheme and credential using auth_helpers if auth_config is provided
        if auth_config and auth_config.type == "apiKey":
            try:
                self.auth_scheme, self.auth_credential = (
                    auth_helpers.token_to_scheme_credential(
                        token_type="apikey",
                        location=auth_config.in_field,
                        name=auth_config.name,
                        credential_value=auth_config.value,
                    )
                )
            except ValueError as e:
                logger.error(f"Error setting up auth: {e}")

    def to_schema(self) -> Dict[str, Any]:
        """Convert the tool to a schema for LLM function calling.

        Returns:
            A schema for the tool
        """
        # Build parameter schema based on endpoint parameters
        properties = {}
        required = []

        for param in self.endpoint.parameters:
            param_schema = param.schema.copy()
            properties[param.name] = {
                "type": param_schema.get("type", "string"),
                "description": param.description,
            }

            # Add enum values if available
            if "enum" in param_schema:
                properties[param.name]["enum"] = param_schema["enum"]

            if param.required:
                required.append(param.name)

        # Add request body parameters if present
        if self.endpoint.request_body:
            content = self.endpoint.request_body.get("content", {})
            for content_type, content_schema in content.items():
                if "application/json" in content_type:
                    schema = content_schema.get("schema", {})
                    if "properties" in schema:
                        for prop_name, prop_schema in schema["properties"].items():
                            properties[prop_name] = prop_schema
                            if "required" in schema and prop_name in schema["required"]:
                                required.append(prop_name)

        # Build the complete schema
        schema = {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

        return schema

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the API request with retry and rate limiting.

        Args:
            **kwargs: Parameters for the API request

        Returns:
            The API response
        """
        # Check rate limits before making the request
        wait_time = self.rate_limiter.wait_time_seconds()
        if wait_time > 0:
            logger.info(
                f"Rate limit reached. Waiting {wait_time:.2f} seconds before making request."
            )
            time.sleep(wait_time)

        # Prepare URL with path parameters
        url = f"{self.base_url}{self.endpoint.path}"

        # Separate parameters by location
        path_params = {}
        query_params = {}
        header_params = {}
        body_params = {}

        for param in self.endpoint.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                if param.location == "path":
                    path_params[param.name] = value
                elif param.location == "query":
                    query_params[param.name] = value
                elif param.location == "header":
                    header_params[param.name] = value
                elif param.location == "body":
                    body_params[param.name] = value

        # Format URL with path parameters
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))

        # Add authentication if configured using auth_helpers
        if self.auth_scheme and self.auth_credential:
            try:
                api_param, auth_kwargs = auth_helpers.credential_to_param(
                    self.auth_scheme, self.auth_credential
                )
                if api_param and auth_kwargs:
                    # Extract the auth parameter and add it to the appropriate location
                    for param_name, param_value in auth_kwargs.items():
                        # Remove the internal prefix from auth_helpers
                        clean_name = param_name.replace(
                            auth_helpers.INTERNAL_AUTH_PREFIX, ""
                        )
                        if api_param.location == "header":
                            header_params[clean_name] = param_value
                        elif api_param.location == "query":
                            query_params[clean_name] = param_value
            except ValueError as e:
                logger.error(f"Error applying auth: {e}")

        # If pagination is enabled, prepare for collecting paginated responses
        paginated_responses = []
        current_page = 0
        current_query_params = query_params.copy()
        current_url = url

        while True:
            # Implement retry loop with exponential backoff
            attempt = 0
            while True:
                try:
                    # Consume a rate limit token
                    self.rate_limiter.consume_token()

                    # Make the request
                    method = self.endpoint.method.lower()
                    if method == "get":
                        response = requests.get(
                            current_url,
                            params=current_query_params,
                            headers=header_params,
                            timeout=30,
                        )
                    elif method == "post":
                        response = requests.post(
                            current_url,
                            params=current_query_params,
                            headers=header_params,
                            json=body_params if body_params else None,
                            timeout=30,
                        )
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    # Check status code and raise for retry if needed
                    if self.retry_handler.should_retry(response.status_code, attempt):
                        attempt += 1
                        backoff_time = self.retry_handler.get_backoff_time(attempt)
                        logger.info(
                            f"Request failed with status {response.status_code}. "
                            f"Retrying in {backoff_time:.2f} seconds (attempt {attempt}/{self.retry_config.max_retries})"
                        )
                        time.sleep(backoff_time)
                        continue

                    # Raise for other error status codes
                    response.raise_for_status()

                    # Parse response
                    if response.content:
                        try:
                            response_data = response.json()
                        except ValueError:
                            response_data = {"text": response.text}
                    else:
                        response_data = {
                            "status": "Success",
                            "status_code": response.status_code,
                        }

                    # Add response to paginated responses if pagination is enabled
                    if self.pagination_config.enabled:
                        paginated_responses.append(response_data)

                        # Get parameters for next page
                        next_page_params = (
                            self.pagination_handler.prepare_next_page_params(
                                original_params=current_query_params,
                                current_page=current_page,
                                response_data=response_data,
                                response_headers=dict(response.headers),
                            )
                        )

                        if next_page_params:
                            current_page += 1

                            # Handle special case where we have a full URL from Link header
                            if "_pagination_next_url" in next_page_params:
                                current_url = next_page_params["_pagination_next_url"]
                                current_query_params = (
                                    {}
                                )  # Clear query params as they're in the URL
                            else:
                                current_query_params = next_page_params

                            # Continue to next page
                            break
                        else:
                            # No more pages, combine results and return
                            if len(paginated_responses) > 1:
                                return self.pagination_handler.combine_results(
                                    paginated_responses
                                )
                            else:
                                return response_data
                    else:
                        # Pagination not enabled, return single response
                        return response_data

                except requests.exceptions.RequestException as e:
                    if (
                        attempt < self.retry_config.max_retries
                        and self.retry_config.enabled
                    ):
                        attempt += 1
                        backoff_time = self.retry_handler.get_backoff_time(attempt)
                        logger.info(
                            f"Request failed with error: {str(e)}. "
                            f"Retrying in {backoff_time:.2f} seconds (attempt {attempt}/{self.retry_config.max_retries})"
                        )
                        time.sleep(backoff_time)
                    else:
                        logger.error(
                            f"Request failed after {attempt} attempts: {str(e)}"
                        )
                        raise

            # If we got here and are not paginating, break the loop
            if not self.pagination_config.enabled:
                break

        # This should only be reached if pagination is enabled but no results were found
        if paginated_responses:
            return self.pagination_handler.combine_results(paginated_responses)
        else:
            return {"error": "No response data available"}


class OpenAPIToolkit:
    """Toolkit for creating tools from an OpenAPI specification."""

    def __init__(
        self,
        spec: Dict[str, Any],
        auth_config: Optional[ApiAuthConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        pagination_config: Optional[PaginationConfig] = None,
    ):
        """Initialize an OpenAPI toolkit.

        Args:
            spec: OpenAPI specification as a dictionary
            auth_config: Authentication configuration
            rate_limit_config: Rate limiting configuration
            retry_config: Retry configuration
            pagination_config: Pagination configuration
        """
        self.spec_parser = OpenAPISpecParser(spec)
        self.base_url = self.spec_parser.get_base_url()
        self.auth_config = auth_config
        self.rate_limit_config = rate_limit_config
        self.retry_config = retry_config
        self.pagination_config = pagination_config
        self.tools = self._create_tools()

    def _create_tools(self) -> List[RestApiTool]:
        """Create tools from the OpenAPI specification.

        Returns:
            List of REST API tools
        """
        tools = []
        endpoints = self.spec_parser.get_endpoints()

        for name, description, endpoint_spec in endpoints:
            # Extract operation ID to use as a unique tool name
            operation_id = endpoint_spec.get("operationId")
            if not operation_id:
                # Generate an operation ID if not provided
                method, path = name.split(" ", 1)
                operation_id = f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"

            # Clean up path parameters
            path = name.split(" ", 1)[1]
            method = name.split(" ", 1)[0].lower()

            # Extract and transform parameters
            parameters = []
            for param_spec in endpoint_spec.get("parameters", []):
                param = ApiParameter(
                    name=param_spec["name"],
                    description=param_spec.get("description", ""),
                    required=param_spec.get("required", False),
                    location=param_spec["in"],
                    schema=param_spec.get("schema", {}),
                )
                parameters.append(param)

            # Extract request body if present
            request_body = None
            if "requestBody" in endpoint_spec:
                request_body = endpoint_spec["requestBody"]

            # Extract response schema if present
            response_schema = None
            if "responses" in endpoint_spec and "200" in endpoint_spec["responses"]:
                response_schema = endpoint_spec["responses"]["200"].get("schema")

            # Create an ApiEndpoint object
            api_endpoint = ApiEndpoint(
                operation_id=operation_id,
                method=method,
                path=path,
                summary=endpoint_spec.get("summary", ""),
                description=endpoint_spec.get("description", ""),
                parameters=parameters,
                request_body=request_body,
                response_schema=response_schema,
            )

            # Create a RestApiTool
            tool = RestApiTool(
                name=operation_id,
                description=description or endpoint_spec.get("summary", ""),
                endpoint=api_endpoint,
                base_url=self.base_url,
                auth_config=self.auth_config,
                rate_limit_config=self.rate_limit_config,
                retry_config=self.retry_config,
                pagination_config=self.pagination_config,
            )

            tools.append(tool)

        return tools

    def get_tools(self) -> List[RestApiTool]:
        """Get all tools from the toolkit.

        Returns:
            A list of REST API tools
        """
        return self.tools

    def get_tool(self, name: str) -> Optional[RestApiTool]:
        """Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            The tool if found, None otherwise
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools.

        Returns:
            A list of tool schemas
        """
        return [tool.to_schema() for tool in self.tools]
