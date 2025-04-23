"""MCP server for AutoMCP."""

import logging
import os
from typing import Dict, List, Optional

import fastmcp
from fastapi import FastAPI, Request
from pydantic import BaseModel

from ..documentation.resources import ResourceManager

logger = logging.getLogger(__name__)


class MCPToolsetConfig(BaseModel):
    """Configuration for an MCP toolset."""

    api_name: str
    api_description: str
    tools: List[Dict]
    resources: Dict
    prompts: Dict


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

        # Get OpenAI API key from environment if not provided
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        # Create resource manager for documentation search
        self.resource_manager = self._create_resource_manager()

        # Create FastAPI app
        self.app = FastAPI(
            title=f"{config.api_name} MCP Server",
            description=f"MCP server for {config.api_name} API",
        )

        # Create MCP handler
        self.mcp_handler = self._create_mcp_handler()

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
            )
        except Exception as e:
            logger.error(f"Error creating resource manager: {e}")
            return None

    def _create_mcp_handler(self) -> fastmcp.MCPHandler:
        """Create an MCP handler for the server.

        Returns:
            MCP handler
        """
        # Create tools
        tools = {}
        for tool_schema in self.config.tools:
            tool_name = tool_schema["name"]
            tools[tool_name] = {
                "handler": self._create_tool_handler(tool_name),
                "schema": tool_schema,
            }

        # Add documentation search tool if resource manager is available
        if self.resource_manager:
            search_tool = {
                "name": "search_documentation",
                "description": f"Search {self.config.api_name} documentation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for in documentation",
                        }
                    },
                    "required": ["query"],
                },
            }
            tools["search_documentation"] = {
                "handler": self._create_search_handler(),
                "schema": search_tool,
            }

            # Add the search tool to the config
            self.config.tools.append(search_tool)

        # Create handler
        handler = fastmcp.MCPHandler(
            tools=tools, resources=self.config.resources, prompts=self.config.prompts
        )

        return handler

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
        async def handler(request: Request, **kwargs):
            """Handle a tool call."""
            try:
                # This is a placeholder. In a real implementation, this would call
                # the actual API client to execute the request.
                logger.info(f"Executing tool {tool_name} with args: {kwargs}")

                # For now, just return a dummy response
                return {
                    "status": "success",
                    "message": f"Tool {tool_name} executed successfully",
                    "args": kwargs,
                }
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                return {"status": "error", "message": str(e)}

        return handler

    def _create_search_handler(self):
        """Create a handler function for documentation search.

        Returns:
            Handler function
        """

        async def search_documentation_handler(request: Request, query: str):
            """Handle a documentation search."""
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

        return search_documentation_handler

    def start(self):
        """Start the MCP server."""
        # Mount the MCP handler
        self.app.mount("/mcp", self.mcp_handler.app)

        # Add a simple health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {"status": "ok"}

        # Add documentation search endpoint
        if self.resource_manager:

            @self.app.get("/search")
            async def search_docs(query: str):
                """Search documentation."""
                results = self.resource_manager.search_chunks(query)
                return {"results": results}

        # Start the server
        import uvicorn

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="debug" if self.debug else "info",
        )


def create_server_from_config(
    config_path: str,
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False,
    db_directory: str = "./.chromadb",
    openai_api_key: Optional[str] = None,
):
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
