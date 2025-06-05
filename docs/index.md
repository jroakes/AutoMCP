# AutoMCP

**AutoMCP** is a toolkit for building Model Control Protocol (MCP) servers from OpenAPI specifications. It enables seamless integration between APIs and Large Language Models (LLMs) like Claude, GPT-4, and others that support the MCP protocol.

## Key Features

- Generate MCP tools from OpenAPI specs
- Crawl API documentation to create MCP resources
- Serve custom prompts directly from configuration
- Extract structured data from API specifications
- Standardized authentication handling for API keys (header and query)
- Rate limiting with token bucket algorithm to prevent API throttling
- Retry mechanism with exponential backoff for transient failures
- Launch an MCP server for immediate use
- CLI Tools: Manage multiple API servers from a simple command-line interface

## Why AutoMCP?

AutoMCP makes it easy to expose your API to LLMs by handling:

- Standardized API interaction through the MCP protocol
- Documentation indexing for better context
- Authentication and rate limiting
- Prompts and response formatting

## Getting Started

```bash
# Clone the repository
git clone https://github.com/jroakes/automcp.git
cd automcp

# Install dependencies
pip install -r requirements.txt

# Add an API to AutoMCP
python -m src.main add --config example_config.json

# Start the MCP server
python -m src.main serve --config example_config.json
```

See the [Installation](getting-started/installation.md) and [Getting Started](getting-started/quick_start.md) guides for more details.

## How It Works

1. The tool reads your API configuration from a JSON file
2. It loads the OpenAPI specification from a URL or file
3. It crawls the API documentation (if provided) to extract relevant information
4. It generates MCP tools based on the OpenAPI endpoints
5. It applies authentication, rate limiting, and retry configurations to the tools
6. It creates MCP resources from the crawled documentation
7. It serves custom prompts directly from the configuration file
8. It launches an MCP server that LLM clients can connect to

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ OpenAPI     │    │ Documentation│    │ Prompt      │
│ Processing  │    │ Crawling     │    │ Generation  │
│             │    │ (Crawl4AI)   │    │             │
└──────┬──────┘    └───────┬──────┘    └──────┬──────┘
       │                   │                  │
       │          ┌────────▼──────────┐       │
       │          │ Vector Database   │       │
       │          │ (ChromaDB)        │       │
       │          └────────┬──────────┘       │
       │                   │                  │
       └──────────┬────────┘────────┬─────────┘
                  │                 │
          ┌───────▼─────────────────▼───────┐
          │        FastMCP Server           │
          │  ┌─────────┬─────────┬────────┐ │
          │  │ Tools   │Resources│Prompts │ │
          │  └─────────┴─────────┴────────┘ │
          └───────────────┬─────────────────┘
                          │ MCP Protocol
          ┌───────────────▼─────────────────┐
          │         LLM Client              │
          │    (Claude, GPT-4, etc.)        │
          └─────────────────────────────────┘
```