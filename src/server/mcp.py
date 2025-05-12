"""
Name: MCP Server.
Description: Provides the MCP Server implementation for serving API tools, resources, and prompts. Creates FastMCP instances and handles tool execution.
"""

import logging
from fastmcp import FastMCP
from fastmcp.resources import TextResource
import urllib.parse

# Import the centralized formatter
from ..models import MCPToolsetConfig
from ..openapi.tools import FastMCPOpenAPITool
from ..constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
)

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation."""

    def __init__(
        self,
        mcp_config: MCPToolsetConfig,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        debug: bool = False,
        db_directory: str = None,
    ):
        """Initialize an MCP server.

        Args:
            mcp_config: MCP toolset configuration
            host: Host for the server
            port: Port for the server
            debug: Whether to enable debug mode
            db_directory: Directory to store the vector database (optional)
        """
        self.mcp_config = mcp_config
        self.host = host
        self.port = port
        self.debug = debug
        self.db_directory = db_directory

        # Get resource manager and toolkit directly from mcp_config
        self.resource_manager = self.mcp_config.resource_manager
        self.api_toolkit = self.mcp_config.toolkit

        # Create FastMCP instance
        self.mcp = self._create_mcp_instance()


    def _create_mcp_instance(self) -> FastMCP:
        """Create a FastMCP instance for this server.

        Returns:
            FastMCP instance
        """
        # Create FastMCP instance
        mcp = FastMCP(self.mcp_config.name, description=self.mcp_config.api_description)

        # Register tools - using FastMCPOpenAPITool instead of dynamic functions
        if self.api_toolkit:
            # Get tool schemas from the toolkit
            tool_schemas = self.api_toolkit.get_tool_schemas()
            
            for tool_schema in tool_schemas:
                tool_name = tool_schema.get("name", "")
                if not tool_name:
                    continue

                # Get the corresponding RestApiTool from the toolkit
                rest_tool = self.api_toolkit.get_tool(tool_name)
                if not rest_tool:
                    logger.warning(f"RestApiTool for '{tool_name}' not found in toolkit")
                    continue

                mcp_tool = FastMCPOpenAPITool(rest_tool)
                mcp._tool_manager._tools[tool_name] = mcp_tool
                logger.debug(f"Registered tool: {tool_name}")

        if self.resource_manager:
            # Define search_docs_resource function
            async def search_docs_resource(query: str, limit: int = 5) -> TextResource:
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
                results_data = {
                    "query": query,
                    "limit": limit,
                    "count": len(results),
                    "results": results,
                }
                
                # Use URL encoding for the query part of the URI
                encoded_query = urllib.parse.quote(query)
                resource_uri = f"search:{encoded_query}" 
                
                # Return as TextResource, provide a name
                return TextResource(
                    name=f"Search Results for '{query}'", # Provide a name
                    uri=resource_uri,
                    text=str(results_data)
                )

            # Add as a resource using explicit method
            # Using a placeholder name in the URI template for FastMCP registration
            mcp.add_resource_fn(search_docs_resource, "search://{query}", description="Search the API documentation.")

            # Define get_doc_resource function
            async def get_doc_resource(doc_id: str) -> TextResource:
                """Return the full text of a crawled documentation page."""
                resource = self.resource_manager.get_resource(doc_id)
                resource_uri = f"docs:{doc_id}" # Use docs: scheme
                if resource:
                    content = {
                        "content": resource.content,
                        "metadata": {
                            "title": resource.title,
                            "url": resource.url,  # The original HTTP URL
                            "doc_id": doc_id,
                        },
                    }
                    return TextResource(
                        name=resource.title or f"Document {doc_id}", # Provide name
                        uri=resource_uri,
                        text=str(content)
                    )
                
                return TextResource(
                    name=f"Document {doc_id}", # Provide name
                    uri=resource_uri,
                    text=f"Documentation page '{doc_id}' not found."
                )

            # Add as a resource using explicit method
            # Using docs: scheme for registration
            mcp.add_resource_fn(get_doc_resource, "docs:{doc_id}")

            # Get the resources list directly from resource_manager
            resource_list = self.resource_manager.list_resources()

            # Loop through all resources returned by list_resources
            for resource_data in resource_list:
                uri = resource_data.get("uri")
                if uri:
                    # This is a static resource, register it
                    logger.debug(f"Registering static resource: {uri}")
                    
                    # Create TextResource object and add it using add_resource
                    text_res = TextResource(
                        uri=uri,
                        text=resource_data.get("content", ""),
                        name=resource_data.get("name", ""),
                        description=resource_data.get("description", ""),
                    )
                    
                    mcp.add_resource(text_res)


        # Register prompts (already constructed as Prompt objects)
        for prompt_obj in self.mcp_config.prompts:

            # mcp.add_prompt routes _prompt_manager.to add_prompt_from_fn
            mcp._prompt_manager.add_prompt(prompt_obj)

        return mcp

