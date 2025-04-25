# Getting Started with AutoMCP

This guide will walk you through the basic steps to get AutoMCP up and running.

## Quick Start

```bash
# Install AutoMCP
# Clone the repository and install dependencies
git clone https://github.com/jroakes/automcp.git
cd automcp
pip install -r requirements.txt

# Add an API configuration
python -m src.main add --config your_api_config.json

# Start the MCP server
python -m src.main serve
```

## Basic Workflow

The workflow for using AutoMCP typically involves these steps:

1. Create a configuration file for your API
2. Add the API to AutoMCP
3. Start the MCP server
4. Connect your LLM to the MCP endpoints

## Creating an API Configuration

Create a JSON file with your API configuration. At minimum, you need to include:

```json
{
  "name": "Your API Name",
  "description": "A description of what your API does",
  "openapi_spec_url": "https://example.com/openapi.json",
  "documentation_url": "https://example.com/docs"
}
```

### Advanced Configuration Options

For more control, you can add:

```json
{
  "name": "Your API Name",
  "description": "A description of what your API does",
  "openapi_spec_url": "https://example.com/openapi.json",
  "documentation_url": "https://example.com/docs",
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "Authorization",
    "value": "Bearer ${API_KEY}"
  },
  "rate_limits": {
    "per_minute": 60,
    "enabled": true
  },
  "retry": {
    "max_retries": 3,
    "backoff_factor": 0.5,
    "enabled": true
  },
  "db_directory": "./your_api_db",
  "crawl": {
    "max_depth": 3,
    "max_pages": 100
  },
  "prompts": {
    "example_prompt": {
      "description": "An example prompt for this API",
      "content": "Here is how to use the API effectively..."
    }
  }
}
```

## Adding an API to AutoMCP

Once you have your configuration file, add it to AutoMCP:

```bash
python -m src.main add --config your_api_config.json
```

For multiple APIs in a directory:

```bash
python -m src.main add --config ./api_configs/
```

This will:
1. Process the OpenAPI specification
2. Crawl the documentation
3. Set up the vector database for documentation search
4. Register the API in AutoMCP's registry

## Checking Registered APIs

To list the APIs registered with AutoMCP:

```bash
python -m src.main list-servers
```

## Starting the MCP Server

To start the MCP server:

```bash
python -m src.main serve
```

This will start a server on http://0.0.0.0:8000 by default.

Options:
```bash
python -m src.main serve --host 127.0.0.1 --port 8080 --debug
```

## Integrating with Claude

To generate a configuration file for Claude:

```bash
python -m src.main install claude --output .claude.json
```

This creates a Claude-compatible configuration file that you can use to integrate your MCP server with Claude. 