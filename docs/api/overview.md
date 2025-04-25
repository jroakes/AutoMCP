# API Reference

This section contains the detailed API reference for AutoMCP's Python modules. The documentation is generated automatically from the source code.

## Package Structure

AutoMCP is organized into the following modules:

- **main**: Command-line interface and entry points
- **manager**: MCP server management and configuration
- **utils**: Utility functions and helper classes
- **openapi**: OpenAPI specification parsing and API interaction
- **mcp**: Model Control Protocol implementation
- **documentation**: Documentation crawling and resource management
- **prompt**: Prompt management and generation

## Using the API Reference

Each module's documentation includes:

- Function and class definitions
- Parameter descriptions
- Return value information 
- Code examples (where available)

## Core Components

The core components of AutoMCP are:

### CLI

The command-line interface provides commands for:
- Adding API configurations
- Listing registered servers
- Deleting servers
- Starting the MCP server
- Installing configurations for LLMs like Claude

### OpenAPI Processing

The OpenAPI module handles:
- Parsing OpenAPI specifications
- Converting API endpoints to MCP tools
- Managing authentication and rate limiting

### Documentation Management

The documentation module provides:
- Web crawling of API documentation
- Document parsing and chunking
- Vector database storage and retrieval

### MCP Server

The MCP server implements:
- Tools API for executing API calls
- Resources API for retrieving documentation
- Prompts API for managing prompts 