"""
Name: MCP Configuration classes.
Description: Shared configuration types for MCP server implementation to avoid circular imports.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class MCPToolsetConfig(BaseModel):
    """Configuration for an MCP toolset."""

    name: str
    api_description: str
    tools: List[Dict]
    resources: Dict
    prompts: Dict

    # --- Runtime metadata (optional) ---
    # Keeping these in the config means we do not have to try to reverse-engineer
    # them later when a tool is actually executed.
    openapi_spec: Optional[Dict] = None
    authentication: Optional[Dict] = None  # Raw auth section from the ApiConfig
    rate_limits: Optional[Dict] = None  # Raw rate-limit section from the ApiConfig
    retry: Optional[Dict] = None  # Raw retry section from the ApiConfig
    
    @property
    def server_name(self) -> str:
        """Get the standardized server name (lowercase with underscores).
        
        Returns:
            Standardized server name for use in URLs and file paths
        """
        return self.name.lower().replace(" ", "_") if self.name else "" 