# AutoMCP

**AutoMCP** is a toolkit for building Model Control Protocol (MCP) servers from OpenAPI specifications. It enables seamless integration between APIs and Large Language Models (LLMs) like Claude, GPT-4, and others that support the MCP protocol.

## Key Features

- **OpenAPI Integration**: Convert any API with an OpenAPI specification into an MCP-compatible server
- **Documentation Crawling**: Automatically crawl and index API documentation for LLM context
- **MCP Server**: Run a compliant MCP server that LLMs can interact with
- **CLI Tools**: Manage multiple API servers from a simple command-line interface
- **Prompt Management**: Configure and manage prompts for better LLM interactions

## Why AutoMCP?

AutoMCP makes it easy to expose your API to LLMs by handling:

- Standardized API interaction through the MCP protocol
- Documentation indexing for better context
- Authentication and rate limiting
- Prompts and response formatting

## Getting Started

```bash
# Install AutoMCP
pip install automcp

# Add an API to AutoMCP
automcp add --config api_config.json

# Start the MCP server
automcp serve
```

See the [Installation](getting-started/installation.md) and [Getting Started](getting-started/quick_start.md) guides for more details.

## How It Works

1. AutoMCP parses your OpenAPI specification to understand your API's endpoints
2. It crawls your API documentation to build a searchable knowledge base
3. It sets up an MCP server that exposes your API as tools and resources
4. LLMs can then discover and use your API through the MCP protocol

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ OpenAPI     │    │ Documentation│    │ Prompt      │
│ Processing  │    │ Crawling     │    │ Management  │
└──────┬──────┘    └───────┬──────┘    └──────┬──────┘
       │                   │                  │
       └──────────┬────────┘────────┬─────────┘
                  │                 │
          ┌───────▼─────────────────▼───────┐
          │           MCP Server            │
          └───────────────┬─────────────────┘
                          │
          ┌───────────────▼─────────────────┐
          │              LLM                │
          └─────────────────────────────────┘
```

v0.1.2