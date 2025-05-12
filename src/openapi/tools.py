"""
Name: OpenAPI tools.
Description: Implements RestApiTool and OpenAPIToolkit classes for creating LLM-compatible tools from OpenAPI specifications. Provides comprehensive support for authentication, rate limiting, retry logic, and pagination when making API requests.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
import tenacity
from fastmcp.tools.tool import Tool, _convert_to_content

from .spec import OpenAPISpecParser
from .auth import auth_helpers
from .models import (
    ApiParameter,
    ApiEndpoint,
    ApiAuthConfig,
    RateLimitConfig,
    RetryConfig,
)
from .utils import RateLimiter, RetryHandler

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
        """
        self.name = name
        self.description = description
        self.endpoint = endpoint
        self.base_url = base_url
        self.auth_config = auth_config
        self.auth_scheme = None
        self.auth_credential = None

        # Store configs
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.retry_config = retry_config or RetryConfig()

        # Setup auth scheme and credential using auth_helpers if auth_config is provided
        if auth_config:
            try:
                if auth_config.type == "apiKey":
                    self.auth_scheme, self.auth_credential = (
                        auth_helpers.token_to_scheme_credential(
                            token_type="apikey",
                            location=auth_config.in_field,
                            name=auth_config.name,
                            credential_value=auth_config.value,
                        )
                    )
                elif auth_config.type == "http":
                    # Handle HTTP auth (Basic or Bearer)
                    if auth_config.scheme == "basic":
                        # Handle basic auth with username and password
                        if hasattr(auth_config, "username") and hasattr(
                            auth_config, "password"
                        ):
                            self.auth_scheme, self.auth_credential = (
                                auth_helpers.token_to_scheme_credential(
                                    token_type="basic",
                                    username=auth_config.username,
                                    password=auth_config.password,
                                )
                            )
                        # Or with pre-formatted credential
                        elif hasattr(auth_config, "value"):
                            self.auth_scheme, self.auth_credential = (
                                auth_helpers.token_to_scheme_credential(
                                    token_type="basic",
                                    credential_value=auth_config.value,
                                )
                            )
                    elif auth_config.scheme == "bearer":
                        # Handle bearer token auth
                        self.auth_scheme, self.auth_credential = (
                            auth_helpers.token_to_scheme_credential(
                                token_type="bearer",
                                credential_value=auth_config.value,
                            )
                        )
                elif auth_config.type == "oauth2":
                    # Handle OAuth2 auth
                    self.auth_scheme, self.auth_credential = (
                        auth_helpers.token_to_scheme_credential(
                            token_type="oauth2",
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
            param_schema = param.schema_definition.copy()
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

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the API request (synchronous wrapper).

        Args:
            **kwargs: Parameters for the API request

        Returns:
            The API response
        """
        import anyio
        return anyio.run(self.execute_async, **kwargs)

    async def execute_async(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the API request asynchronously.

        Args:
            **kwargs: Parameters for the API request

        Returns:
            The API response
        """
        # Prepare URL with path parameters
        url = self.endpoint.path

        # Separate parameters by location
        path_params = {}
        query_params = {}
        header_params = {}
        body_params = {}

        # Process parameters by location
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

        # Add authentication if configured using auth_helpers - only for query params
        # (Headers are already handled by the shared client)
        if self.auth_scheme and self.auth_credential:
            try:
                api_param, auth_kwargs = auth_helpers.credential_to_param(
                    self.auth_scheme, self.auth_credential
                )
                if api_param and auth_kwargs and api_param.location == "query":
                    # Add query parameters
                    for param_name, param_value in auth_kwargs.items():
                        # Remove the internal prefix from auth_helpers
                        clean_name = param_name.replace(
                            auth_helpers.INTERNAL_AUTH_PREFIX, ""
                        )
                        query_params[clean_name] = param_value
            except ValueError as e:
                logger.error(f"Error applying auth: {e}")
        
        # Determine the HTTP method
        method = self.endpoint.method.lower()
        
        # Prepare JSON body if needed
        json_body = body_params if body_params else None
        
        # Execute the request using the toolkit's request method
        result = await self._toolkit.request(
            method, 
            url,
            params=query_params,
            headers=header_params,
            json=json_body
        )
        
        return result


class OpenAPIToolkit:
    """Toolkit for creating tools from an OpenAPI specification."""

    def __init__(
        self,
        spec: Dict[str, Any],
        auth_config: Optional[ApiAuthConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize an OpenAPI toolkit.

        Args:
            spec: OpenAPI specification as a dictionary
            auth_config: Authentication configuration
            rate_limit_config: Rate limiting configuration
            retry_config: Retry configuration

        Raises:
            ValueError: If authentication is required by the OpenAPI spec but not provided in config
        """
        self.spec_parser = OpenAPISpecParser(spec)
        self.base_url = self.spec_parser.get_base_url()
        
        # Validate authentication requirements
        security_schemes = self.spec_parser.get_security_schemes()
        security_reqs = self.spec_parser.get_security_requirements()
        
        if security_reqs and security_schemes:
            # Check if auth is required but not provided
            first_req_name = list(security_reqs[0].keys())[0]
            if first_req_name in security_schemes:
                scheme_info = security_schemes[first_req_name]
                scheme_type = scheme_info.get("type")
                
                # OAuth2 is not supported in this release
                if scheme_type == "oauth2":
                    raise ValueError("OAuth2 authentication is not supported in this release")
                
                # If auth is required but not provided, raise error
                if not auth_config:
                    if scheme_type == "apiKey":
                        raise ValueError(
                            f"API requires '{scheme_type}' authentication with key '{scheme_info.get('name')}' "
                            f"in {scheme_info.get('in')}, but no authentication config was provided"
                        )
                    elif scheme_type == "http":
                        raise ValueError(
                            f"API requires HTTP {scheme_info.get('scheme')} authentication, "
                            f"but no authentication config was provided"
                        )
                    else:
                        raise ValueError(
                            f"API requires '{scheme_type}' authentication, but no authentication config was provided"
                        )
                
                # Validate that the provided auth matches the required scheme
                if auth_config:
                    if scheme_type == "apiKey" and auth_config.type != "apiKey":
                        raise ValueError(
                            f"API requires apiKey authentication but config provided {auth_config.type}. "
                            f"Please update your configuration to use 'type': 'apiKey'"
                        )
                    elif scheme_type == "http" and auth_config.type != "http":
                        raise ValueError(
                            f"API requires HTTP authentication but config provided {auth_config.type}. "
                            f"For Bearer token authentication, use: "
                            f"{{'type': 'http', 'scheme': 'bearer', 'value': 'your-token-here'}} "
                            f"instead of apiKey type with Authorization header."
                        )
                    
                    # Further validation for apiKey
                    if scheme_type == "apiKey" and auth_config.type == "apiKey":
                        if auth_config.name != scheme_info.get("name") or auth_config.in_field != scheme_info.get("in"):
                            raise ValueError(
                                f"API requires apiKey '{scheme_info.get('name')}' in {scheme_info.get('in')}, "
                                f"but config specified '{auth_config.name}' in {auth_config.in_field}"
                            )
                    
                    # Further validation for HTTP
                    if scheme_type == "http" and auth_config.type == "http":
                        if auth_config.scheme != scheme_info.get("scheme"):
                            raise ValueError(
                                f"API requires HTTP {scheme_info.get('scheme')} authentication, "
                                f"but config specified HTTP {auth_config.scheme}"
                            ) 
        
        self.auth_config = auth_config
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.retry_config = retry_config or RetryConfig()
        
        # Set up centralized rate limiting and retry handling
        self._rate_limiter = RateLimiter(self.rate_limit_config)
        self._retry_handler = RetryHandler(self.retry_config)
        
        # Set up shared httpx client with auth
        self._headers, self._httpx_auth = auth_helpers.build_httpx_auth(auth_config)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            auth=self._httpx_auth,
            timeout=getattr(self.retry_config, "timeout", 30),
        )
        
        # Create tools
        self.tools = self._create_tools()

    async def aclose(self):
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()

    def _create_tools(self) -> List[RestApiTool]:
        """Create tools from the OpenAPI specification.

        Returns:
            List of REST API tools
        """
        tools = []
        endpoints = self.spec_parser.get_endpoints()

        for name, description, endpoint_spec in endpoints:
            method = name.split(" ", 1)[0].lower()

            # Only support GET and POST methods as per guidelines
            if method not in ["get", "post"]:
                logger.debug(
                    f"Skipping endpoint {name} as method '{method}' is not supported."
                )
                continue

            # Extract operation ID to use as a unique tool name
            operation_id = endpoint_spec.get("operationId")
            if not operation_id:
                # Generate an operation ID if not provided
                method, path = name.split(" ", 1)
                operation_id = f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"

            # Clean up path parameters
            path = name.split(" ", 1)[1]

            # Extract and transform parameters
            parameters = []
            for param_spec in endpoint_spec.get("parameters", []):
                param = ApiParameter(
                    name=param_spec["name"],
                    description=param_spec.get("description", ""),
                    required=param_spec.get("required", False),
                    location=param_spec["in"],
                    schema_definition=param_spec.get("schema", {}),
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
            )
            
            # Set toolkit reference for execute method to use
            tool._toolkit = self

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

    async def request(
        self, 
        method: str, 
        url: str, 
        *, 
        params=None, 
        headers=None, 
        json=None
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry and rate limiting.
        
        Args:
            method: HTTP method
            url: URL to request
            params: Query parameters
            headers: HTTP headers
            json: JSON body
            
        Returns:
            Parsed response data
        """
        # Check and wait for rate limit if needed
        await self._rate_limiter.consume_token_async()
        
        # Define retry decorator with retry handler's kwargs
        @tenacity.retry(**self._retry_handler.tenacity_kwargs())
        async def _do_request():
            response = await self._client.request(
                method, 
                url, 
                params=params, 
                headers=headers, 
                json=json
            )
            response.raise_for_status()
            
            # Parse response
            if response.content:
                try:
                    return response.json()
                except ValueError:
                    return {"text": response.text}
            else:
                return {
                    "status": "Success",
                    "status_code": response.status_code,
                }
                
        return await _do_request()


class FastMCPOpenAPITool(Tool):
    """Bridges RestApiTool -> FastMCP Tool object."""

    def __init__(self, rest_tool: RestApiTool):
        """Initialize a FastMCPOpenAPITool.
        
        Args:
            rest_tool: RestApiTool instance to wrap
        """
        super().__init__(
            name=rest_tool.name,
            description=rest_tool.description,
            parameters=rest_tool.to_schema()["parameters"],
            fn=self._run,
            context_kwarg="context",
        )
        self._rest_tool = rest_tool

    async def _run(self, **kwargs):
        """Execute the tool asynchronously.
        
        Args:
            **kwargs: Parameters for the tool
            
        Returns:
            Tool execution result as MCP-compatible content
        """
        # Call the async execution method directly
        raw = await self._rest_tool.execute_async(**kwargs)
        return _convert_to_content(raw)


async def execute_tool(
    tool_schema: Dict[str, Any], 
    toolkit: "OpenAPIToolkit", 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a tool using the OpenAPI toolkit.
    
    Args:
        tool_schema: Tool schema definition
        toolkit: OpenAPIToolkit instance
        parameters: Parameters for the tool
        
    Returns:
        The result of the tool execution
    """
    tool_name = tool_schema.get("name")
    if not tool_name:
        raise ValueError("Tool schema missing 'name' field")
    
    # Find the tool in the toolkit
    tool = toolkit.get_tool(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found in toolkit")
    
    # Execute the tool with parameters (using async method directly)
    result = await tool.execute_async(**parameters)
    return result
