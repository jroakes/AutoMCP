"""
Name: MCP Server.
Description: Provides the MCP Server implementation for serving API tools, resources, and prompts. Creates FastMCP instances and handles tool execution.
"""

import os
import logging
from fastmcp.resources import TextResource
from typing import Dict, List, Optional
from pydantic import BaseModel
from fastmcp import FastMCP

# Import the centralized formatter
from ..prompt import format_template
from ..documentation.resources import ResourceManager
from .config import MCPToolsetConfig
from ..openapi.spec import extract_openapi_spec_from_tool
from ..openapi.models import ApiAuthConfig, RateLimitConfig, RetryConfig
from ..openapi.tools import OpenAPIToolkit, execute_tool
from ..constants import (
    DEFAULT_DB_DIRECTORY,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_RETRY_STATUS_CODES,
)

logger = logging.getLogger(__name__)


class MCPToolsetConfig(BaseModel):
    """Configuration for an MCP toolset."""

    name: str
    api_description: str
    tools: List[Dict]
    resources: Dict
    prompts: Dict

    # --- Runtime metadata (optional) ---
    # Keeping these in the config means we do not have to try to reverse-engineer
    # them later when a tool is actually executed.
    openapi_spec: Optional[Dict] = None
    authentication: Optional[Dict] = None  # Raw auth section from the ApiConfig
    rate_limits: Optional[Dict] = None  # Raw rate-limit section from the ApiConfig
    retry: Optional[Dict] = None  # Raw retry section from the ApiConfig

    @property
    def server_name(self) -> str:
        """Get the standardized server name (lowercase with underscores).

        Returns:
            Standardized server name for use in URLs and file paths
        """
        return self.name.lower().replace(" ", "_") if self.name else ""


