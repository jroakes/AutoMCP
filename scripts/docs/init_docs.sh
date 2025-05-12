#!/bin/bash
# Script to initialize MkDocs documentation from source code

# Exit on error
set -e

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "=== Initializing AutoMCP Documentation ==="

# Create docs directory structure
mkdir -p docs/{openapi,api,mcp,cli,documentation,prompt}

# Create mkdocs.yml configuration
cat > mkdocs.yml << 'EOF'
site_name: AutoMCP Documentation
site_description: Documentation for the AutoMCP OpenAPI toolkit
repo_url: https://github.com/yourusername/AutoMCP
repo_name: AutoMCP

theme:
  name: material
  palette:
    primary: indigo
    accent: indigo
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.expand
    - navigation.indexes
    - content.code.annotate
    - search.highlight
  icon:
    repo: fontawesome/brands/github

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: google
            show_source: true
  - autorefs

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences
  - admonition
  - pymdownx.details
  - pymdownx.tabbed:
      alternate_style: true

nav:
  - 'Home': 'index.md'
  - 'Getting Started':
    - 'Installation': 'getting-started/installation.md'
    - 'CLI Usage': 'getting-started/cli.md'
    - 'Starting a Server': 'getting-started/server.md'
  - 'MCP':
    - 'Overview': 'mcp/index.md'
    - 'Server': 'mcp/server.md'
    - 'Configuration': 'mcp/configuration.md'
    - 'Endpoints': 'mcp/endpoints.md'
  - 'OpenAPI':
    - 'Overview': 'openapi/index.md'
    - 'Tools': 'openapi/tools.md'
    - 'Authentication': 'openapi/authentication.md'
    - 'Rate Limiting': 'openapi/rate_limiting.md'
    - 'Retry': 'openapi/retry.md'
  - 'Documentation Tools':
    - 'Crawler': 'documentation/crawler.md'
    - 'Resource Management': 'documentation/resources.md'
  - 'Prompt Generation':
    - 'Generator': 'prompt/generator.md'
    - 'Templates': 'prompt/templates.md'
  - 'API Reference':
    - 'MCP Server': 'api/mcp_server.md'
    - 'OpenAPI Toolkit': 'api/openapi_toolkit.md'
    - 'Documentation': 'api/documentation.md'
    - 'Prompt': 'api/prompt.md'
  - 'Development':
    - 'Contributing': 'development/contributing.md'
EOF

# Create index.md
cat > docs/index.md << 'EOF'
# AutoMCP Documentation

AutoMCP is a toolkit for interacting with REST APIs through OpenAPI specifications.

## Features

- OpenAPI specification parsing
- API request handling with authentication
- Rate limiting with token bucket algorithm
- Retry mechanism with exponential backoff
- Pagination support for various mechanisms:
  - Link header-based pagination (RFC 5988)
  - Cursor-based pagination
  - Offset/limit pagination
  - Page-based pagination

## Installation

```bash
pip install automcp
```

## Quick Start

```python
from automcp.openapi import OpenAPIToolkit
from automcp.openapi.models import ApiAuthConfig, PaginationConfig

# Load OpenAPI spec
with open("api_spec.json", "r") as f:
    spec = json.load(f)

# Configure authentication
auth_config = ApiAuthConfig(
    type="apiKey",
    in_field="header",
    name="Authorization",
    value="Bearer YOUR_API_KEY"
)

# Configure pagination
pagination_config = PaginationConfig(
    enabled=True,
    mechanism="auto",
    results_field="items"
)

# Create toolkit
toolkit = OpenAPIToolkit(
    spec=spec,
    auth_config=auth_config,
    pagination_config=pagination_config
)

# Get tools
tools = toolkit.get_tools()

# Execute a tool
result = tools[0].execute(param1="value1", param2="value2")
```
EOF

# Create basic OpenAPI overview page
cat > docs/openapi/index.md << 'EOF'
# OpenAPI Toolkit Overview

The AutoMCP OpenAPI toolkit provides tools for interacting with APIs defined by OpenAPI specifications.

