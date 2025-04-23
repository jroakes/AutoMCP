"""Prompt generator for API tools."""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

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
        self, api_name: str, api_description: str, tools: List[Dict], resources: Dict
    ):
        """Initialize the prompt generator.

        Args:
            api_name: Name of the API
            api_description: Description of the API
            tools: List of tools as dictionaries
            resources: Dictionary of resources
        """
        self.api_name = api_name
        self.api_description = api_description
        self.tools = tools
        self.resources = resources

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

    def create_tool_usage_prompt(self) -> PromptTemplate:
        """Create a prompt template for using tools with the API.

        Returns:
            A prompt template
        """
        template = f"""# Using {self.api_name} API Tools

To use the {self.api_name} API, follow these steps:

1. Identify which tool you need to use for your task
2. Call the tool with the required parameters
3. Process the response to extract the information you need

Available tools:
{{tools}}

Example usage:
```
# Example calling a tool
response = await tool_name(param1=value1, param2=value2)
```

Let me know which tool you want to use, and I'll help you with the specific parameters required.
"""

        return PromptTemplate(
            id="tool_usage",
            name=f"{self.api_name} Tool Usage Guide",
            description=f"Guide for using tools with the {self.api_name} API.",
            template=template,
            variables=["tools"],
        )

    def create_search_query_prompt(self) -> PromptTemplate:
        """Create a prompt template for formulating search queries.

        Returns:
            A prompt template
        """
        template = f"""# {self.api_name} Search Query Guide

To search for information using the {self.api_name} API, you can use the following pattern:

1. What information are you looking for? (e.g., users, products, articles)
2. What specific attributes or filters do you need? (e.g., by ID, by name, by date)
3. How should the results be sorted or limited? (e.g., limit to 10, sort by date)

Example search query:
```
{{example_query}}
```

Formulate your search query clearly specifying what you're looking for and any filters or constraints.
"""

        return PromptTemplate(
            id="search_query",
            name=f"{self.api_name} Search Query Guide",
            description=f"Guide for formulating search queries with the {self.api_name} API.",
            template=template,
            variables=["example_query"],
        )

    def create_error_handling_prompt(self) -> PromptTemplate:
        """Create a prompt template for handling errors.

        Returns:
            A prompt template
        """
        template = f"""# {self.api_name} Error Handling Guide

When using the {self.api_name} API, you may encounter various errors. Here's how to handle common issues:

1. Authentication errors: Check that your API credentials are correct and properly configured
2. Parameter errors: Ensure all required parameters are provided and in the correct format
3. Rate limiting errors: The API may have limits on how many requests you can make in a time period
4. Resource not found: The requested resource may not exist or you may not have permission to access it

Common error codes:
- 400: Bad Request - Check your request parameters
- 401: Unauthorized - Authentication issue
- 403: Forbidden - Permission issue
- 404: Not Found - Resource doesn't exist
- 429: Too Many Requests - Rate limited

If you encounter an error, please provide the error message and status code for troubleshooting.
"""

        return PromptTemplate(
            id="error_handling",
            name=f"{self.api_name} Error Handling Guide",
            description=f"Guide for handling errors with the {self.api_name} API.",
            template=template,
            variables=[],
        )

    def create_authentication_prompt(self) -> PromptTemplate:
        """Create a prompt template for authentication.

        Returns:
            A prompt template
        """
        template = f"""# {self.api_name} Authentication Guide

To authenticate with the {self.api_name} API, you need to:

1. Obtain API credentials ({{auth_type}})
2. Include these credentials with each request

Example authentication:
```
{{auth_example}}
```

Make sure to keep your API credentials secure and never expose them in client-side code.
"""

        return PromptTemplate(
            id="authentication",
            name=f"{self.api_name} Authentication Guide",
            description=f"Guide for authenticating with the {self.api_name} API.",
            template=template,
            variables=["auth_type", "auth_example"],
        )

    def to_mcp_prompts(self) -> Dict:
        """Convert prompt templates to MCP prompts format.

        Returns:
            Dictionary of MCP prompts
        """
        # Create all prompt templates
        prompts = [
            self.create_api_overview_prompt(),
            self.create_tool_usage_prompt(),
            self.create_search_query_prompt(),
            self.create_error_handling_prompt(),
            self.create_authentication_prompt(),
        ]

        # Convert to MCP format
        mcp_prompts = {}
        for prompt in prompts:
            mcp_prompts[prompt.id] = {
                "name": prompt.name,
                "description": prompt.description,
                "template": prompt.template,
                "variables": prompt.variables,
            }

        return mcp_prompts
