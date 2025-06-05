"""
Name: Prompt generator.
Description: Provides PromptGenerator for creating MCP-compatible prompts from API configurations. Generates prompts only from the config and no longer includes templates.
"""

import logging
from typing import Dict, List, Optional

# FastMCP primitives
from fastmcp.prompts import Prompt
from fastmcp.prompts.prompt import PromptArgument

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PromptGenerator:
    """Generator for API prompts from config only."""

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

    def generate_prompts(self) -> List[Prompt]:
        """Generate a list of Prompt objects for FastMCP from config only."""

        prompts = []

        # Only include custom prompts from API config
        for i, prompt_data in enumerate(self.custom_prompts):
            try:
                prompts.append(self._build_custom_prompt(prompt_data, i))
            except Exception as exc:  # pragma: no cover – defensive
                logger.warning("Failed to build custom prompt %s: %s", prompt_data, exc)

        return prompts

    def to_mcp_prompts(self) -> Dict[str, Prompt]:  # noqa: N802 – legacy name
        """Return prompts as a mapping for legacy callers.

        NOTE: The new preferred method is :py:meth:`generate_prompts` which
        returns a list of :class:`fastmcp.Prompt` objects.  This shim provides
        a minimal backwards-compatibility layer until all call-sites are
        migrated.
        """

        return {prompt.name: prompt for prompt in self.generate_prompts()}
