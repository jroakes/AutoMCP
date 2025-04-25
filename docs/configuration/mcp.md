# MCP Server Configuration

The MCP server in AutoMCP can be configured through both the API configuration files and command-line options.

## API Configuration

The API configuration file contains settings that are specific to an API and its MCP server. Here are the MCP-related configuration options:

```json
{
  "name": "Example API",
  "description": "Example API for demonstration purposes",
  "openapi_spec_url": "https://example.com/openapi.json",
  "documentation_url": "https://example.com/docs",
  "mcp": {
    "server": {
      "prefix": "/api_name",
      "tools_endpoint": "/tools",
      "resources_endpoint": "/resources",
      "prompts_endpoint": "/prompts"
    },
    "tools": {
      "exclude_operations": ["internal_operation", "admin_*"],
      "include_operations": ["public_*"],
      "summary_truncation": 120
    },
    "resources": {
      "max_search_results": 5,
      "search_threshold": 0.7
    }
  }
}
```

### MCP Server Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `prefix` | string | URL prefix for this API's MCP endpoints | `/api_name` |
| `tools_endpoint` | string | URL path for the tools endpoint | `/tools` |
| `resources_endpoint` | string | URL path for the resources endpoint | `/resources` |
| `prompts_endpoint` | string | URL path for the prompts endpoint | `/prompts` |

### Tools Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `exclude_operations` | array | Operations to exclude (supports wildcards) | `[]` |
| `include_operations` | array | Operations to include (supports wildcards) | `[]` |
| `summary_truncation` | number | Maximum length for operation summaries | `120` |

### Resources Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_search_results` | number | Maximum number of search results to return | `5` |
| `search_threshold` | number | Minimum similarity score for search results (0-1) | `0.7` |

## Command-Line Configuration

When starting the MCP server with the CLI, you can provide additional configuration:

```bash
automcp serve --host 127.0.0.1 --port 8080 --debug
```

### CLI Options for MCP Server

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Host to bind the server to | `0.0.0.0` |
| `--port` | Port to bind the server to | `8000` |
| `--debug` | Enable debug mode | `false` |
| `--config` | Path to API configuration file or directory | None |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

## Multi-API Configuration

AutoMCP allows you to serve multiple APIs from a single MCP server. Each API has its own set of MCP endpoints under its own prefix.

For example, if you have two APIs configured:

1. `github` API: Endpoints at `/github/tools`, `/github/resources`, `/github/prompts`
2. `twitter` API: Endpoints at `/twitter/tools`, `/twitter/resources`, `/twitter/prompts`

### Claude Configuration for Multiple APIs

When generating a Claude configuration file, all registered APIs will be included:

```bash
automcp install claude --output .claude.json
```

This generates:

```json
{
  "tools": [
    {
      "name": "github",
      "url": "http://localhost:8000/github/mcp",
      "schema_version": "v1"
    },
    {
      "name": "twitter",
      "url": "http://localhost:8000/twitter/mcp",
      "schema_version": "v1"
    }
  ]
}
``` 