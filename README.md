# AutoMCP: Build MCP servers from OpenAPI specs

> **⚠️ ALPHA WARNING:** AutoMCP is in active development and *not* production-ready. The codebase is changing rapidly and may fail unpredictably. Proceed with caution!

AutoMCP is a tool for automatically generating [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/mcp) tools, resources, and prompts from OpenAPI specifications.

## Features

- Generate MCP tools from OpenAPI specs
- Crawl API documentation to create MCP resources
- Generate helpful prompts for using the API
- Extract structured data from API specifications
- Standardized authentication handling for API keys (header and query)
- Rate limiting with token bucket algorithm to prevent API throttling
- Retry mechanism with exponential backoff for transient failures
- Launch an MCP server for immediate use

## Installation

```bash
# Clone the repository
git clone https://github.com/jroakes/automcp.git
cd automcp

# Install dependencies
pip install -r requirements.txt
```

## Documentation

- [Usage Guide](#usage) - Instructions for configuring and running AutoMCP
- [MCP Migration Guide](docs/mcp_migration_guide.md) - Guide for updating from decorator-based implementation to explicit method calls
- [System Components](#system-components) - Overview of AutoMCP's main components
- [Testing](#testing) - Information about the test suite

## Usage

### Configuration

Create a JSON configuration file with the following structure:

```json
{
  "name": "weather-api",
  "display_name": "Weather API",
  "description": "A comprehensive API for retrieving current weather and forecasts",
  "icon": "https://example.com/weather-api.svg",
  "version": "1.0.3",
  "documentation_url": "https://weather-api.example.com/docs",
  "openapi_spec_url": "https://weather-api.example.com/openapi.json",
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
    "value": "your-api-key"
  },
  "rate_limits": {
    "per_minute": 60,
    "per_hour": 1200,
    "per_day": 10000,
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

For APIs using HTTP Bearer authentication, the configuration would look like:

```json
"authentication": {
  "type": "http",
  "scheme": "bearer",
  "value": "your-token-here"
}
```

### Running the Tool

```bash
# Add API configuration and crawl documentation
python -m src.main add --config example_config.json

# Start server with custom host and port
python -m src.main serve --config example_config.json --host 127.0.0.1 --port 9000
```

## How It Works

1. The tool reads your API configuration from a JSON file
2. It loads the OpenAPI specification from a URL or file
3. It crawls the API documentation (if provided) to extract relevant information
4. It generates MCP tools based on the OpenAPI endpoints
5. It applies authentication, rate limiting, and retry configurations to the tools
6. It creates MCP resources from the crawled documentation
7. It generates helpful prompts for using the API
8. It launches an MCP server that LLM clients can connect to

## System Components

### OpenAPI Processing

The OpenAPI module provides robust parsing capabilities for OpenAPI specifications:

- **Spec Parser**: Extracts endpoints, parameters, responses, and schemas
- **Reduced Spec**: Creates a simplified representation focusing on essential components
- **Authentication Config**: Flexibly handles different auth methods (API keys, Bearer tokens)

### Documentation Processing

The documentation crawler extracts valuable information from API documentation:

- Crawls landing pages and follows links
- Uses LLM-based link review to identify relevant content
- Vectorizes content for retrieval-augmented generation (RAG)
- Connects usage data with API schema for better tool generation

### Rate Limiting

Rate limiting is implemented using a token bucket algorithm that can enforce limits at multiple levels:

- Requests per minute
- Requests per hour (optional)
- Requests per day (optional)

This helps prevent API throttling and ensures your application stays within usage limits.

### Retry Mechanism

The retry system provides resilience by automatically retrying failed requests:

- Configurable retry attempts with exponential backoff
- Retries on specific HTTP status codes (defaults to 429, 500, 502, 503, 504)
- Automatic handling of connection errors and timeouts

### Prompt Generation

The system generates useful prompts for working with APIs:

- Creates examples based on endpoint documentation
- Provides context from the documentation RAG system
- Suggests parameter values based on API schemas

## Testing

AutoMCP includes a comprehensive test suite for verifying functionality:

- **Unit Tests**: Individual modules and components using Python's unittest
- **Models**: Tests for data models and validation logic
- **Utility Classes**: Rate limiting and retry mechanism tests
- **OpenAPI Parsing**: Tests for spec parsing and transformation

See the [tests/README.md](tests/README.md) for more details on running tests.

## Compatibility

AutoMCP works with the following libraries:

- [Google's ADK Python](https://github.com/google/adk-python)
- [Hugging Face's SmolaGents](https://huggingface.co/docs/smolagents/index)
- [LangChain's LangGraph](https://www.langchain.com/langgraph)

## License

This project is licensed under the MIT License - see the LICENSE file for details.