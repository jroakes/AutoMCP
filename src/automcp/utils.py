"""
Name: Utility functions.
Description: Provides utility functions for loading OpenAPI specs from files or URLs, defining the ApiConfig model for API configurations, and implementing the ServerRegistry for managing API server registrations. Offers core functionality used across the AutoMCP system.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import datetime

import yaml
import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def configure_logging(debug: bool = False):
    """Configure logging for the entire application.

    Args:
        debug: If True, set logging level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if debug:
        logging.getLogger("automcp").setLevel(logging.DEBUG)
        logging.getLogger("openapi").setLevel(logging.DEBUG)
    else:
        logging.getLogger("automcp").setLevel(logging.INFO)
        logging.getLogger("openapi").setLevel(logging.INFO)
        # Set documentation resources to DEBUG even in non-debug mode

    # Set chromadb logger to WARNING to reduce logging
    logging.getLogger("chromadb").setLevel(logging.WARNING)

    # Set NLTK logger to be less verbose
    logging.getLogger("nltk").setLevel(logging.WARNING)

    # Set httpx logger to WARNING to reduce HTTP request logging
    logging.getLogger("httpx").setLevel(logging.WARNING)


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
    db_directory: Optional[str] = None
    crawl: Optional[Dict[str, Any]] = None
    prompts: Optional[List[Dict[str, str]]] = None


class ServerRegistry:
    """Registry for managing API servers."""

    def __init__(self, registry_path: str = "./.automcp/registry.json"):
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

    - Downloads required NLTK resources
    - Configures logging
    """
    import nltk

    configure_logging()

    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
