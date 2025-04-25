# Testing Guide

AutoMCP uses pytest for testing. This guide explains how to run tests and add new ones.

## Running Tests

To run all tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=src
```

To run specific test files:

```bash
pytest tests/test_specific_file.py
```

To run specific test functions:

```bash
pytest tests/test_specific_file.py::test_specific_function
```

## Test Structure

Tests are organized by module:

- `tests/test_main.py`: Tests for the CLI functionality
- `tests/test_manager.py`: Tests for server management
- `tests/test_utils.py`: Tests for utility functions
- `tests/openapi/`: Tests for OpenAPI modules
- `tests/mcp/`: Tests for MCP server modules
- `tests/documentation/`: Tests for documentation modules
- `tests/prompt/`: Tests for prompt modules

## Writing Tests

When adding new features, create corresponding test files. Here's an example test:

```python
import pytest
from src.utils import ServerRegistry

def test_add_server():
    # Setup
    registry = ServerRegistry(registry_file=":memory:")
    
    # Exercise
    registry.add_server("test_api", "test_config.json", "test_db_dir")
    
    # Verify
    servers = registry.list_servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "test_api"
    assert servers[0]["config_path"] == "test_config.json"
    assert servers[0]["db_directory"] == "test_db_dir"
```

## Using Fixtures

Use pytest fixtures for common setup:

```python
import pytest
from src.utils import ServerRegistry

@pytest.fixture
def registry():
    """Create an in-memory registry for testing."""
    return ServerRegistry(registry_file=":memory:")

def test_add_server(registry):
    registry.add_server("test_api", "test_config.json", "test_db_dir")
    servers = registry.list_servers()
    assert len(servers) == 1
```

## Mocking External Services

Use the `unittest.mock` module or `pytest-mock` to mock external services:

```python
from unittest.mock import patch, MagicMock

def test_process_config():
    # Mock HTTP response for OpenAPI spec
    mock_response = MagicMock()
    mock_response.json.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}
    mock_response.status_code = 200
    
    with patch("requests.get", return_value=mock_response):
        config = process_config("config.json")
        assert config.name == "Test API"
```

## Testing the CLI

To test CLI commands, use the `CliRunner` from the `click.testing` module:

```python
from click.testing import CliRunner
from src.main import main

def test_list_servers_command():
    runner = CliRunner()
    result = runner.invoke(main, ["list-servers"])
    assert result.exit_code == 0
    assert "No API servers registered" in result.output
```

## Testing Standards

- Each module should have at least 80% test coverage
- Test both success and failure cases
- Test edge cases and boundary conditions
- Use meaningful assertions that help diagnose failures

## Continuous Integration

Tests are run automatically on GitHub Actions for every pull request. Ensure your tests pass locally before submitting a PR. 