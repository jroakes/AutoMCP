"""
Name: Utility functions.
Description: Common utility functions for AutoMCP, including loading OpenAPI specs, managing server registries, and logging.
"""

import datetime
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any

import requests
import yaml
from pydantic import BaseModel

from .constants import DEFAULT_REGISTRY_FILE

# Configure logging
logger = logging.getLogger(__name__)


def configure_logging(debug: bool = False):
    """Configure logging for the application.

    Args:
        debug: Whether to enable debug mode
    """
    logging_level = logging.DEBUG if debug else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)

    # Check if handlers are already configured to prevent duplicates
    if root_logger.handlers:
        # Update existing handlers with the current log level
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging_level)
        return

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to the logger
    root_logger.addHandler(console_handler)


def load_spec_from_file(file_path: str) -> Dict[str, Any]:
    """Load OpenAPI spec from a file.

    Args:
        file_path: Path to the OpenAPI spec file

    Returns:
        Dict containing the OpenAPI spec
    """
    _, ext = os.path.splitext(file_path)
    with open(file_path, "r") as f:
        if ext.lower() in (".yaml", ".yml"):
            return yaml.safe_load(f)
        elif ext.lower() == ".json":
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")


def load_spec_from_url(url: str) -> Dict[str, Any]:
    """Load OpenAPI spec from a URL.

    Args:
        url: URL to the OpenAPI spec

    Returns:
        Dict containing the OpenAPI spec
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")

    if "application/json" in content_type:
        return response.json()
    elif "yaml" in content_type or url.endswith((".yaml", ".yml")):
        return yaml.safe_load(response.text)
    else:
        # Try to parse as JSON first, then fall back to YAML
        try:
            return response.json()
        except json.JSONDecodeError:
            try:
                return yaml.safe_load(response.text)
            except yaml.YAMLError:
                raise ValueError("Unable to parse response as JSON or YAML")


class ApiConfig(BaseModel):
    """Configuration for an API."""

    name: str
    display_name: Optional[str] = None
    description: str
    icon: Optional[str] = None
    version: Optional[str] = None
    documentation_url: Optional[str] = None
    openapi_spec_url: str
    openapi_spec: Optional[Dict[str, Any]] = None
    authentication: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    retry: Optional[Dict[str, Any]] = None
    crawl: Optional[Dict[str, Any]] = None
    prompts: Optional[List[Dict[str, str]]] = None

    @property
    def server_name(self) -> str:
        """Get the standardized server name (lowercase with underscores).

        Returns:
            Standardized server name for use in URLs and file paths
        """
        return self.name.lower().replace(" ", "_") if self.name else ""


class ServerRegistry:
    """Registry for managing API servers."""

    def __init__(self, registry_path: str = DEFAULT_REGISTRY_FILE):
        """Initialize the server registry.

        Args:
            registry_path: Path to the registry file
        """
        self.registry_path = registry_path
        self._ensure_registry_file()

    def _ensure_registry_file(self):
        """Ensure the registry file exists."""
        registry_dir = os.path.dirname(self.registry_path)
        if not os.path.exists(registry_dir):
            os.makedirs(registry_dir, exist_ok=True)

        if not os.path.exists(self.registry_path):
            # Create empty registry
            self._save_registry({})

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load the registry from file.

        Returns:
            Dictionary of server configurations
        """
        try:
            with open(self.registry_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_registry(self, registry: Dict[str, Dict[str, Any]]):
        """Save the registry to file.

        Args:
            registry: Dictionary of server configurations
        """
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    def add_server(self, name: str, config_path: str, db_directory: str):
        """Add or update a server in the registry.

        Args:
            name: Server name
            config_path: Path to the server config file
            db_directory: Path to the database directory
        """
        registry = self._load_registry()
        registry[name] = {
            "name": name,
            "config_path": config_path,
            "db_directory": db_directory,
            "added_at": str(datetime.datetime.now()),
        }
        self._save_registry(registry)

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered servers.

        Returns:
            List of server configurations
        """
        registry = self._load_registry()
        return list(registry.values())

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a server configuration by name.

        Args:
            name: Server name

        Returns:
            Server configuration, or None if not found
        """
        registry = self._load_registry()
        return registry.get(name)

    def delete_server(self, name: str) -> bool:
        """Delete a server from the registry.

        Args:
            name: Server name

        Returns:
            True if the server was deleted, False if not found
        """
        registry = self._load_registry()
        if name in registry:
            del registry[name]
            self._save_registry(registry)
            return True
        return False

    def get_all_config_paths(self) -> List[str]:
        """Get all registered config file paths.

        Returns:
            List of config file paths
        """
        registry = self._load_registry()
        return [server["config_path"] for server in registry.values()]

    def get_db_directory(self, name: str) -> Optional[str]:
        """Get the database directory for a server by name.

        Args:
            name: Server name

        Returns:
            Database directory path, or None if not found
        """
        server = self.get_server(name)
        if server:
            return server.get("db_directory")
        return None


def setup_environment():
    """Setup the environment for the application.

    - Loads environment variables from .env file
    - Downloads required NLTK resources
    - Configures logging
    """
    import nltk

    # Configure logging first
    configure_logging()

    try:
        from dotenv import load_dotenv

        load_dotenv()
        logger.debug("Loaded environment variables from .env file")
    except ImportError:
        logger.warning(
            "python-dotenv not installed. Environment variables will only be loaded from system."
        )

    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
