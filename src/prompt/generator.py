"""
Name: Prompt generator.
Description: Provides PromptGenerator for creating MCP-compatible prompts from API configurations, tools, and resources. Generates standardized prompts for API overviews, tool usage guides, and resource usage guides.
"""

import logging
from typing import Dict, List, Optional

# FastMCP primitives
from fastmcp.prompts import Prompt
from fastmcp.prompts.prompt import PromptArgument

# Import shared template strings
from .templates import (
    API_OVERVIEW_TEMPLATE,
    TOOL_USAGE_GUIDE_TEMPLATE,
    RESOURCE_USAGE_GUIDE_TEMPLATE,
)

from pydantic import BaseModel

logger = logging.getLogger(__name__)



class PromptGenerator:
    """Generator for API tool prompts."""

    def __init__(
        self,
        api_name: str,
        api_description: str,
        tools: List[Dict],
        resources: Dict,
        custom_prompts: Optional[List[Dict[str, str]]] = None,
    ):
        """Initialize the prompt generator.

        Args:
            api_name: Name of the API
            api_description: Description of the API
            tools: List of tools as dictionaries
            resources: Dictionary of resources
            custom_prompts: Optional list of custom prompts from the config file
        """
        self.api_name = api_name
        self.api_description = api_description
        self.tools = tools
        self.resources = resources
        self.custom_prompts = custom_prompts or []

    # ---------------------------------------------------------------------
    # Prompt builders (return Prompt objects)
    # ---------------------------------------------------------------------

    def _build_api_overview_prompt(self) -> Prompt:
        """Return a *static* Prompt describing the API overview."""

        tool_names = [tool["name"] for tool in self.tools]
        content = API_OVERVIEW_TEMPLATE.format(
            api_name=self.api_name,
            api_description=self.api_description,
            tool_list=", ".join(tool_names),
        )

        def _overview_fn() -> str:  # pragma: no cover – trivial closure
            return content

        return Prompt(
            name="api_overview",
            description=f"Overview of the {self.api_name} API and its tools.",
            arguments=[],
            fn=_overview_fn,
        )

    def _build_tool_usage_guide_prompt(self) -> Prompt:
        """Return a *static* Prompt describing tool usage."""

        tool_names = [tool["name"] for tool in self.tools]
        content = TOOL_USAGE_GUIDE_TEMPLATE.format(
            api_name=self.api_name,
            tool_list=", ".join(tool_names),
        )

        def _tool_usage_fn() -> str:  # pragma: no cover
            return content

        return Prompt(
            name="tool_usage_guide",
            description="Guide to understanding and using the tools generated from OpenAPI specs",
            arguments=[],
            fn=_tool_usage_fn,
        )

    def _build_resource_usage_guide_prompt(self) -> Prompt:
        """Return a *static* Prompt describing resource usage."""

        resource_count = len(self.resources) if self.resources else 0
        content = RESOURCE_USAGE_GUIDE_TEMPLATE.format(
            api_name=self.api_name,
            resource_count=resource_count,
        )

        def _resource_usage_fn() -> str:  # pragma: no cover
            return content

        return Prompt(
            name="resource_usage_guide",
            description="Guide to understanding and using the resources created from crawled API documentation",
            arguments=[],
            fn=_resource_usage_fn,
        )

    def _build_custom_prompt(self, prompt_data: Dict[str, str], index: int) -> Prompt:
        """Convert an arbitrary prompt entry from the API config into a Prompt object."""

        prompt_name = prompt_data.get("name", f"Custom Prompt {index}")
        description = prompt_data.get("description", "")

        # If the prompt is conversation style (list of messages)
        if isinstance(prompt_data.get("content"), list):
            messages = prompt_data["content"]
            return Prompt(
                name=prompt_name.lower().replace(" ", "_"),
                description=description,
                arguments=[],
                fn=lambda messages=messages: messages,  # Capture messages in lambda
            )

        # Otherwise treat as template string (with optional variables)
        template_str = prompt_data.get("content", "")
        variables = prompt_data.get("variables", [])

        # Build PromptArguments (all required = True by default)
        arg_objs: List[PromptArgument] = [
            PromptArgument(name=v, description=f"Value for {v}", required=True)
            for v in variables
        ]

        if variables:
            # Create a template function that formats with kwargs
            return Prompt(
                name=prompt_name.lower().replace(" ", "_"),
                description=description,
                arguments=arg_objs,
                fn=lambda template_str=template_str, **kwargs: template_str.format(**kwargs),
            )

        # Static string prompt (no variables)
        return Prompt(
            name=prompt_name.lower().replace(" ", "_"),
            description=description,
            arguments=[],
            fn=lambda template_str=template_str: template_str,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_prompts(self) -> List[Prompt]:
        """Generate a list of Prompt objects for FastMCP."""

        # Create the static prompts directly from their templates
        api_overview = Prompt(
            name="api_overview",
            description=f"Overview of the {self.api_name} API and its tools.",
            arguments=[],
            fn=lambda: API_OVERVIEW_TEMPLATE.format(
                api_name=self.api_name,
                api_description=self.api_description,
                tool_list=", ".join([tool["name"] for tool in self.tools]),
            ),
        )
        
        tool_usage = Prompt(
            name="tool_usage_guide",
            description="Guide to understanding and using the tools generated from OpenAPI specs",
            arguments=[],
            fn=lambda: TOOL_USAGE_GUIDE_TEMPLATE.format(
                api_name=self.api_name,
                tool_list=", ".join([tool["name"] for tool in self.tools]),
            ),
        )
        
        resource_count = len(self.resources) if self.resources else 0
        resource_usage = Prompt(
            name="resource_usage_guide",
            description="Guide to understanding and using the resources created from crawled API documentation",
            arguments=[],
            fn=lambda: RESOURCE_USAGE_GUIDE_TEMPLATE.format(
                api_name=self.api_name,
                resource_count=resource_count,
            ),
        )
        
        prompts = [api_overview, tool_usage, resource_usage]

        # Custom prompts from API config
        for i, prompt_data in enumerate(self.custom_prompts):
            try:
                prompts.append(self._build_custom_prompt(prompt_data, i))
            except Exception as exc:  # pragma: no cover – defensive
                logger.warning("Failed to build custom prompt %s: %s", prompt_data, exc)

        return prompts

    # ------------------------------------------------------------------
    # Back-compat shim (to be removed once callers are updated)
    # ------------------------------------------------------------------

    def to_mcp_prompts(self) -> Dict[str, Prompt]:  # noqa: N802 – legacy name
        """Return prompts as a mapping for legacy callers.

        NOTE: The new preferred method is :py:meth:`generate_prompts` which
        returns a list of :class:`fastmcp.Prompt` objects.  This shim provides
        a minimal backwards-compatibility layer until all call-sites are
        migrated.
        """

        return {prompt.name: prompt for prompt in self.generate_prompts()}
