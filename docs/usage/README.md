# Usage

## Configuration

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

## Running the Tool

```bash
# Add API configuration and crawl documentation
python -m src.main add --config example_config.json

# List all registered API servers
python -m src.main list-servers

# Start server(s) - will use all registered servers if no config specified
python -m src.main serve --host 127.0.0.1 --port 9000

# Start server with specific config
python -m src.main serve --config example_config.json --host 127.0.0.1 --port 9000

# Remove an API server and its data
python -m src.main remove --name weather-api

# Generate Claude Desktop configuration
python -m src.main install claude --output .claude.json
``` 