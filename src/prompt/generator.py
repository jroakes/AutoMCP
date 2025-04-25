"""
Name: Prompt generator.
Description: Provides PromptGenerator for creating MCP-compatible prompts from API configurations, tools, and resources. Generates standardized prompts for API overviews, tool usage guides, and resource usage guides.
"""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PromptTemplate(BaseModel):
    """Template for a prompt to be used with an API."""

    id: str
    name: str
    description: str
    template: str
    variables: List[str] = []


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

    def create_api_overview_prompt(self) -> PromptTemplate:
        """Create a prompt template for an overview of the API.

        Returns:
            A prompt template
        """
        # Get list of all tools
        tool_names = [tool["name"] for tool in self.tools]

        # Create the template
        template = f"""# {self.api_name} Overview

{self.api_description}

This API provides the following tools:
{', '.join(tool_names)}

To use this API, you can call any of the available tools.

Example:
```
To get information about X, you can use the get_x tool.
```

Let me know what specific information you need from the {self.api_name} API, and I'll help you find the right tool to use.
"""

        return PromptTemplate(
            id="api_overview",
            name=f"{self.api_name} API Overview",
            description=f"Overview of the {self.api_name} API and its tools.",
            template=template,
            variables=[],
        )

    def create_tool_usage_guide_prompt(self) -> PromptTemplate:
        """Create a prompt template for tool usage guide.

        Returns:
            A prompt template
        """
        template = f"""# {self.api_name} Tool Usage Guide

**Tool Overview**
The tools available for {self.api_name} are generated from its OpenAPI specification. Each tool represents an API endpoint and follows a consistent structure:

1. **Name**: A descriptive name derived from the endpoint operation ID
2. **Description**: Explanation of what the tool does, taken from the API documentation
3. **Parameters**: Required and optional parameters for the tool, with data types and descriptions

**How to Use the Tools**
1. Identify the appropriate tool for your task based on the description
2. Provide all required parameters in the correct format
3. Handle the response according to the expected return type

**Tool List**
{', '.join([tool["name"] for tool in self.tools])}

**Authentication**
Most API calls require authentication. Check the authentication guide for how to obtain and use API credentials.

**Error Handling**
When tools return errors, check for:
- Missing required parameters
- Invalid parameter formats
- Authentication issues
- Rate limit restrictions
- Server errors (may require retries)

For detailed information about a specific tool, use its name to get parameter requirements and examples.
"""

        return PromptTemplate(
            id="tool_usage_guide",
            name="Tool Usage Guide",
            description="Guide to understanding and using the tools generated from OpenAPI specs",
            template=template,
            variables=[],
        )

    def create_resource_usage_guide_prompt(self) -> PromptTemplate:
        """Create a prompt template for resource usage guide.

        Returns:
            A prompt template
        """
        resource_count = len(self.resources) if self.resources else 0

        template = f"""# {self.api_name} Resource Usage Guide

**Understanding API Resources**
Resources are searchable chunks of documentation from the {self.api_name} API documentation. These resources provide context and examples for using the API effectively.

**How Resources are Created**
1. API documentation pages are crawled from {self.api_name}'s documentation site
2. Content is extracted, cleaned, and split into semantic chunks
3. Chunks are embedded and stored in a vector database for semantic search

**Current Resource Database**
- Total resources: {resource_count}
- Source: API documentation crawled from official sites
- Embedding model: OpenAI text-embedding model

**How to Use Resources**
1. Search for relevant documentation using natural language queries
2. Reference specific documentation sections when formulating API requests
3. Use examples from documentation to understand parameter formats and expected responses

**Searching Resources**
When you need information about the API, you can search the documentation resources using the search_documentation tool. This performs a semantic search and returns the most relevant chunks.

Example search: "How to authenticate with {self.api_name}?"
"""

        return PromptTemplate(
            id="resource_usage_guide",
            name="Resource Usage Guide",
            description="Guide to understanding and using the resources created from crawled API documentation",
            template=template,
            variables=[],
        )

    def create_custom_prompt(
        self, prompt_data: Dict[str, str], index: int
    ) -> PromptTemplate:
        """Create a prompt template from custom prompt data.

        Args:
            prompt_data: Dictionary containing prompt data
            index: Index of the prompt for ID generation

        Returns:
            A prompt template
        """
        prompt_name = prompt_data.get("name", f"Custom Prompt {index}")
        prompt_id = prompt_name.lower().replace(" ", "_")

        return PromptTemplate(
            id=prompt_id,
            name=prompt_name,
            description=prompt_data.get("description", ""),
            template=prompt_data.get("content", ""),
            variables=[],
        )

    def to_mcp_prompts(self) -> Dict:
        """Convert prompt templates to MCP prompts format.

        Returns:
            Dictionary of MCP prompts compatible with FastMCP
        """
        try:
            from fastmcp.prompts.base import UserMessage, AssistantMessage
        except ImportError:
            # Use our mock classes during testing
            from tests.fixtures.fastmcp_mock import UserMessage, AssistantMessage

        # Create the standard prompts
        prompts = [
            self.create_api_overview_prompt(),
            self.create_tool_usage_guide_prompt(),
            self.create_resource_usage_guide_prompt(),
        ]

        # Add custom prompts from the config file
        for i, prompt_data in enumerate(self.custom_prompts):
            prompts.append(self.create_custom_prompt(prompt_data, i))

        # Convert to MCP format compatible with FastMCP
        mcp_prompts = {}
        for prompt in prompts:
            prompt_id = prompt.id

            # For tool usage prompts, format as messages for better LLM interaction
            if prompt_id == "tool_usage_guide":
                mcp_prompts[prompt_id] = [
                    UserMessage("How should I use the tools in this API?"),
                    AssistantMessage(prompt.template),
                ]
            elif prompt_id == "resource_usage_guide":
                mcp_prompts[prompt_id] = [
                    UserMessage("How can I use the documentation resources?"),
                    AssistantMessage(prompt.template),
                ]
            else:
                # For other prompts, use the structure expected by FastMCP
                mcp_prompts[prompt_id] = {
                    "name": prompt.name,
                    "description": prompt.description,
                    "template": prompt.template,
                    "variables": prompt.variables,
                }

        return mcp_prompts
