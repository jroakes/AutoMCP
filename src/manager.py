"""
Name: Core functionality manager.
Description: Contains core functionality for processing API configurations, generating tools from OpenAPI specs, preparing resource managers with documentation, and starting MCP servers. Orchestrates the different components of AutoMCP to create a complete MCP server.
"""

import json
import logging
import os
from typing import Dict, List

from fastmcp.prompts import Prompt

from .utils import load_spec_from_url, substitute_env_vars, ServerRegistry, ApiConfig
from .openapi.tools import OpenAPIToolkit
from .documentation.crawler import DocumentationCrawler
from .documentation.resources import ResourceManager
from .prompt.generator import PromptGenerator
from .models import MCPToolsetConfig
from .server.mcp import MCPServer
from .constants import (
    DEFAULT_DB_DIRECTORY,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_TYPE,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_RATE_LIMIT_DELAY,
    DEFAULT_HOST,
    DEFAULT_PORT,
)


logger = logging.getLogger(__name__)


def process_config(config_path: str) -> ApiConfig:
    """Process an API configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        API configuration
    """
    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Process environment variables in authentication before creating the ApiConfig
    if "authentication" in config_data:
        auth_config = config_data["authentication"]

        # Handle the main auth value
        if "value" in auth_config:
            auth_config["value"] = substitute_env_vars(auth_config["value"])

        # Also handle username/password if present (for basic auth)
        if "username" in auth_config:
            auth_config["username"] = substitute_env_vars(auth_config["username"])
        if "password" in auth_config:
            auth_config["password"] = substitute_env_vars(auth_config["password"])

        # Handle OAuth2 credentials if present
        if "client_id" in auth_config:
            auth_config["client_id"] = substitute_env_vars(auth_config["client_id"])
        if "client_secret" in auth_config:
            auth_config["client_secret"] = substitute_env_vars(
                auth_config["client_secret"]
            )

    api_config = ApiConfig(**config_data)

    # Load OpenAPI spec if URL is provided
    if api_config.openapi_spec_url and not api_config.openapi_spec:
        logger.debug(f"Loading OpenAPI spec from {api_config.openapi_spec_url}")
        api_config.openapi_spec = load_spec_from_url(api_config.openapi_spec_url)

    return api_config


def prepare_resource_manager(
    api_config: ApiConfig, db_directory: str
) -> ResourceManager:
    """Prepare a resource manager with crawled documentation.

    Args:
        api_config: API configuration
        db_directory: Directory to store the vector database

    Returns:
        ResourceManager instance with crawled documentation
    """
    logger.info("Preparing resource manager from documentation")

    # Skip if no documentation URL is provided
    if not api_config.documentation_url:
        logger.warning("No documentation URL provided, skipping resource preparation")
        return None

    # Create a ResourceManager instance
    resource_manager = ResourceManager(
        db_directory=db_directory,
        embedding_type=DEFAULT_EMBEDDING_TYPE,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        server_name=api_config.server_name,
    )

    # Crawl documentation if needed
    if resource_manager.is_empty():
        logger.info(f"Crawling documentation from {api_config.documentation_url}")

        # Set default crawler parameters
        max_pages = DEFAULT_MAX_PAGES
        max_depth = DEFAULT_MAX_DEPTH
        rendering = False

        # Get crawler config from api_config if available
        if api_config.crawl:
            # Get rendering setting (default: False if not specified)
            rendering = api_config.crawl.rendering

            # Get max_pages setting (default: 50 if not specified)
            if api_config.crawl.max_pages is not None:
                max_pages = api_config.crawl.max_pages

            # Get max_depth setting (default: 3 if not specified)
            if api_config.crawl.max_depth is not None:
                max_depth = api_config.crawl.max_depth

        crawler = DocumentationCrawler(
            base_url=api_config.documentation_url,
            resource_manager=resource_manager,
            max_pages=max_pages,
            max_depth=max_depth,
            rate_limit_delay=DEFAULT_RATE_LIMIT_DELAY,
            rendering=rendering,
        )
        crawler.crawl()
    else:
        logger.debug("Using existing crawled documentation")

    return resource_manager