class MCPServer:
    """MCP Server implementation."""

    def __init__(
        self,
        config: MCPToolsetConfig,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        debug: bool = False,
        db_directory: str = DEFAULT_DB_DIRECTORY,
    ):
        """Initialize an MCP server.

        Args:
            config: MCP toolset configuration
            host: Host for the server
            port: Port for the server
            debug: Whether to enable debug mode
            db_directory: Directory to store the vector database
        """
        self.config = config
        self.host = host
        self.port = port
        self.debug = debug
        self.db_directory = db_directory

        # Initialize resource manager
        self.resource_manager = self._create_resource_manager()

        # Create FastMCP instance
        self.mcp = self._create_mcp_instance()

        # Initialize API toolkit for OpenAPI operations (when needed during execution)
        self.api_toolkit = None

    def _create_resource_manager(self) -> ResourceManager:
        """Create a resource manager for documentation search.

        Returns:
            Resource manager
        """

        return ResourceManager(
            db_directory=self.db_directory,
            embedding_type="openai",
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name=self.config.server_name,
        )

    def _create_mcp_instance(self) -> FastMCP:
        """Create a FastMCP instance for this server.

        Returns:
            FastMCP instance
        """
        # Create FastMCP instance
        mcp = FastMCP(self.config.name, description=self.config.api_description)

        # Register tools
        for tool in self.config.tools:
            tool_name = tool.get("name", "")
            tool_description = tool.get("description", "")
            if not tool_name:
                continue

            # Create a handler for this tool
            handler = self._create_tool_handler(tool_name)

            # Register the tool
            @mcp.tool(name=tool_name, description=tool_description)
            async def dynamic_tool(handler=handler, **kwargs):  # noqa: D401,E501
                """Dynamic tool handler."""
                return await handler(**kwargs)

        if self.resource_manager:

            @mcp.resource("search://{query}")
            async def search_docs_resource(query: str, limit: int = 5) -> dict:
                """Search documentation and return results matching the query string.

                Args:
                    query: The search query text
                    limit: Maximum number of results to return (default: 5)

                Returns:
                    Search results with metadata and content snippets
                """

                # Search for documentation chunks
                results = self.resource_manager.search_chunks(query, limit=limit)

                # Format results for consumption
                return {
                    "query": query,
                    "limit": limit,
                    "count": len(results),
                    "results": results,
                }

            @mcp.resource("docs://{doc_id}")
            async def get_doc_resource(doc_id: str):
                """Return the full text of a crawled documentation page."""

                resource = self.resource_manager.get_resource(doc_id)
                if resource:
                    return {
                        "content": resource.content,
                        "metadata": {
                            "title": resource.title,
                            "url": resource.url,  # The original HTTP URL
                            "doc_id": doc_id,
                        },
                    }
                return f"Documentation page '{doc_id}' not found."

            # Get the resources list directly from resource_manager
            resource_list = self.resource_manager.list_resources()

            # Loop through all resources returned by list_resources
            for resource_data in resource_list:
                uri = resource_data.get("uri")
                if uri:
                    # This is a static resource, register it
                    logger.debug(f"Registering static resource: {uri}")
                    text_res = TextResource(
                        uri=uri,
                        name=resource_data.get("name", ""),
                        description=resource_data.get("description", ""),
                        text=resource_data.get("content", ""),
                    )
                    mcp.add_resource(text_res)

        # Register prompts
        for prompt_name, prompt_data in self.config.prompts.items():
            # Check if prompt_data is a list of messages (conversation prompts)
            if isinstance(prompt_data, list):
                # For conversation-style prompts. If the last element is a
                # dict with a "description" key, treat it as metadata.
                desc = ""
                if prompt_data and isinstance(prompt_data[-1], dict):
                    desc = prompt_data[-1].get("description", "")

                @mcp.prompt(name=prompt_name, description=desc)
                def prompt_func():
                    return prompt_data

            else:
                # For template-style prompts
                template = prompt_data.get("template", "")
                variables = prompt_data.get("variables", [])
                description = prompt_data.get("description", "")

                if variables:
                    # For prompts with variables, create a function that takes those variables
                    # using partial instead of exec for safety
                    def create_prompt_func(template_str, doc_str):
                        """Create a prompt function with the given template and docstring."""

                        def prompt_wrapper(**kwargs):
                            """Wrapper function that will be assigned a dynamic docstring."""
                            return format_template(template_str, **kwargs)

                        # Set the docstring
                        prompt_wrapper.__doc__ = doc_str
                        return prompt_wrapper

                    # Create the prompt function
                    prompt_func = create_prompt_func(
                        template_str=template, doc_str=f"Prompt: {description}"
                    )

                    # Register with FastMCP
                    mcp.prompt(name=prompt_name, description=description)(prompt_func)
                else:
                    # For simple prompts without variables
                    @mcp.prompt(name=prompt_name, description=description)
                    def prompt_func():
                        """Simple prompt without variables."""
                        return template

        return mcp

    def _initialize_api_toolkit(self):
        """Initialise the reusable OpenAPIToolkit instance for this server."""
        if self.api_toolkit is not None:
            return

        openapi_spec = self.config.openapi_spec or extract_openapi_spec_from_tool(
            self.config.tools
        )

        if not openapi_spec:
            logger.warning(
                "Unable to obtain an OpenAPI specification for toolkit initialisation. Falling back to tool reconstruction which may be incomplete."
            )
            return

        # Map raw config dictionaries (if any) into concrete config models
        auth_cfg_dict = self.config.authentication or {}
        rate_cfg_dict = self.config.rate_limits or {}
        retry_cfg_dict = self.config.retry or {}

        # Construct auth config (if provided)
        auth_config = None
        if auth_cfg_dict:
            auth_type = auth_cfg_dict.get("type")
            if auth_type == "apiKey":
                auth_config = ApiAuthConfig(
                    type="apiKey",
                    in_field=auth_cfg_dict.get("in"),
                    name=auth_cfg_dict.get("name"),
                    value=auth_cfg_dict.get("value", ""),
                )
            elif auth_type == "http":
                scheme = auth_cfg_dict.get("scheme")
                if scheme == "bearer":
                    auth_config = ApiAuthConfig(
                        type="http",
                        scheme="bearer",
                        value=auth_cfg_dict.get("value", ""),
                    )
                elif scheme == "basic":
                    username = auth_cfg_dict.get("username")
                    password = auth_cfg_dict.get("password")
                    if username and password:
                        auth_config = ApiAuthConfig(
                            type="http",
                            scheme="basic",
                            username=username,
                            password=password,
                            value=f"{username}:{password}",
                        )
                    else:
                        auth_config = ApiAuthConfig(
                            type="http",
                            scheme="basic",
                            value=auth_cfg_dict.get("value", ""),
                        )
            elif auth_type == "oauth2":
                token = auth_cfg_dict.get("value")
                auth_config = ApiAuthConfig(
                    type="oauth2",
                    scheme="bearer",  # OAuth2 tokens are typically used as bearer tokens
                    value=token,
                    client_id=auth_cfg_dict.get("client_id"),
                    client_secret=auth_cfg_dict.get("client_secret"),
                    token_url=auth_cfg_dict.get("token_url"),
                    scope=auth_cfg_dict.get("scope"),
                    auto_refresh=auth_cfg_dict.get("auto_refresh", False),
                )

        # Construct rate limit config (if provided)
        rate_limit_config = None
        if rate_cfg_dict:
            rate_limit_config = RateLimitConfig(
                requests_per_minute=rate_cfg_dict.get(
                    "per_minute", DEFAULT_REQUESTS_PER_MINUTE
                ),
                requests_per_hour=rate_cfg_dict.get("per_hour"),
                requests_per_day=rate_cfg_dict.get("per_day"),
                enabled=rate_cfg_dict.get("enabled", True),
            )

        # Construct retry config (if provided)
        retry_config = None
        if retry_cfg_dict:
            retry_config = RetryConfig(
                max_retries=retry_cfg_dict.get("max_retries", DEFAULT_MAX_RETRIES),
                backoff_factor=retry_cfg_dict.get(
                    "backoff_factor", DEFAULT_BACKOFF_FACTOR
                ),
                retry_on_status_codes=retry_cfg_dict.get(
                    "retry_on_status_codes", DEFAULT_RETRY_STATUS_CODES
                ),
                enabled=retry_cfg_dict.get("enabled", True),
            )

        # Create toolkit
        self.api_toolkit = OpenAPIToolkit(
            openapi_spec,
            auth_config=auth_config,
            rate_limit_config=rate_limit_config,
            retry_config=retry_config,
        )

    def _create_tool_handler(self, tool_name: str):
        """Create a handler for a specific tool.

        Args:
            tool_name: Name of the tool to create a handler for

        Returns:
            Async function that handles tool execution
        """
        # Find the tool schema
        tool_schema = next(
            (tool for tool in self.config.tools if tool["name"] == tool_name), None
        )
        if not tool_schema:
            raise ValueError(f"Tool '{tool_name}' not found in configuration")

        # Create a handler function that will be returned
        async def handler(**kwargs):
            """Generic handler for tool execution."""
            # Ensure we have a properly initialised API toolkit
            if self.api_toolkit is None:
                self._initialize_api_toolkit()

            if self.api_toolkit is None:
                return {"error": "Unable to initialize API toolkit for tool execution"}

            # Execute the tool using the toolkit
            response = await execute_tool(
                tool_schema=tool_schema,
                toolkit=self.api_toolkit,
                parameters=kwargs,
            )
            return response

        return handler


def create_server_from_config(
    mcp_config: MCPToolsetConfig,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    debug: bool = False,
    db_directory: str = DEFAULT_DB_DIRECTORY,
) -> "MCPServer":
    """Create an MCP server from a configuration object.

    Args:
        mcp_config: MCP toolset configuration object
        host: Host for the server
        port: Port for the server
        debug: Whether to enable debug mode
        db_directory: Directory to store the vector database

    Returns:
        MCP server
    """
    # Create and return the server
    return MCPServer(
        config=mcp_config,
        host=host,
        port=port,
        debug=debug,
        db_directory=db_directory,
    )
