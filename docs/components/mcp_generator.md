# MCP Generator

The MCP Generator is the component of AutoMCP that transforms OpenAPI specifications into MCP-compatible servers.

## Overview

The MCP Generator:

1. Parses OpenAPI specifications
2. Converts API operations to MCP tools
3. Creates MCP server endpoints
4. Configures authentication, rate limiting, and other features
5. Manages multiple API servers under a single MCP server

## Generation Process

### From OpenAPI to MCP

1. **Parse Specification**: Extract endpoints, parameters, and descriptions
2. **Create Tool Schemas**: Convert operations to JSON Schema for parameters
3. **Generate Execution Logic**: Create the execution functions for each tool
4. **Setup MCP Endpoints**: Configure the FastAPI routes for the MCP server

### Example Transformation

OpenAPI Operation:
```yaml
paths:
  /users/{user_id}:
    get:
      operationId: getUser
      summary: Get user details
      description: Retrieves detailed information about a user
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
```

MCP Tool:
```json
{
  "name": "getUser",
  "description": "Get user details - Retrieves detailed information about a user",
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
}
```

## MCP Server Structure

The generated MCP server includes:

### 1. Tools Endpoint

- `GET /api_name/tools`: Lists all available tools
- `POST /api_name/tools/call`: Executes a tool with parameters

### 2. Resources Endpoint

- `GET /api_name/resources`: Lists all indexed documentation resources
- `POST /api_name/resources/call`: Retrieves a specific resource
- `POST /api_name/resources/search`: Searches for resources

### 3. Prompts Endpoint

- `GET /api_name/prompts`: Lists all available prompts
- `POST /api_name/prompts/call`: Retrieves a specific prompt

## Multiple API Support

The MCP Generator can handle multiple APIs in a single server:

1. Each API gets its own namespace (e.g., `/github/tools`, `/twitter/tools`)
2. Tools, resources, and prompts are isolated between APIs
3. Each API can have its own configuration options
4. All APIs are served from a single FastAPI instance

## Configuration Options

The MCP Generator can be configured through:

```json
{
  "mcp": {
    "server": {
      "prefix": "/api_name",
      "tools_endpoint": "/tools",
      "resources_endpoint": "/resources",
      "prompts_endpoint": "/prompts"
    },
    "tools": {
      "exclude_operations": ["internal_operation", "admin_*"],
      "include_operations": ["public_*"]
    }
  }
}
```

## Integration with Claude

The MCP Generator can create Claude-compatible configurations:

```json
{
  "tools": [
    {
      "name": "github",
      "url": "http://localhost:8000/github/mcp",
      "schema_version": "v1"
    }
  ]
}
```

This can be generated using:

```bash
automcp install claude --output .claude.json
```

## Best Practices

1. **Use Descriptive Operation IDs**: Clear operationIds make better tool names
2. **Provide Good Descriptions**: Detailed descriptions help LLMs understand tool purposes
3. **Filter Operations**: Use include/exclude patterns to expose only relevant endpoints
4. **Test Integration**: Verify the MCP server works correctly with your LLM 