"""
Name: Shared models.
Description: Contains models shared across multiple modules to avoid circular imports.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from fastmcp.prompts import Prompt

from .openapi.tools import OpenAPIToolkit
from .documentation.resources import ResourceManager


class MCPToolsetConfig(BaseModel):
    """Configuration for an MCP toolset."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    api_description: str
    openapi_spec: Optional[Dict] = None

    toolkit: OpenAPIToolkit
    resource_manager: ResourceManager
    prompts: List[Prompt]

    @property
    def server_name(self) -> str:
        """Get the standardized server name (lowercase with underscores).
        
        Returns:
            Standardized server name for use in URLs and file paths
        """
        return self.name.lower().replace(" ", "_") if self.name else "" 