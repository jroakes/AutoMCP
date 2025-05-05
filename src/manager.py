"""
Name: Core functionality manager.
Description: Contains core functionality for processing API configurations, generating tools from OpenAPI specs, preparing resource managers with documentation, and starting MCP servers. Orchestrates the different components of AutoMCP to create a complete MCP server.
"""

import json
import logging
import os
from typing import Dict, List

from .utils import ApiConfig, load_spec_from_url, ServerRegistry
from .openapi.tools import OpenAPIToolkit
from .openapi.models import ApiAuthConfig, RateLimitConfig, RetryConfig
from .documentation.crawler import DocumentationCrawler
from .documentation.resources import ResourceManager
from .prompt.generator import PromptGenerator
from .mcp.config import MCPToolsetConfig
from .mcp.server import MCPServer, create_server_from_config
from .constants import (
    DEFAULT_DB_DIRECTORY,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_RATE_LIMIT_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_RETRY_STATUS_CODES,
    DEFAULT_REQUESTS_PER_MINUTE,
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


def substitute_env_vars(value: str) -> str:
    """Substitute environment variables in a string using Python's string formatting.

    Uses the {VAR_NAME} format to reference environment variables.

    Args:
        value: String potentially containing environment variable references like {VAR_NAME}

    Returns:
        String with environment variables substituted
    """
    if not value or not isinstance(value, str):
        return value

    # Only proceed if there are potential variables to substitute
    if "{" not in value:
        return value

    # Get all environment variables
    env_vars = dict(os.environ)

    try:
        # Apply formatting with all environment variables
        return value.format(**env_vars)
    except KeyError as e:
        # Log missing environment variables and leave the value unchanged
        logger.warning(f"Environment variable '{e}' referenced in '{value}' not found")
        return value
    except ValueError:
        # Handle invalid format strings
        logger.warning(f"Invalid format string: '{value}'")
        return value


def generate_tools(api_config: ApiConfig) -> List[Dict]:
    """Generate tools from an API configuration.

    Args:
        api_config: API configuration

    Returns:
        List of tool schemas
    """
    logger.info("Generating tools from OpenAPI spec")

    # Create auth config if authentication is provided, otherwise try to discover from spec
    auth_config = None
    if api_config.authentication:
        auth_data = api_config.authentication
        auth_type = auth_data.get("type")

        if auth_type == "apiKey":
            auth_config = ApiAuthConfig(
                type="apiKey",
                in_field=auth_data.get("in"),
                name=auth_data.get("name"),
                value=auth_data.get("value", ""),
            )
        elif auth_type == "http":
            scheme = auth_data.get("scheme")
            if scheme == "bearer":
                auth_config = ApiAuthConfig(
                    type="http",
                    scheme="bearer",
                    value=auth_data.get("value", ""),
                )
            elif scheme == "basic":
                username = auth_data.get("username")
                password = auth_data.get("password")
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
                        value=auth_data.get("value", ""),
                    )
        elif auth_type == "oauth2":
            token = auth_data.get("value")
            auth_config = ApiAuthConfig(
                type="oauth2",
                scheme="bearer",  # OAuth2 tokens are typically used as bearer tokens
                value=token,
                client_id=auth_data.get("client_id"),
                client_secret=auth_data.get("client_secret"),
                token_url=auth_data.get("token_url"),
                scope=auth_data.get("scope"),
                auto_refresh=auth_data.get("auto_refresh", False),
            )
    elif api_config.openapi_spec:
        # Try to discover authentication from the OpenAPI spec
        from .openapi.spec import OpenAPISpecParser

        parser = OpenAPISpecParser(api_config.openapi_spec)
        security_schemes = parser.get_security_schemes()
        security_reqs = parser.get_security_requirements()

        if security_reqs and security_schemes:
            # Use the first security requirement found (simplification)
            first_req_name = list(security_reqs[0].keys())[0]
            if first_req_name in security_schemes:
                scheme_info = security_schemes[first_req_name]
                scheme_type = scheme_info.get("type")
                logger.info(
                    f"Discovered '{scheme_type}' security scheme '{first_req_name}' from OpenAPI spec."
                )

                if scheme_type == "apiKey":
                    auth_config = ApiAuthConfig(
                        type="apiKey",
                        in_field=scheme_info.get("in"),
                        name=scheme_info.get("name"),
                        value="",  # User must provide via env var or config
                    )
                    logger.warning(
                        f"apiKey value for '{scheme_info.get('name')}' must be provided via config or environment variable."
                    )
                elif scheme_type == "http":
                    http_scheme = scheme_info.get("scheme")
                    auth_config = ApiAuthConfig(
                        type="http",
                        scheme=http_scheme,
                        value="",  # User must provide via env var or config
                    )
                    logger.warning(
                        f"Credential value for http '{http_scheme}' auth must be provided via config or environment variable."
                    )
                # Add other types like oauth2 if needed
                else:
                    logger.warning(
                        f"Unsupported security scheme type '{scheme_type}' discovered."
                    )
            else:
                logger.warning(
                    f"Security requirement '{first_req_name}' not found in defined schemes."
                )
        else:
            logger.info(
                "No authentication information found in config or OpenAPI spec."
            )

    # Create rate limit config if provided
    rate_limit_config = None
    if hasattr(api_config, "rate_limits") and api_config.rate_limits:
        rate_limit_config = RateLimitConfig(
            requests_per_minute=api_config.rate_limits.get(
                "per_minute", DEFAULT_REQUESTS_PER_MINUTE
            ),
            requests_per_hour=api_config.rate_limits.get("per_hour"),
            requests_per_day=api_config.rate_limits.get("per_day"),
            enabled=api_config.rate_limits.get("enabled", True),
        )

    # Create retry config if provided
    retry_config = None
    if hasattr(api_config, "retry") and api_config.retry:
        retry_config = RetryConfig(
            max_retries=api_config.retry.get("max_retries", DEFAULT_MAX_RETRIES),
            backoff_factor=api_config.retry.get(
                "backoff_factor", DEFAULT_BACKOFF_FACTOR
            ),
            retry_on_status_codes=api_config.retry.get(
                "retry_on_status_codes", DEFAULT_RETRY_STATUS_CODES
            ),
            enabled=api_config.retry.get("enabled", True),
        )

    # Create toolkit
    toolkit = OpenAPIToolkit(
        api_config.openapi_spec,
        auth_config=auth_config,
        rate_limit_config=rate_limit_config,
        retry_config=retry_config,
    )

    # Get tool schemas
    return toolkit.get_tool_schemas()


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
        embedding_type="openai",
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
            rendering = api_config.crawl.get("rendering", False)

            # Get max_pages setting (default: 50 if not specified)
            if "max_pages" in api_config.crawl:
                max_pages = api_config.crawl.get("max_pages")

            # Get max_depth setting (default: 3 if not specified)
            if "max_depth" in api_config.crawl:
                max_depth = api_config.crawl.get("max_depth")

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
) -> Dict:
    """Generate prompts from an API configuration.

    Args:
        api_config: API configuration
        tools: List of tool schemas
        resource_manager: Resource manager with documentation

    Returns:
        Dictionary of prompts
    """
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

    return generator.to_mcp_prompts()


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
    tools = generate_tools(api_config)

    # Get resources
    resources = {}
    if resource_manager:
        # Convert list of resource dicts to a dict keyed by URI
        resource_list = resource_manager.list_resources()
        resources = {res["uri"]: res for res in resource_list}

    # Generate prompts
    prompts = generate_prompts(api_config, tools, resource_manager)

    # Create config
    return MCPToolsetConfig(
        name=api_config.name,
        api_description=api_config.description,
        tools=tools,
        resources=resources,
        prompts=prompts,
        openapi_spec=api_config.openapi_spec,
        authentication=api_config.authentication,
        rate_limits=api_config.rate_limits,
        retry=api_config.retry,
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
        try:
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
                embedding_type="openai",
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                server_name=server_name,
            )

            # Skip if resource DB doesn't exist (not crawled during add)
            if not resource_manager.exists():
                logger.warning(
                    f"No crawled documentation found for {server_name}. Run 'automcp add' first."
                )
                resource_manager = None
            else:
                logger.debug(
                    f"Using existing resource manager for {server_name} from {api_db_dir}"
                )

            # Create MCP config
            mcp_config = create_mcp_config(api_config, resource_manager)

            # Create and mount MCP server at /{server_name}/mcp.
            server = MCPServer(
                config=mcp_config,
                host=host,
                port=port,
                debug=debug,
                db_directory=api_db_dir,
            )

            # Mount the FastMCP SSE sub-application at /{server_name}/mcp.
            app.mount(f"/{server_name}/mcp", server.mcp.sse_app())

            # Add search endpoint if resource manager is available
            if resource_manager:

                @app.get(f"/{server_name}/search")
                async def search_docs(
                    query: str,
                    config_name=server_name,
                    resource_manager=resource_manager,
                ):
                    """Search documentation."""
                    results = resource_manager.search_chunks(query)
                    return {"results": results}

            logger.info(
                f"Mounted MCP server for {api_config.name} at /{server_name}/mcp"
            )

        except Exception as e:
            logger.error(f"Error setting up MCP server for {config_path}: {e}")

    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
    )


def create_mcp_server_from_config_file(
    config_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    debug: bool = False,
    db_directory: str = DEFAULT_DB_DIRECTORY,
) -> MCPServer:
    """Create an MCP server from a configuration file.

    Args:
        config_path: Path to the configuration file
        host: Host for the server
        port: Port for the server
        debug: Whether to enable debug mode
        db_directory: Directory to store the vector database

    Returns:
        MCP server
    """
    # Process the configuration file
    api_config = process_config(config_path)

    # Determine the server name
    server_name = api_config.server_name

    # Determine the database directory
    api_db_directory = os.path.join(db_directory, server_name)

    # Create a resource manager and prepare it with documentation
    resource_manager = prepare_resource_manager(api_config, api_db_directory)

    # Create MCP config
    mcp_config = create_mcp_config(api_config, resource_manager)

    # Create and return the server
    return create_server_from_config(
        mcp_config=mcp_config,
        host=host,
        port=port,
        debug=debug,
        db_directory=api_db_directory,
    )
