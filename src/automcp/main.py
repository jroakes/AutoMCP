"""
Name: Command-line interface.
Description: Implements the command-line interface for AutoMCP with commands for adding APIs, listing servers, deleting servers, serving MCP instances, and installing for platforms like Claude. Provides a user-friendly way to interact with AutoMCP's core functionality.
"""

import argparse
import glob
import json
import logging
import os
import sys
import shutil
import ssl
from .manager import process_config, prepare_resource_manager, start_mcp_server
from .utils import ServerRegistry, setup_environment

# Resolve ssl certificate issues.  We are not dealing with YMYL data here.
ssl._create_default_https_context = ssl._create_unverified_context

# Setup environment (includes logging configuration)
setup_environment()

logger = logging.getLogger(__name__)


def add_command(args):
    """Add an API configuration to AutoMCP."""
    registry = ServerRegistry(args.registry_file)
    config_paths = []

    # Check if a directory was provided
    if os.path.isdir(args.config):
        # Find all JSON files in the directory
        config_paths = glob.glob(os.path.join(args.config, "*.json"))
        logger.debug(f"Found {len(config_paths)} configuration files in {args.config}")
    else:
        # Assume a single config file was provided
        config_paths = [args.config]

    for config_path in config_paths:
        try:
            # Get the API name from the filename or from the config
            config_name = os.path.basename(config_path).split(".")[0]

            # Process config
            api_config = process_config(config_path)

            # Use db_directory from config, args, or default based on API name
            if api_config.db_directory:
                db_directory = api_config.db_directory
            elif args.db_directory:
                db_directory = os.path.join(args.db_directory, config_name)
            else:
                db_directory = os.path.join("./.chromadb", config_name)

            # Initialize resource manager and crawl documentation
            prepare_resource_manager(api_config, db_directory=db_directory)

            # Register the API
            registry.add_server(config_name, os.path.abspath(config_path), db_directory)

            logger.info(f"Added and crawled documentation for {api_config.name}")
        except Exception as e:
            logger.error(f"Error adding API configuration for {config_path}: {e}")


def list_servers_command(args):
    """List all registered API servers."""
    registry = ServerRegistry(args.registry_file)
    servers = registry.list_servers()

    if not servers:
        print("No API servers registered.")
        return

    print(f"Found {len(servers)} registered API server(s):")
    for server in servers:
        print(f"  - {server['name']} (config: {server['config_path']})")
        print(f"    Database: {server['db_directory']}")
        print(f"    Added: {server['added_at']}")
        print("")


def delete_command(args):
    """Delete an API server from AutoMCP."""
    registry = ServerRegistry(args.registry_file)

    # Get server info before deleting
    server = registry.get_server(args.name)
    if not server:
        logger.error(f"No server found with name '{args.name}'")
        return

    # Delete server from registry
    success = registry.delete_server(args.name)

    if success:
        logger.info(f"Deleted server '{args.name}' from registry")

        # Optionally delete database directory
        if (
            args.clean
            and server.get("db_directory")
            and os.path.exists(server["db_directory"])
        ):
            try:
                shutil.rmtree(server["db_directory"])
                logger.info(f"Deleted database directory at {server['db_directory']}")
            except Exception as e:
                logger.error(f"Error deleting database directory: {e}")
    else:
        logger.error(f"Failed to delete server '{args.name}'")


def remove_command(args):
    """Remove an API server and its data from AutoMCP."""
    registry = ServerRegistry(args.registry_file)

    # Get server info before removing
    server = registry.get_server(args.name)
    if not server:
        logger.error(f"No server found with name '{args.name}'")
        return

    # Remove server from registry
    success = registry.delete_server(args.name)

    if success:
        logger.info(f"Removed server '{args.name}' from registry")

        # Always clean up database directory by default unless --keep-data is specified
        if (
            not args.keep_data
            and server.get("db_directory")
            and os.path.exists(server["db_directory"])
        ):
            try:
                shutil.rmtree(server["db_directory"])
                logger.info(f"Removed database directory at {server['db_directory']}")
            except Exception as e:
                logger.error(f"Error removing database directory: {e}")
    else:
        logger.error(f"Failed to remove server '{args.name}'")


def serve_command(args):
    """Start MCP server(s) for API configuration(s)."""
    registry = ServerRegistry(args.registry_file)

    if args.config:
        # Use specified config path(s)
        config_paths = []
        if os.path.isdir(args.config):
            # Find all JSON files in the directory
            config_paths = glob.glob(os.path.join(args.config, "*.json"))
            logger.debug(
                f"Found {len(config_paths)} configuration files in {args.config}"
            )
        else:
            # Assume a single config file was provided
            config_paths = [args.config]
    else:
        # Use all registered servers
        config_paths = registry.get_all_config_paths()
        if not config_paths:
            logger.error(
                "No registered servers found. Use 'automcp add' to add servers first."
            )
            return

    # Start the server with all configs
    start_mcp_server(
        config_paths=config_paths,
        host=args.host,
        port=args.port,
        debug=args.debug,
        db_directory=args.db_directory,
    )


