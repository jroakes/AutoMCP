"""
Name: MCP server.
Description: Implements the MCPServer class that creates a FastMCP instance, registers tools from configurations, and handles exposing MCP functionality via FastMCP. Provides a unified interface for exposing API functionality as MCP tools.
"""

import logging
import os
from typing import Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from ..documentation.resources import ResourceManager
from ..openapi.tools import OpenAPIToolkit
from ..openapi.models import ApiAuthConfig, RateLimitConfig, RetryConfig
from ..prompt.formatter import format_template

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


class MCPServer:
    """MCP server for AutoMCP."""

    def __init__(
        self,
        config: MCPToolsetConfig,
        host: str = "0.0.0.0",
        port: int = 8000,
        debug: bool = False,
        db_directory: str = "./.chromadb",
        openai_api_key: Optional[str] = None,
    ):
        """Initialize the MCP server.

        Args:
            config: MCP toolset configuration
            host: Host to bind the server to
            port: Port to bind the server to
            debug: Whether to enable debug mode
            db_directory: Directory to store the vector database
            openai_api_key: OpenAI API key for embeddings
        """
        self.config = config
        self.host = host
        self.port = port
        self.debug = debug
        self.db_directory = db_directory

        # Get OpenAI API key from environment or config
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        # Create resource manager for documentation search
        self.resource_manager = self._create_resource_manager()

        # Create API toolkit
        self.api_toolkit = None

        # Create MCP FastMCP instance
        self.mcp = self._create_mcp_instance()

    def _create_resource_manager(self) -> ResourceManager:
        """Create a resource manager for documentation search.

        Returns:
            Resource manager
        """
        if not self.openai_api_key:
            logger.warning(
                "No OpenAI API key provided, disabling embedding functionality"
            )
            return None

        try:
            # Create resource manager
            return ResourceManager(
                db_directory=self.db_directory,
                embedding_type="openai",
                openai_api_key=self.openai_api_key,
                embedding_model="text-embedding-3-small",
                server_name=self.config.name.lower().replace(" ", "_"),
            )
        except Exception as e:
            logger.error(f"Error creating resource manager: {e}")
            return None

    def _create_mcp_instance(self) -> FastMCP:
        """Create an MCP instance for the server.

        Returns:
            FastMCP instance
        """
        # Create FastMCP instance
        mcp = FastMCP(name=self.config.name, description=self.config.api_description)

        # Register tools from config while avoiding the late-binding closure issue
        for tool_schema in self.config.tools:
            tool_name = tool_schema["name"]
            tool_description = tool_schema.get("description", "")
            parameters = tool_schema.get("parameters", {})

            handler = self._create_tool_handler(tool_name)

            # Capture the handler in the function default so each iteration keeps its own
            @mcp.tool(
                name=tool_name, description=tool_description, parameters=parameters
            )
            async def _dynamic_tool(_handler=handler, **kwargs):  # noqa: D401,E501
                """Dynamically generated tool handler (wrapper)."""
                return await _handler(**kwargs)

        # Add documentation search tool if resource manager is available
        if self.resource_manager:

            @mcp.tool(
                name="search_documentation",
                description=f"Search {self.config.name} documentation",
            )
            async def search_documentation(query: str):
                """Search documentation."""
                try:
                    if not self.resource_manager:
                        return {
                            "status": "error",
                            "message": "Documentation search is not available",
                        }

                    # Search for documentation chunks
                    results = self.resource_manager.search_chunks(query)

                    return {
                        "status": "success",
                        "results": results,
                    }
                except Exception as e:
                    logger.error(f"Error searching documentation: {e}")
                    return {"status": "error", "message": str(e)}

            # Register documentation search as a resource with template
            @mcp.resource("search://{query}")
            async def search_docs_resource(query: str):
                """Search documentation and return results as a resource."""
                try:
                    results = self.resource_manager.search_chunks(query)
                    # Format results as a well-structured document
                    content = f"# Search Results for: {query}\n\n"
                    for i, result in enumerate(results):
                        content += (
                            f"## Result {i+1}: {result.get('title', 'Untitled')}\n"
                        )
                        content += f"**Source:** {result.get('url', 'Unknown')}\n\n"
                        content += f"{result.get('content', '')}\n\n"
                        content += "---\n\n"
                    return content
                except Exception as e:
                    logger.error(f"Error accessing search resource: {e}")
                    return f"Error searching documentation: {str(e)}"

            # Register individual documentation pages as resources
            @mcp.resource("docs://{doc_id}")
            async def get_doc_resource(doc_id: str):
                """Get a specific documentation page by ID."""
                try:
                    # Get the document from the resource manager
                    resource = self.resource_manager.get_resource(doc_id)
                    if resource:
                        return resource.content
                    else:
                        return f"Documentation page with ID '{doc_id}' not found."
                except Exception as e:
                    logger.error(f"Error accessing doc resource: {e}")
                    return f"Error retrieving documentation: {str(e)}"

        # Register resources
        # for resource_name, resource_data in self.config.resources.items():
        #     # Assuming resource_data contains 'name', 'description', etc.
        #     # The actual content for static resources might need different handling
        #     # or might not be directly registered here if dynamically generated.
        #     # This loop seems redundant given the specific resource decorators above.
        #     # If list_resources returns static content, it should be added differently.
        #     logger.debug(f"Registering static resource: {resource_name}")
        #     # mcp.add_resource(uri=resource_name, content=...) # Example structure
        #     pass

        # Register prompts
        for prompt_name, prompt_data in self.config.prompts.items():
            # Check if prompt_data is a list of messages (conversation prompts)
            if isinstance(prompt_data, list):
                # For conversation-style prompts
                @mcp.prompt(name=prompt_name)
                def prompt_func():
                    return prompt_data

                # The decorator has already registered this prompt
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
                    mcp.prompt(name=prompt_name)(prompt_func)
                else:
                    # For simple prompts without variables
                    @mcp.prompt(name=prompt_name)
                    def prompt_func():
                        """Simple prompt without variables."""
                        return template

        return mcp

    def _initialize_api_toolkit(self):
        """Initialise the reusable OpenAPIToolkit instance for this server."""
        if self.api_toolkit is not None:
            return

        # Prefer the full spec provided in the config as it preserves servers / base_url.
        from ..openapi.spec import extract_openapi_spec_from_tool

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
                    # Extract username/password or use token directly
                    auth_value = auth_cfg_dict.get("value", "")
                    username = auth_cfg_dict.get("username", "")
                    password = auth_cfg_dict.get("password", "")

                    # If username and password are provided, they take precedence
                    if username and password:
                        auth_config = ApiAuthConfig(
                            type="http", scheme="basic", value=f"{username}:{password}"
                        )
                    else:
                        auth_config = ApiAuthConfig(
                            type="http",
                            scheme="basic",
                            value=auth_value,
                        )
            elif auth_type == "oauth2":
                # Handle OAuth2 tokens (assuming pre-acquired token)
                token = auth_cfg_dict.get("value", "")
                auth_config = ApiAuthConfig(
                    type="http",  # Use http/bearer as the actual transport mechanism
                    scheme="bearer",
                    value=token,
                )

                # Store additional OAuth2 fields for potential future use
                # (token acquisition, refresh, etc.)
                if "client_id" in auth_cfg_dict or "client_secret" in auth_cfg_dict:
                    logger.info(
                        "OAuth2 client credentials provided but not currently used for automatic token acquisition"
                    )

        rate_limit_config = (
            RateLimitConfig(
                requests_per_minute=rate_cfg_dict.get("per_minute", 60),
                requests_per_hour=rate_cfg_dict.get("per_hour"),
                requests_per_day=rate_cfg_dict.get("per_day"),
                enabled=rate_cfg_dict.get("enabled", True),
            )
            if rate_cfg_dict
            else None
        )

        retry_config = (
            RetryConfig(
                max_retries=retry_cfg_dict.get("max_retries", 3),
                backoff_factor=retry_cfg_dict.get("backoff_factor", 0.5),
                retry_on_status_codes=retry_cfg_dict.get(
                    "retry_on_status_codes", [429, 500, 502, 503, 504]
                ),
                enabled=retry_cfg_dict.get("enabled", True),
            )
            if retry_cfg_dict
            else None
        )

        self.api_toolkit = OpenAPIToolkit(
            spec=openapi_spec,
            auth_config=auth_config,
            rate_limit_config=rate_limit_config,
            retry_config=retry_config,
        )

    def _create_tool_handler(self, tool_name: str):
        """Create a handler function for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Handler function
        """
        # Find the tool in the config
        tool_schema = None
        for tool in self.config.tools:
            if tool["name"] == tool_name:
                tool_schema = tool
                break

        if not tool_schema:
            raise ValueError(f"Tool {tool_name} not found in config")

        # Create handler function
        async def handler(**kwargs):
            """Handle a tool call by forwarding to the API."""
            try:
                # Initialize API toolkit if not already initialized
                self._initialize_api_toolkit()

                # If we have a toolkit, use it to execute the API call
                if self.api_toolkit:
                    api_tool = self.api_toolkit.get_tool(tool_name)
                    if api_tool:
                        return api_tool.execute(**kwargs)

                # Fallback if toolkit or tool not available
                logger.warning(
                    f"Tool {tool_name} not found in API toolkit, using mock implementation"
                )
                return {
                    "status": "success",
                    "message": f"Tool {tool_name} executed with mock implementation",
                    "args": kwargs,
                }
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                return {"status": "error", "message": str(e)}

        return handler


def create_server_from_config(
    config_path: str,
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False,
    db_directory: str = "./.chromadb",
    openai_api_key: Optional[str] = None,
) -> "MCPServer":
    """Create an MCP server from a config file.

    Args:
        config_path: Path to the config file
        host: Host to bind the server to
        port: Port to bind the server to
        debug: Whether to enable debug mode
        db_directory: Directory to store the vector database
        openai_api_key: OpenAI API key for embeddings

    Returns:
        MCP server
    """
    import json

    # Load config
    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Create config
    config = MCPToolsetConfig(**config_data)

    # Create server
    server = MCPServer(
        config,
        host,
        port,
        debug,
        db_directory=db_directory,
        openai_api_key=openai_api_key,
    )

    return server