def generate_prompts(
    api_config: ApiConfig, tools: List[Dict], resource_manager: ResourceManager
) -> List[Prompt]:
    """Generate Prompt objects from an API configuration."""
    logger.info("Generating prompts")

    # Get resources from resource manager
    resources = {}
    if resource_manager:
        # Convert list of resource dicts to a dict keyed by URI
        resource_list = resource_manager.list_resources()
        resources = {res["uri"]: res for res in resource_list}

    # Create generator
    generator = PromptGenerator(
        api_name=api_config.name,
        api_description=api_config.description,
        tools=tools,
        resources=resources,
        custom_prompts=api_config.prompts,
    )

    return generator.generate_prompts()


def create_mcp_config(
    api_config: ApiConfig, resource_manager: ResourceManager
) -> MCPToolsetConfig:
    """Create an MCP configuration for an API.

    Args:
        api_config: API configuration
        resource_manager: Resource manager with documentation

    Returns:
        MCP configuration
    """
    logger.info(f"Creating MCP configuration for {api_config.name}")


    # Generate tools
    toolkit = OpenAPIToolkit(
        api_config.openapi_spec,
        auth_config=api_config.authentication,
        rate_limit_config=api_config.rate_limits,
        retry_config=api_config.retry,
    )

    # Generate prompts
    prompts = generate_prompts(api_config, toolkit.get_tool_schemas(), resource_manager)

    # Create config
    return MCPToolsetConfig(
        name=api_config.name,
        api_description=api_config.description,
        openapi_spec=api_config.openapi_spec,
        toolkit=toolkit,
        resource_manager=resource_manager,
        prompts=prompts,
    )


def start_mcp_server(
    config_paths: List[str],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    debug: bool = False,
):
    """Start an MCP server with multiple API configurations.

    Args:
        config_paths: Paths to API configuration files
        host: Host to bind the server to
        port: Port to bind the server to
        debug: Whether to enable debug mode
    """
    from fastapi import FastAPI
    import uvicorn

    logger.info(
        f"Starting MCP server on {host}:{port} with {len(config_paths)} API configs"
    )

    # Get server registry for db paths
    registry = ServerRegistry()

    # Create the main app
    app = FastAPI(
        title="AutoMCP Server",
        description="MCP server for multiple APIs",
    )

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "apis": [os.path.basename(p).split(".")[0] for p in config_paths],
        }

    # Process each config and create MCP handlers
    for config_path in config_paths:

        # ---------------------------
        # Load and validate the config
        # ---------------------------

        api_config = process_config(config_path)

        # Canonical server_name from the ApiConfig
        server_name = api_config.server_name

        # ------------------------------------------------------
        # Determine database directory path - always use consistent path
        # ------------------------------------------------------
        # Check if there's a registered path in the registry, otherwise create standard path
        api_db_dir = registry.get_db_directory(server_name) or os.path.join(
            DEFAULT_DB_DIRECTORY, server_name
        )


        # --------------------------------------------------
        # Create a ResourceManager that matches the crawler
        # --------------------------------------------------

        resource_manager = ResourceManager(
            db_directory=api_db_dir,
            embedding_type=DEFAULT_EMBEDDING_TYPE,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name=server_name,
        )


        # Skip if resource DB doesn't exist (not crawled during add)
        if not resource_manager.exists():
            logger.warning(
                f"No crawled documentation found for {server_name}. Run 'automcp add' first."
            )
            continue

        else:
            logger.debug(
                f"Using existing resource manager for {server_name} from {api_db_dir}"
            )

        # Create MCP config
        mcp_config = create_mcp_config(api_config, resource_manager)

        # Create and mount MCP server at /{server_name}/mcp.
        server = MCPServer(
            mcp_config=mcp_config,
            host=host,
            port=port,
            debug=debug,
            db_directory=api_db_dir,
        )

        # Mount the FastMCP SSE sub-application at /{server_name}/mcp.
        app.mount(f"/{server_name}/mcp", server.mcp.sse_app())
        

        logger.info(
            f"Mounted MCP server for {api_config.name} at /{server_name}/mcp"
        )

    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
    )

