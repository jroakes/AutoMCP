"""Main module for AutoMCP."""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Optional

from .utils import ApiConfig, load_spec_from_url
from .openapi.tools import OpenAPIToolkit
from .openapi.models import ApiAuthConfig, RateLimitConfig, RetryConfig
from .documentation.crawler import DocumentationCrawler
from .documentation.resources import ResourceManager
from .prompt.generator import PromptGenerator
from .mcp.server import MCPServer, MCPToolsetConfig


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

    api_config = ApiConfig(**config_data)

    # Load OpenAPI spec if URL is provided
    if api_config.openapi_spec_url and not api_config.openapi_spec:
        logger.info(f"Loading OpenAPI spec from {api_config.openapi_spec_url}")
        api_config.openapi_spec = load_spec_from_url(api_config.openapi_spec_url)

    return api_config


def generate_tools(api_config: ApiConfig) -> List[Dict]:
    """Generate tools from an API configuration.

    Args:
        api_config: API configuration

    Returns:
        List of tool schemas
    """
    logger.info("Generating tools from OpenAPI spec")

    # Create auth config if authentication is provided
    auth_config = None
    if api_config.authentication:
        auth_type = api_config.authentication.get("type")
        if auth_type == "apiKey":
            auth_config = ApiAuthConfig(
                type="apiKey",
                in_field=api_config.authentication.get("in"),
                name=api_config.authentication.get("name"),
                value=api_config.authentication.get("value", ""),
            )
        elif (
            auth_type == "http" and api_config.authentication.get("scheme") == "bearer"
        ):
            auth_config = ApiAuthConfig(
                type="http",
                scheme="bearer",
                value=api_config.authentication.get("value", ""),
            )

    # Create rate limit config if provided
    rate_limit_config = None
    if hasattr(api_config, "rate_limits") and api_config.rate_limits:
        rate_limit_config = RateLimitConfig(
            requests_per_minute=api_config.rate_limits.get("per_minute", 60),
            requests_per_hour=api_config.rate_limits.get("per_hour"),
            requests_per_day=api_config.rate_limits.get("per_day"),
            enabled=api_config.rate_limits.get("enabled", True),
        )

    # Create retry config if provided
    retry_config = None
    if hasattr(api_config, "retry") and api_config.retry:
        retry_config = RetryConfig(
            max_retries=api_config.retry.get("max_retries", 3),
            backoff_factor=api_config.retry.get("backoff_factor", 0.5),
            retry_on_status_codes=api_config.retry.get(
                "retry_on_status_codes", [429, 500, 502, 503, 504]
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


def generate_resources(api_config: ApiConfig) -> Dict:
    """Generate resources from an API configuration.

    Args:
        api_config: API configuration

    Returns:
        Dictionary of resources
    """
    logger.info("Generating resources from documentation")

    # Skip if no documentation URL is provided
    if not api_config.documentation_url:
        logger.warning("No documentation URL provided, skipping resource generation")
        return {}

    # Get LLM API key from environment or config
    llm_api_key = os.environ.get("OPENAI_API_KEY")

    # Check if authentication has an LLM API key
    if api_config.authentication and "llm_api_key" in api_config.authentication:
        llm_api_key = api_config.authentication.get("llm_api_key")

    # Create a ResourceManager instance
    resource_manager = ResourceManager(
        db_directory="./.chromadb",
        embedding_type="openai",
        openai_api_key=llm_api_key,
        embedding_model="text-embedding-3-small",
    )

    # Crawl documentation
    logger.info(f"Crawling documentation from {api_config.documentation_url}")
    crawler = DocumentationCrawler(
        base_url=api_config.documentation_url,
        resource_manager=resource_manager,
        max_pages=50,  # Increase default to get more comprehensive coverage
        max_depth=3,
        rate_limit_delay=(1.0, 3.0),  # Add rate limiting to be respectful
        bypass_cache=False,  # Use cache by default
    )
    crawler.crawl()

    # Convert resources to MCP resource format
    return resource_manager.list_resources()


def generate_prompts(api_config: ApiConfig, tools: List[Dict], resources: Dict) -> Dict:
    """Generate prompts from an API configuration.

    Args:
        api_config: API configuration
        tools: List of tool schemas
        resources: Dictionary of resources

    Returns:
        Dictionary of prompts
    """
    logger.info("Generating prompts")

    # Create generator
    generator = PromptGenerator(
        api_name=api_config.name,
        api_description=api_config.description,
        tools=tools,
        resources=resources,
    )

    return generator.to_mcp_prompts()


def generate_mcp_config(
    api_config: ApiConfig, output_path: Optional[str] = None
) -> Dict:
    """Generate an MCP configuration from an API configuration.

    Args:
        api_config: API configuration
        output_path: Path to write the configuration to, or None to skip writing

    Returns:
        MCP configuration
    """
    logger.info("Generating MCP configuration")

    # Generate tools, resources, and prompts
    tools = generate_tools(api_config)
    resources = generate_resources(api_config)
    prompts = generate_prompts(api_config, tools, resources)

    # Create config
    config = {
        "api_name": api_config.name,
        "api_description": api_config.description,
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
    }

    # Write to file if output path is provided
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

    return config


def start_server(
    config: Dict, host: str = "0.0.0.0", port: int = 8000, debug: bool = False
):
    """Start an MCP server from a configuration.

    Args:
        config: MCP configuration
        host: Host to bind the server to
        port: Port to bind the server to
        debug: Whether to enable debug mode
    """
    logger.info(f"Starting MCP server on {host}:{port}")

    # Create config
    mcp_config = MCPToolsetConfig(**config)

    # Create server
    server = MCPServer(mcp_config, host, port, debug)

    # Start server
    server.start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AutoMCP - Build a tool from an OpenAPI spec"
    )
    parser.add_argument(
        "--config", type=str, required=True, help="Path to API configuration file"
    )
    parser.add_argument(
        "--output", type=str, help="Path to write MCP configuration file"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the server to"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--no-server", action="store_true", help="Skip starting the server"
    )

    args = parser.parse_args()

    try:
        # Process config
        api_config = process_config(args.config)

        # Generate MCP config
        mcp_config = generate_mcp_config(api_config, args.output)

        # Start server if not disabled
        if not args.no_server:
            start_server(mcp_config, args.host, args.port, args.debug)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