## Components

- **OpenAPISpecParser**: Parses OpenAPI specifications and extracts endpoints
- **RestApiTool**: Tool for making requests to a REST API endpoint
- **OpenAPIToolkit**: Creates tools from an OpenAPI specification

## Usage

```python
from automcp.openapi import OpenAPIToolkit

# Load your OpenAPI spec
with open("api_spec.json", "r") as f:
    spec = json.load(f)

# Create toolkit
toolkit = OpenAPIToolkit(spec=spec)

# Get all tools
tools = toolkit.get_tools()

# Get a specific tool by name
tool = toolkit.get_tool("operation_id")

# Execute a tool
result = tool.execute(param1="value1", param2="value2")
```
EOF

# Create pagination documentation
cat > docs/openapi/pagination.md << 'EOF'
# Pagination Support

AutoMCP provides robust pagination support for REST APIs through the `PaginationHandler` class.

## Supported Pagination Mechanisms

- **Link Headers (RFC 5988)**: Used by GitHub API and others
- **Cursor-based Pagination**: Uses a cursor/token for continuation
- **Offset/Limit Pagination**: Uses offset and limit parameters
- **Page-based Pagination**: Uses page number parameters

## Configuration

```python
from automcp.openapi.models import PaginationConfig

pagination_config = PaginationConfig(
    enabled=True,
    mechanism="auto",  # or "link", "cursor", "offset", "page"
    max_pages=5,
    cursor_param="cursor",
    cursor_response_field="next_cursor",
    offset_param="offset",
    limit_param="limit",
    page_param="page",
    results_field="items"
)
```

## Auto-Detection

When mechanism is set to "auto", the pagination handler will automatically detect the pagination mechanism based on response structure:

1. First checks for Link headers
2. Then looks for cursor fields
3. Then tries offset/limit parameters 
4. Finally falls back to page-based pagination
EOF

# Create API reference pages
cat > docs/api/models.md << 'EOF'
# Models API Reference

::: src.openapi.models
    options:
      show_submodules: true
EOF

cat > docs/api/tools.md << 'EOF'
# Tools API Reference

::: src.openapi.tools
    options:
      show_submodules: true
EOF

cat > docs/api/utils.md << 'EOF'
# Utilities API Reference

::: src.openapi.utils
    options:
      show_submodules: true
EOF

cat > docs/api/spec.md << 'EOF'
# Spec Parser API Reference

::: src.openapi.spec
    options:
      show_submodules: true
EOF

# Create development guides
mkdir -p docs/development
cat > docs/development/testing.md << 'EOF'
# Testing Guide

AutoMCP uses a comprehensive test suite to ensure code quality and functionality.

## Test Structure

- `/mcp`: Tests for the MCP module
- `/openapi`: Tests for the OpenAPI module including:
  - Models tests
  - Spec parser tests
  - Utility tests (RetryHandler, RateLimiter, PaginationHandler)

## Running Tests

```bash
# Run all tests
pytest

# Run only OpenAPI tests
pytest tests/openapi/

# Run only pagination tests
pytest tests/openapi/test_pagination.py
```

## Writing Tests

When adding new features, please include tests that verify:

1. Core functionality works as expected
2. Edge cases are handled properly
3. Error conditions are managed gracefully
EOF

# Create getting started guides
mkdir -p docs/getting-started
cat > docs/getting-started/installation.md << 'EOF'
# Installation

AutoMCP can be installed from PyPI using pip:

```bash
pip install automcp
```

## Development Installation

For development, clone the repository and install in development mode:

```bash
git clone https://github.com/yourusername/AutoMCP.git
cd AutoMCP
pip install -e ".[dev]"
```

## Requirements

- Python 3.8+
- Dependencies (automatically installed):
  - FastAPI
  - Pydantic
  - Requests
  - PyYAML
  - ChromaDB (for documentation indexing)
  - OpenAI (for embeddings)
EOF

cat > docs/getting-started/cli.md << 'EOF'
# CLI Usage

