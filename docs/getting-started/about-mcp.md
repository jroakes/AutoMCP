# About MCP

The Model Context Protocol (MCP) is a standardized way for Large Language Models (LLMs) to interact with external tools and services. AutoMCP implements MCP servers for your APIs, making them accessible to LLMs.

## What is MCP?

MCP provides a structured interface for LLMs to:

1. Discover available tools and capabilities
2. Execute operations on external systems
3. Retrieve contextual information
4. Access predefined prompts and templates

## AutoMCP's MCP Implementation

AutoMCP creates MCP-compliant servers that expose three main endpoints:

### Tools

The `tools` endpoint allows LLMs to interact with your API's operations:

- **List Tools**: Discover available API endpoints
- **Call Tool**: Execute specific API operations with parameters

### Resources

The `resources` endpoint provides access to documentation:

- **List Resources**: Get a list of all indexed documentation pages
- **Call Resource**: Retrieve the content of a specific documentation page
- **Search**: Perform semantic search across the documentation

### Prompts

The `prompts` endpoint manages predefined prompts:

- **List Prompts**: View available prompts defined in the configuration
- **Call Prompt**: Retrieve the content of a specific prompt

## MCP Server Architecture

```
┌─────────────────────────────────────────┐
│               MCP Server                │
├─────────────┬─────────────┬─────────────┤
│    Tools    │  Resources  │   Prompts   │
├─────────────┴─────────────┴─────────────┤
│           FastAPI Application           │
└─────────────────────────────────────────┘
             ▲                 ▲
             │                 │
  ┌──────────┴──────────┐     │
  │   OpenAPI Toolkit   │     │
  └─────────────────────┘     │
             ▲                │
             │                │
  ┌──────────┴──────────┐    │
  │  OpenAPI Spec Parser│    │
  └─────────────────────┘    │
                             │
  ┌───────────────────────────┐
  │   Documentation Manager   │
  └───────────────────────────┘
             ▲
             │
  ┌──────────┴──────────┐
  │ Documentation Crawler│
  └─────────────────────┘
```

## Detailed MCP Endpoint Specifications

AutoMCP provides a complete MCP server implementation with three main endpoints: Tools, Resources, and Prompts. The following sections detail the API specifications for each endpoint.

### Tools Endpoint

The Tools endpoint allows LLMs to discover and call API operations.

#### List Tools

Retrieves a list of all available tools from the API.

**Request:**
```http
GET /tools
```

**Response:**
```json
{
  "tools": [
    {
      "name": "get_user",
      "description": "Get a user by ID",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {
            "type": "string",
            "description": "The ID of the user"
          }
        },
        "required": ["user_id"]
      }
    },
    {
      "name": "list_repositories",
      "description": "List repositories for a user",
      "parameters": {
        "type": "object",
        "properties": {
          "username": {
            "type": "string",
            "description": "The username to list repositories for"
          },
          "per_page": {
            "type": "integer",
            "description": "Number of results per page"
          }
        },
        "required": ["username"]
      }
    }
  ]
}
```

#### Call Tool

Executes a specific tool with the provided parameters.

**Request:**
```http
POST /tools/call
Content-Type: application/json

{
  "name": "get_user",
  "parameters": {
    "user_id": "12345"
  }
}
```

**Response:**
```json
{
  "result": {
    "id": "12345",
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Resources Endpoint

The Resources endpoint provides access to API documentation.

#### List Resources

Retrieves a list of all indexed documentation resources.

**Request:**
```http
GET /resources
```

**Response:**
```json
{
  "resources": [
    {
      "uri": "getting-started",
      "title": "Getting Started with the API"
    },
    {
      "uri": "authentication",
      "title": "Authentication Guide"
    },
    {
      "uri": "endpoints/users",
      "title": "Users API Reference"
    }
  ]
}
```

#### Call Resource

Retrieves the content of a specific documentation resource.

**Request:**
```http
POST /resources/call
Content-Type: application/json

{
  "uri": "authentication"
}
```

**Response:**
```json
{
  "content": "# Authentication Guide\n\nTo authenticate with our API, you need to provide an API key in the Authorization header...",
  "metadata": {
    "title": "Authentication Guide",
    "last_updated": "2023-09-15"
  }
}
```

#### Search Resources

Performs a semantic search across documentation.

**Request:**
```http
POST /resources/search
Content-Type: application/json

{
  "query": "How do I authenticate?",
  "limit": 3
}
```

**Response:**
```json
{
  "results": [
    {
      "uri": "authentication",
      "title": "Authentication Guide",
      "content": "# Authentication Guide\n\nTo authenticate with our API, you need to provide an API key...",
      "score": 0.95
    },
    {
      "uri": "api-keys",
      "title": "Managing API Keys",
      "content": "# Managing API Keys\n\nAPI keys can be generated in your account settings...",
      "score": 0.82
    },
    {
      "uri": "getting-started",
      "title": "Getting Started",
      "content": "# Getting Started\n\nBefore making API calls, you'll need to authenticate...",
      "score": 0.76
    }
  ]
}
```

### Prompts Endpoint

The Prompts endpoint manages predefined prompts.

#### List Prompts

Retrieves a list of all available prompts.

**Request:**
```http
GET /prompts
```

**Response:**
```json
{
  "prompts": [
    {
      "id": "usage_example",
      "description": "Example of how to use the API"
    },
    {
      "id": "error_handling",
      "description": "How to handle common errors"
    }
  ]
}
```

#### Call Prompt

Retrieves the content of a specific prompt.

**Request:**
```http
POST /prompts/call
Content-Type: application/json

{
  "id": "usage_example"
}
```

**Response:**
```json
{
  "content": "Here's how to use the API effectively:\n\n1. First, authenticate...",
  "metadata": {
    "description": "Example of how to use the API"
  }
}
```

## Usage in LLMs

LLMs like Claude that support the MCP protocol can directly interact with your MCP server. After configuration, the LLM can:

1. Discover your API's capabilities
2. Call endpoints with appropriate parameters 
3. Search documentation for context
4. Use predefined prompts for consistent interactions 