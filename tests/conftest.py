"""Configuration file for pytest."""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add src directory to the path so tests can import modules correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fixtures for test data


@pytest.fixture
def sample_mcp_config():
    """Return a sample MCP configuration for testing."""
    return {
        "api_name": "test-api",
        "api_description": "Test API",
        "tools": [
            {
                "name": "test_tool",
                "description": "Test tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "Parameter 1"}
                    },
                    "required": ["param1"],
                },
            }
        ],
        "resources": {"test_resource": {"content": "Test content"}},
        "prompts": {"test_prompt": "Test prompt"},
    }


@pytest.fixture
def sample_openapi_spec():
    """Return a sample OpenAPI specification for testing."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "description": "API for testing",
            "version": "1.0.0",
        },
        "servers": [{"url": "https://api.example.com/v1"}],
        "paths": {
            "/test": {
                "get": {
                    "operationId": "testGet",
                    "summary": "Test endpoint",
                    "description": "Test endpoint description",
                    "parameters": [
                        {
                            "name": "param1",
                            "in": "query",
                            "description": "Test parameter",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"result": {"type": "string"}},
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }


@pytest.fixture
def sample_api_config():
    """Return a sample API configuration for testing."""
    return {
        "name": "test-api",
        "display_name": "Test API",
        "description": "API for testing",
        "openapi_spec_url": "https://api.example.com/openapi.json",
        "documentation_url": "https://api.example.com/docs",
        "authentication": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "value": "test-api-key",
        },
        "rate_limits": {"per_minute": 60, "per_hour": 1000, "enabled": True},
        "retry": {
            "max_retries": 3,
            "backoff_factor": 0.5,
            "retry_on_status_codes": [429, 500, 502, 503, 504],
            "enabled": True,
        },
    }


@pytest.fixture
def sample_api_config_with_db():
    """Return a sample API configuration with db_directory for testing."""
    return {
        "name": "test-api-db",
        "display_name": "Test API with DB",
        "description": "API for testing with custom DB directory",
        "openapi_spec_url": "https://api.example.com/openapi.json",
        "documentation_url": "https://api.example.com/docs",
        "db_directory": "./test_custom_db",
        "authentication": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "value": "test-api-key",
        },
    }


@pytest.fixture
def temp_registry_file():
    """Create a temporary registry file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp.write(b"{}")
        tmp_path = tmp.name

    yield tmp_path

    # Cleanup after test
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