AutoMCP provides a command-line interface for generating tools from OpenAPI specifications and starting an MCP server.

## Basic Usage

```bash
# Generate MCP configuration from OpenAPI spec
automcp --config api_config.json --output mcp_config.json

# Generate and start an MCP server
automcp --config api_config.json
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--config` | Path to API configuration file (required) |
| `--output` | Path to write MCP configuration file (optional) |
| `--host` | Host to bind the server to (default: 0.0.0.0) |
| `--port` | Port to bind the server to (default: 8000) |
| `--debug` | Enable debug mode |
| `--no-server` | Skip starting the server |

## API Configuration File

The API configuration file is a JSON file that contains information about the API:

```json
{
  "name": "My API",
  "description": "A description of my API",
  "openapi_spec_url": "https://example.com/openapi.json",
  "documentation_url": "https://example.com/docs",
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "Authorization",
    "value": "Bearer YOUR_API_KEY"
  },
  "rate_limits": {
    "per_minute": 60,
    "per_hour": 1000,
    "enabled": true
  },
  "retry": {
    "max_retries": 3,
    "backoff_factor": 0.5,
    "retry_on_status_codes": [429, 500, 502, 503, 504],
    "enabled": true
  }
}
```

Alternatively, you can provide the OpenAPI spec directly:

```json
{
  "name": "My API",
  "description": "A description of my API",
  "openapi_spec": {
    "openapi": "3.0.0",
    "info": {
      "title": "My API",
      "version": "1.0.0"
    },
    "paths": {
      "/example": {
        "get": {
          "operationId": "getExample",
          "summary": "Get an example",
          "responses": {
            "200": {
              "description": "Success"
            }
          }
        }
      }
    }
  }
}
```

## Example: Using the GitHub API

```bash
# Create a GitHub API configuration
cat > github_api.json << EOF
{
  "name": "GitHub API",
  "description": "GitHub REST API",
  "openapi_spec_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
  "documentation_url": "https://docs.github.com/en/rest",
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "Authorization",
    "value": "token YOUR_GITHUB_TOKEN"
  }
}
EOF

# Generate and start an MCP server
automcp --config github_api.json --port 8080
```
EOF

cat > docs/getting-started/server.md << 'EOF'
# Starting a Server

AutoMCP can generate and run an MCP (Model Control Protocol) server that provides tools for calling API endpoints.

## Quick Start

```bash
# Start a server with default options
automcp --config api_config.json

# Start a server with custom host and port
automcp --config api_config.json --host 127.0.0.1 --port 8080

# Enable debug mode
automcp --config api_config.json --debug
```

## Server Configuration

The server will be available at the specified host and port. By default, it listens on `0.0.0.0:8000`.

### Endpoints

The MCP server provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information |
| `/health` | GET | Health check |
| `/toolset` | GET | Get toolset information |
| `/tools` | GET | List available tools |
| `/execute` | POST | Execute a tool |

## Example: API Request

After starting the server, you can execute a tool using the `/execute` endpoint:

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_user",
    "parameters": {
      "username": "octocat"
    }
  }'
```

## Integrating with LLMs

The MCP server can be integrated with language models using function calling. The server provides function schemas that LLMs can use to make API calls.

```python
import requests
import json
from openai import OpenAI

# Get tool schemas from MCP server
response = requests.get("http://localhost:8000/tools")
tools = response.json()

# Initialize OpenAI client
client = OpenAI()

# Call the LLM with the tools
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You can use tools to call APIs."},
        {"role": "user", "content": "Get information about the octocat user on GitHub"}
    ],
    tools=tools
)

# Extract tool calls
tool_calls = response.choices[0].message.tool_calls
if tool_calls:
    for tool_call in tool_calls:
        # Execute the tool call on the MCP server
        execute_response = requests.post(
            "http://localhost:8000/execute",
            json={
                "tool_name": tool_call.function.name,
                "parameters": json.loads(tool_call.function.arguments)
            }
        )
        tool_result = execute_response.json()
        print(tool_result)