def install_claude_command(args):
    """Install AutoMCP for Claude."""
    try:
        registry = ServerRegistry(args.registry_file)

        if args.config:
            # Use specified config path(s)
            config_paths = []
            if os.path.isdir(args.config):
                # Find all JSON files in the directory
                config_paths = glob.glob(os.path.join(args.config, "*.json"))
                logger.debug(
                    f"Found {len(config_paths)} configuration files in {args.config}"
                )
            else:
                # Assume a single config file was provided
                config_paths = [args.config]
        else:
            # Use all registered servers
            config_paths = registry.get_all_config_paths()
            if not config_paths:
                logger.error(
                    "No registered servers found. Use 'automcp add' to add servers first."
                )
                return

        # Generate Claude configuration
        tools = []

        for config_path in config_paths:
            # Get the API name from the filename
            api_name = os.path.basename(config_path).split(".")[0]

            # Add a tool for this API
            tools.append(
                {
                    "name": api_name,
                    "url": f"http://{args.host}:{args.port}/{api_name}/mcp",
                    "schema_version": "v1",
                }
            )

        claude_config = {"tools": tools}

        # Write Claude configuration
        with open(args.output, "w") as f:
            json.dump(claude_config, f, indent=2)

        logger.info(f"Claude configuration successfully written to {args.output}")
        logger.debug(
            f"To use with Claude, make sure your MCP server is running at {args.host}:{args.port}"
        )
    except Exception as e:
        logger.error(f"Error installing for Claude: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="AutoMCP - Build MCP servers from OpenAPI specs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    def add_registry_file_arg(parser):
        """Add registry file argument to parser."""
        parser.add_argument(
            "--registry-file",
            type=str,
            default="./.automcp/registry.json",
            help="Path to the server registry file",
        )

    def add_db_directory_arg(parser):
        """Add database directory argument to parser."""
        parser.add_argument(
            "--db-directory",
            type=str,
            default="./.chromadb",
            help="Directory to store the vector database",
        )

    # Common arguments
    registry_file_arg = add_registry_file_arg
    db_directory_arg = add_db_directory_arg

    # Add command (replaces crawl)
    add_parser = subparsers.add_parser("add", help="Add an API to AutoMCP")
    add_parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to API configuration file or directory with JSON configs",
    )
    db_directory_arg(add_parser)
    registry_file_arg(add_parser)

    # List servers command
    list_parser = subparsers.add_parser(
        "list-servers", help="List all registered API servers"
    )
    registry_file_arg(list_parser)

    # Replace Delete with Remove command
    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove an API server configuration and optionally its crawled data",
    )
    remove_parser.add_argument(
        "--name", type=str, required=True, help="Name of the API server to remove"
    )
    remove_parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Prevent deletion of the associated database directory",
    )
    registry_file_arg(remove_parser)

    # Keep the old delete command for backward compatibility (hidden from help)
    delete_parser = subparsers.add_parser("delete", help=argparse.SUPPRESS)
    delete_parser.add_argument(
        "--name", type=str, required=True, help="Name of the API server to delete"
    )
    delete_parser.add_argument(
        "--clean", action="store_true", help="Also delete the database directory"
    )
    registry_file_arg(delete_parser)

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start MCP server(s)")
    serve_parser.add_argument(
        "--config",
        type=str,
        required=False,
        help="Path to API configuration file or directory with JSON configs (optional, uses registry if not specified)",
    )
    serve_parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the server to"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to"
    )
    serve_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    db_directory_arg(serve_parser)
    registry_file_arg(serve_parser)

    # Install command
    install_parser = subparsers.add_parser(
        "install", help="Install AutoMCP for specific platforms"
    )
    install_subparsers = install_parser.add_subparsers(
        dest="platform", help="Platform to install for"
    )

    # Claude install command
    claude_parser = install_subparsers.add_parser("claude", help="Install for Claude")
    claude_parser.add_argument(
        "--config",
        type=str,
        required=False,
        help="Path to API configuration file or directory with JSON configs (optional, uses registry if not specified)",
    )
    claude_parser.add_argument(
        "--host", type=str, default="localhost", help="Host where MCP server is running"
    )
    claude_parser.add_argument(
        "--port", type=int, default=8000, help="Port where MCP server is running"
    )
    claude_parser.add_argument(
        "--output",
        type=str,
        default=".claude.json",
        help="Path to write Claude configuration file",
    )
    registry_file_arg(claude_parser)

    args = parser.parse_args()

    # Execute command
    if args.command == "add":
        add_command(args)
    elif args.command == "list-servers":
        list_servers_command(args)
    elif args.command == "delete":
        # For backward compatibility
        delete_command(args)
    elif args.command == "remove":
        remove_command(args)
    elif args.command == "serve":
        serve_command(args)
    elif args.command == "install" and args.platform == "claude":
        install_claude_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
