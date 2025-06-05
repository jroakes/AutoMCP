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

# Create and activate virtual environment (recommended)
python -m venv automcp_venv
source automcp_venv/bin/activate  # On Windows: automcp_venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (required for documentation embedding)
export OPENAI_API_KEY="your-openai-api-key"  # For OpenAI embeddings (default)
# OR
export HUGGINGFACE_API_KEY="your-hf-api-key"  # For Hugging Face embeddings (optional)
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
  },
  "crawl": {
    "max_pages": 50,
    "max_depth": 3,
    "rendering": false
  },
  "prompts": [
    {
      "name": "weather_usage",
      "description": "How to use the Weather API effectively",
      "content": "Use this API to get current weather data for any location. Always provide a city name."
    },
    {
      "name": "weather_with_location",
      "description": "Get weather with dynamic location",
      "content": "Get current weather for {location}. Use the get_weather endpoint.",
      "variables": ["location"]
    }
  ],
  "db_directory": "./weather_api_db"
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

### Configuration Fields

#### Required Fields
- `name`: Unique identifier for the API
- `description`: Description of the API functionality
- `openapi_spec_url`: URL to the OpenAPI specification

#### Optional Fields
- `display_name`: Human-readable name for the API
- `icon`: URL to an icon for the API
- `version`: API version
- `documentation_url`: URL to API documentation for crawling
- `db_directory`: Custom directory for storing crawled documentation (defaults to `./.chromadb/{name}`)
- `authentication`: Authentication configuration (see examples above)
- `rate_limits`: Rate limiting configuration
- `retry`: Retry configuration for failed requests
- `crawl`: Documentation crawling configuration
- `prompts`: Custom prompts served directly from the config (no auto-generation)

#### Crawl Configuration
- `max_pages`: Maximum number of pages to crawl (default: 50)
- `max_depth`: Maximum crawling depth (default: 3)
- `rendering`: Whether to use JavaScript rendering (default: false)

#### Prompt Configuration
Prompts are served exactly as specified in the config file:

```json
"prompts": [
  {
    "name": "simple_prompt",
    "description": "A basic static prompt",
    "content": "Use this API to get weather data."
  },
  {
    "name": "template_prompt", 
    "description": "A prompt with variables",
    "content": "Get weather for {location} using the API.",
    "variables": ["location"]
  },
  {
    "name": "conversation_prompt",
    "description": "A conversation-style prompt",
    "content": [
      {"role": "system", "content": "You are a weather assistant."},
      {"role": "user", "content": "How do I get weather data?"}
    ]
  }
]
```

#### Environment Variable Support
Authentication values support environment variable substitution using `${VAR_NAME}` syntax:

```json
"authentication": {
  "type": "apiKey",
  "in": "header",
  "name": "X-API-Key",
  "value": "${WEATHER_API_KEY}"
}
```

### Running the Tool

```bash
# Add API configuration and crawl documentation
python -m src.main add --config example_config.json

# Add multiple APIs from a directory
python -m src.main add --config ./configs/

# List all registered API servers
python -m src.main list-servers

# Start server(s) - will use all registered servers if no config specified
python -m src.main serve --host 127.0.0.1 --port 9000

# Start server with specific config
python -m src.main serve --config example_config.json --host 127.0.0.1 --port 9000

# Start server with multiple configs from directory
python -m src.main serve --config ./configs/ --host 127.0.0.1 --port 9000

# Remove an API server and its data
python -m src.main remove --name weather-api

# Generate Claude Desktop configuration for all registered APIs
python -m src.main install claude --output .claude.json

# Generate Claude configuration for specific APIs
python -m src.main install claude --config ./configs/ --output .claude.json
```

## How It Works