```
EOF

# Create MCP documentation
mkdir -p docs/mcp
cat > docs/mcp/index.md << 'EOF'
# MCP Overview

The Model Control Protocol (MCP) module provides a standardized way for language models to interact with APIs through a server interface.

## What is MCP?

MCP (Model Control Protocol) is a specification for how language models can discover, invoke, and receive results from tools. AutoMCP implements an MCP-compatible server that generates tools from OpenAPI specifications.

## Components

The MCP module includes several key components:

- **MCPServer**: A FastAPI server that exposes API tools
- **MCPToolsetConfig**: Configuration for MCP toolsets
- **Tools**: API tools generated from OpenAPI specifications

## Key Features

- **Dynamic Tool Generation**: Automatically generate tools from OpenAPI specs
- **Standardized Interface**: Provides a consistent interface for language models
- **Authentication Management**: Handles API authentication
- **Resource Management**: Provides access to documentation and other resources
- **Prompt Templates**: Includes prompt templates for better LLM interactions
EOF

cat > docs/mcp/server.md << 'EOF'
# MCP Server

The MCP server is a FastAPI application that provides an interface for language models to discover and invoke API tools.

## Server Initialization

The server is initialized with a toolset configuration:

```python
from automcp.mcp.server import MCPServer, MCPToolsetConfig

# Create config
config = MCPToolsetConfig(
    api_name="My API",
    api_description="A description of my API",
    tools=[...],  # List of tool schemas
    resources={...},  # Dictionary of resources
    prompts={...}  # Dictionary of prompts
)

# Create server
server = MCPServer(config, host="0.0.0.0", port=8000, debug=False)

# Start server
server.start()
```

## Server Endpoints

The server provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Get server information |
| `/health` | GET | Health check endpoint |
| `/toolset` | GET | Get toolset information |
| `/tools` | GET | Get tool schemas |
| `/execute` | POST | Execute a tool |
| `/resources` | GET | Get resources |
| `/resources/{resource_id}` | GET | Get a specific resource |
| `/prompts` | GET | Get prompts |
| `/prompts/{prompt_id}` | GET | Get a specific prompt |

## Authentication

The server supports various authentication mechanisms for API calls:

- API Key authentication
- Bearer token authentication
- Basic authentication

Authentication is handled automatically when executing tools.
EOF

cat > docs/mcp/configuration.md << 'EOF'
# MCP Configuration

The MCP server is configured using the `MCPToolsetConfig` class, which specifies the API information, tools, resources, and prompts.

## MCPToolsetConfig

```python
from automcp.mcp.server import MCPToolsetConfig

config = MCPToolsetConfig(
    api_name="My API",
    api_description="A description of my API",
    tools=[
        {
            "name": "get_user",
            "description": "Get a user by username",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The username of the user"
                    }
                },
                "required": ["username"]
            }
        }
    ],
    resources={
        "user_guide": {
            "title": "User Guide",
            "content": "This is the user guide for the API."
        }
    },
    prompts={
        "system": "You are an assistant that helps users with the API.",
        "examples": [
            {
                "input": "Get information about the octocat user",
                "output": "I'll help you get information about the octocat user. Let me call the API for you."
            }
        ]
    }
)
```

## Configuration File

You can also save and load configurations to/from JSON files:

```python
import json
from automcp.mcp.server import MCPToolsetConfig

# Save configuration
with open("mcp_config.json", "w") as f:
    json.dump(config.dict(), f, indent=2)

# Load configuration
with open("mcp_config.json", "r") as f:
    config_data = json.load(f)
    config = MCPToolsetConfig(**config_data)
```

## Generating Configuration

AutoMCP can automatically generate MCP configurations from API configurations:

```python
from automcp.main import generate_mcp_config
from automcp.utils import ApiConfig

# Create API config
api_config = ApiConfig(
    name="My API",
    description="A description of my API",
    openapi_spec={...}
)

