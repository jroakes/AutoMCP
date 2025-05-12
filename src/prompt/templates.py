"""Prompt templates shared across the project.

This module stores long, mostly static multi-line strings that serve as the
base templates for the hard-coded prompts (API overview, tool usage guide and
resource usage guide).  Placing them in a standalone file keeps the
`generator.py` module concise and focused on business logic.

The placeholders (e.g. `{api_name}`) are **not** formatted here.  They are
instead interpolated by `prompt.generator.PromptGenerator` which provides the
appropriate runtime values (API name, description, etc.).
"""

# NOTE: Do **not** rename these symbols without updating the import statements
# throughout the codebase.

API_OVERVIEW_TEMPLATE: str = (
    """# {api_name} Overview

{api_description}

This API provides access to its functionalities through the Model Context Protocol (MCP).
You can interact with this API using MCP methods such as `list_tools`, `call_tool`, `list_resources`, `call_resource`, `search_resources`, and `get_prompt`.

**Available Tools:**
{tool_list}

**How to Use a Tool:**
To use a specific tool, you will typically use an MCP client's `call_tool` method.
For example: `call_tool(tool_name="<tool_name_from_list>", parameters={{"param1": "value1", "param2": "value2"}})`
Refer to the "Tool Usage Guide" for more details (e.g., by calling `get_prompt(prompt_name="tool_usage_guide")`).

**Available Resources:**
This API also provides informational resources. You can search these resources or call them directly if you know their URI.
Refer to the "Resource Usage Guide" for more details (e.g., by calling `get_prompt(prompt_name="resource_usage_guide")`).

Example of an LLM thinking process:
1. Goal: Find out how to get information from the API.
2. Action: Review the `{tool_list}` provided in this overview or call `list_tools()`.
3. Observation: Found a relevant tool with its required parameters.
4. Action: `call_tool(tool_name="<tool_name>", parameters={{"<param_name>": "<param_value>"}})`

Let me know what specific information you need from the {api_name} API, and I can help guide you on which tool or resource might be most appropriate.
"""
)

TOOL_USAGE_GUIDE_TEMPLATE: str = (
    """# {api_name} Tool Usage Guide

**Tool Overview**
The tools available for {api_name} are generated from its OpenAPI specification. Each tool represents an API endpoint and allows you to perform actions or retrieve specific data. Tools generally follow this structure:

1.  **Name**: A descriptive name, often derived from the API endpoint's operation ID. This is the `tool_name` you will use.
2.  **Description**: An explanation of what the tool does, its purpose, and expected outcomes.
3.  **Parameters**: A list of required and optional parameters the tool accepts. Each parameter will have a name, data type, and description.

**How to Use the Tools via MCP**
1.  **Identify Tool**: Based on your task, select the appropriate tool from the list provided by `list_tools()` or the `{tool_list}` below.
2.  **Prepare Parameters**: Construct a dictionary where keys are the parameter names and values are the data you want to pass. Ensure data types match the tool's requirements.
3.  **Invoke Tool**: Use the `call_tool` method with the `tool_name` and your parameters dictionary.
    Example: `call_tool(tool_name="<selected_tool_name>", parameters={{"param_name1": "valueA", "param_name2": 123}})`
4.  **Handle Response**: The tool will return a response. Process this response according to its structure and content type.

**Tool List**
{tool_list}

**Authentication**
If API calls require authentication, ensure your MCP client or environment is configured with the necessary credentials. Authentication details are typically handled by the MCP server based on the API's OpenAPI specification.

**Error Handling**
When a `call_tool` request results in an error, examine the error message. Common causes include:
-   Missing required parameters.
-   Incorrect data types for parameters.
-   Invalid parameter values.
-   Authentication failures.
-   API rate limit exceeded.
-   Temporary server-side issues with the underlying API.

For detailed information about a specific tool's parameters and structure, refer to the information provided in the `{tool_list}` or the output of `list_tools()`.
"""
)

RESOURCE_USAGE_GUIDE_TEMPLATE: str = (
    """# {api_name} Resource Usage Guide

**Understanding API Resources**
Resources provide access to informational content, often derived from the {api_name} API documentation. They are useful for gaining context, understanding API functionalities, and finding examples.

**How Resources are Created (Typical Process)**
1.  API documentation pages are crawled from {api_name}'s official documentation site.
2.  Relevant content is extracted, cleaned, and divided into manageable, semantic chunks.
3.  These chunks are often embedded using language models and stored in a vector database to enable semantic search.

**Current Resource Database Overview**
-   Total resources available: {resource_count}
-   Primary source: API documentation crawled from official sites.

**How to Use Resources via MCP**

1.  **Searching Resources (Recommended for Discovery):**
    To find relevant documentation or information, use the `search_resources` method. This performs a semantic search across the available resource content.
    Provide your query as a string.
    Example: `search_resources(query="How do I authenticate with the {api_name} API?")`
    The search will return a list of resource chunks most relevant to your query.

2.  **Listing Resources:**
    To get a list of available resource URIs or URI patterns, you can use the `list_resources` method.
    Example: `list_resources()`

3.  **Calling a Specific Resource (Direct Access):**
    If you know the specific URI of a resource (e.g., from `list_resources` or a previous search result), you can fetch its content directly using the `call_resource` method.
    Example: `call_resource(resource_uri="<specific_resource_uri>")`

**Tips for Effective Resource Usage**
-   Use `search_resources` with natural language questions to find general information or how-to guides.
-   Refer to the content of fetched or searched resources when formulating `call_tool` requests to ensure you understand parameter formats and expected API behavior.
-   Examples found within resources can be invaluable for understanding how to use specific API endpoints (tools).
"""
) 