"""Utility functions for AutoMCP."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import yaml
import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