# Generate MCP config
mcp_config = generate_mcp_config(api_config, output_path="mcp_config.json")
```
EOF

cat > docs/mcp/endpoints.md << 'EOF'
# MCP Endpoints

The MCP server provides several endpoints for tool discovery and execution.

## Tool Discovery

### Get Toolset Information

```
GET /toolset
```

Returns information about the toolset, including the API name, description, and available tools.

Example response:
```json
{
  "name": "GitHub API",
  "description": "GitHub REST API",
  "tools": [
    {
      "name": "get_user",
      "description": "Get a user by username"
    },
    {
      "name": "list_repositories",
      "description": "List repositories for a user"
    }
  ]
}
```

### Get Tool Schemas

```
GET /tools
```

Returns detailed schemas for all available tools, compatible with OpenAI function calling.

Example response:
```json
[
  {
    "type": "function",
    "function": {
      "name": "get_user",
      "description": "Get a user by username",
      "parameters": {
        "type": "object",
        "properties": {
          "username": {
            "type": "string",
            "description": "The username of the user"
          }
        },
        "required": ["username"]
      }
    }
  }
]
```

## Tool Execution

### Execute Tool

```
POST /execute
```

Executes a tool with the specified parameters.

Request body:
```json
{
  "tool_name": "get_user",
  "parameters": {
    "username": "octocat"
  }
}
```

Example response:
```json
{
  "id": 1,
  "login": "octocat",
  "name": "The Octocat",
  "company": "@github",
  "blog": "https://github.blog",
  "location": "San Francisco",
  "email": null,
  "hireable": null,
  "bio": null,
  "twitter_username": null,
  "public_repos": 8,
  "public_gists": 8,
  "followers": 5262,
  "following": 9
}
```

## Resource Management

### Get Resources

```
GET /resources
```

Returns a list of available resources.

### Get Resource

```
GET /resources/{resource_id}
```

Returns a specific resource by ID.

## Prompt Management

### Get Prompts

```
GET /prompts
```

Returns a list of available prompts.

### Get Prompt

```
GET /prompts/{prompt_id}
```

Returns a specific prompt by ID.
EOF

# Create documentation crawler documentation
mkdir -p docs/documentation
cat > docs/documentation/crawler.md << 'EOF'
# Documentation Crawler

The documentation crawler extracts content from API documentation websites to provide context for tool usage.

## Overview

The `DocumentationCrawler` class crawls API documentation websites, extracts relevant content, and saves it to a resource manager. This content can be used to provide additional context to language models when using the API.

## Usage

```python
from automcp.documentation.crawler import DocumentationCrawler
from automcp.documentation.resources import ResourceManager

# Create a resource manager
resource_manager = ResourceManager(
    db_directory="./.chromadb",
    embedding_type="openai",
    openai_api_key="your-openai-api-key",
    embedding_model="text-embedding-3-small",
)

# Create a crawler
crawler = DocumentationCrawler(
    base_url="https://docs.github.com/en/rest",
    resource_manager=resource_manager,
    max_pages=50,
    max_depth=3,
    rate_limit_delay=(1.0, 3.0),
    bypass_cache=False,
)

# Crawl the documentation
crawler.crawl()

# Access resources
resources = resource_manager.list_resources()
```

## Configuration Options

| Option | Description |
|--------|-------------|
| `base_url` | The base URL of the documentation site |
| `resource_manager` | The resource manager to store extracted content |
| `max_pages` | Maximum number of pages to crawl |
| `max_depth` | Maximum depth to crawl |
| `rate_limit_delay` | Delay between requests (min, max) in seconds |
| `bypass_cache` | Whether to bypass the cache |

## Extracting Content

The crawler extracts relevant content from HTML pages:

1. Removes irrelevant elements (navigation, footers, etc.)
2. Extracts headings, paragraphs, code blocks, and tables
3. Processes content to create meaningful chunks
4. Indexes chunks for semantic search

## Caching

By default, the crawler caches downloaded pages to avoid repeatedly downloading the same content. This can be disabled with the `bypass_cache` option.
EOF

cat > docs/documentation/resources.md << 'EOF'
# Resource Management

The resource management system stores and retrieves documentation content for use by the MCP server.

## Overview

The `ResourceManager` class manages documentation resources, including:

- Storing extracted documentation content
- Indexing content for semantic search
- Retrieving relevant content for tool usage
- Managing resource metadata

## Usage

```python
from automcp.documentation.resources import ResourceManager