1. **Configuration**: The tool reads your API configuration from JSON files
2. **Registration**: APIs are registered in a local registry for management
3. **OpenAPI Processing**: It loads and processes the OpenAPI specification
4. **Documentation Crawling**: It crawls API documentation and creates a searchable vector database
5. **Tool Generation**: It generates MCP tools based on OpenAPI endpoints with authentication and rate limiting
6. **Resource Creation**: It creates MCP resources from crawled documentation for context
7. **Prompt Serving**: It serves custom prompts directly from the configuration file
8. **Server Launch**: It launches an MCP server that LLM clients can connect to

## Server Registry

AutoMCP maintains a registry of configured APIs, making it easy to manage multiple APIs:

- **Add APIs**: `automcp add --config api_config.json` registers an API and crawls its documentation
- **List APIs**: `automcp list-servers` shows all registered APIs
- **Remove APIs**: `automcp remove --name api-name` removes an API and optionally its data
- **Serve Multiple**: `automcp serve` starts servers for all registered APIs simultaneously

The registry is stored in `./.automcp_cache/registry.json` and tracks:
- API configurations
- Database directories
- Registration timestamps

## System Components

### MCP Server (FastMCP-based)

AutoMCP uses [FastMCP](https://github.com/modelcontextprotocol/fastmcp) to create MCP-compliant servers:

- **Tools**: Generated from OpenAPI endpoints with built-in authentication and rate limiting
- **Resources**: Static documentation pages and searchable content from crawled docs
- **Prompts**: Context-aware prompts based on API capabilities and documentation
- **Multi-API Support**: Single server instance can serve multiple APIs simultaneously

### OpenAPI Processing

The OpenAPI toolkit provides robust parsing and tool generation:

- **Spec Parser**: Extracts endpoints, parameters, responses, and schemas
- **Tool Generation**: Converts OpenAPI operations to MCP tools with validation
- **Authentication Integration**: Supports API keys, Bearer tokens, Basic auth, and OAuth2
- **Request/Response Handling**: Automatic serialization and error handling

### Documentation Processing & Vector Search

The documentation system creates searchable knowledge bases:

- **Web Crawling**: Uses Crawl4AI to extract content from documentation sites
- **Vector Storage**: ChromaDB integration for semantic search capabilities
- **Content Chunking**: Intelligent document splitting for optimal retrieval
- **Search Resources**: Dynamic search functionality exposed as MCP resources

### Rate Limiting & Resilience

Built-in protection against API throttling and failures:

- **Token Bucket Algorithm**: Enforces per-minute, per-hour, and per-day limits
- **Exponential Backoff**: Configurable retry with increasing delays
- **Status Code Handling**: Retries on specific HTTP status codes (429, 5xx)
- **Connection Resilience**: Automatic handling of timeouts and connection errors

### Prompt Management

Simple prompt serving from configuration:

- **Custom Prompts**: User-defined prompts served directly from the config file
- **Static Content**: Prompts contain only what's specified in the configuration
- **Template Support**: Prompts can include variables that are filled at runtime
- **Message Formats**: Support for both string templates and conversation-style message arrays

## Testing

AutoMCP includes a comprehensive test suite for verifying functionality:

- **Unit Tests**: Individual modules and components using Python's unittest
- **Models**: Tests for data models and validation logic
- **Utility Classes**: Rate limiting and retry mechanism tests
- **OpenAPI Parsing**: Tests for spec parsing and transformation
- **MCP Server**: Tests for FastMCP server implementation and tool registration

### Running Tests

```bash
# Activate the virtual environment
source automcp_venv/bin/activate  # On Windows: automcp_venv\Scripts\activate

# Run all tests
python -m unittest discover tests/

# Run specific test file
python -m unittest tests.test_manager

# Run with verbose output
python -m unittest discover tests/ -v
```

See the [tests/README.md](tests/README.md) for more details on running tests.

## Compatibility

AutoMCP works with the following libraries:

- [Google's ADK Python](https://github.com/google/adk-python)
- [Hugging Face's SmolaGents](https://huggingface.co/docs/smolagents/index)
- [LangChain's LangGraph](https://www.langchain.com/langgraph)

## License

This project is licensed under the MIT License - see the LICENSE file for details.