# Create a resource manager
resource_manager = ResourceManager(
    db_directory="./.chromadb",
    embedding_type="openai",
    openai_api_key="your-openai-api-key",
    embedding_model="text-embedding-3-small",
)

# Add a resource
resource_id = resource_manager.add_resource(
    title="User API Guide",
    content="This is a guide to the user API...",
    url="https://docs.example.com/users",
    metadata={"section": "users"}
)

# List resources
resources = resource_manager.list_resources()

# Get a resource
resource = resource_manager.get_resource(resource_id)

# Search resources
results = resource_manager.search("How to get user information", limit=5)
```

## Embedding Types

The resource manager supports different embedding types:

- **OpenAI**: Uses OpenAI's embedding models
- **HuggingFace**: Uses Hugging Face models
- **Local**: Uses locally installed models

## Vector Database

Resources are stored in a ChromaDB vector database, which enables:

- Semantic search of documentation content
- Fast retrieval of relevant information
- Persistence across runs

## Integration with MCP

The MCP server can use the resources to provide context to language models:

1. When a language model requests information about a tool
2. To enrich tool schemas with examples and explanations
3. To provide additional documentation links
EOF

# Create prompt generator documentation
mkdir -p docs/prompt
cat > docs/prompt/generator.md << 'EOF'
# Prompt Generator

The prompt generator creates prompts for language models to effectively use the API tools.

## Overview

The `PromptGenerator` class generates prompts for language models, including:

- System prompts explaining how to use the tools
- Example prompts showing tool usage
- Tool-specific prompts with detailed instructions

## Usage

```python
from automcp.prompt.generator import PromptGenerator

# Create generator
generator = PromptGenerator(
    api_name="GitHub API",
    api_description="GitHub REST API",
    tools=[...],  # List of tool schemas
    resources={}
)

# Generate prompts
prompts = generator.generate_prompts()

# Use specific prompt
system_prompt = prompts[0].fn()
```

## Prompt Types

The generator creates several types of prompts:

- **System**: Instructions for the language model
- **Examples**: Example interactions showing tool usage
- **Tool-specific**: Detailed instructions for using specific tools

## Template Variables

Prompts can include variables that are replaced at runtime:

- `{api_name}`: The name of the API
- `{api_description}`: The description of the API
- `{tools}`: The list of available tools
- `{tool_count}`: The number of available tools

## Customization

Prompt templates can be customized by modifying the template files:

- `system_prompt.txt`: The system prompt template
- `tool_prompt.txt`: The tool-specific prompt template
EOF

cat > docs/prompt/templates.md << 'EOF'
# Prompt Templates

AutoMCP includes customizable prompt templates for language models.

## System Prompt

The system prompt provides general instructions for using the API tools:

```
You are an assistant that uses the {api_name} API. {api_description}

This API provides {tool_count} tools you can use:
{tools}

Follow these guidelines when using the tools:
1. Understand what the user is asking for
2. Choose the appropriate tool for the task
3. Provide all required parameters
4. Explain the results to the user

If you encounter errors, try to understand the error message and adjust your request accordingly.
```

## Tool-Specific Prompts

Tool-specific prompts provide detailed instructions for using individual tools:

```
Tool: {tool_name}
Description: {tool_description}

Parameters:
{parameters}

Example usage:
{example}

Documentation:
{documentation}
```

## Example Prompts

Example prompts show how to use tools in specific scenarios:

```
User: Get information about the octocat user on GitHub.
EOF

echo "=== Building Documentation ==="
mkdocs build

echo "=== Documentation initialized successfully ==="
echo "Run './scripts/docs/serve_docs.sh' to preview the documentation" 