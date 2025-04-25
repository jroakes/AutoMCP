# AutoMCP Tests

This directory contains tests for the AutoMCP project.

## Test Structure

- `/mcp`: Tests for the MCP module
  - `test_server.py`: Unit tests for the MCP server
  - `test_integration.py`: Integration tests for the MCP server (skipped by default)
- `/openapi`: Tests for the OpenAPI module
  - `test_models.py`: Tests for the data models (ApiParameter, ApiEndpoint, RetryConfig, etc.)
  - `test_spec.py`: Tests for the OpenAPI spec parser
  - `test_utils.py`: Tests for utility classes (RetryHandler, RateLimiter)
  - `test_retry_handler.py`: Detailed tests for the retry mechanism
  - `test_rate_limiter.py`: Detailed tests for the rate limiting functionality
  - `test_pagination.py`: Tests for the pagination functionality
- `/conftest.py`: Pytest configuration and fixtures

## Dependency Mocking

The tests use Python's `unittest.mock` to mock external dependencies like the `fastmcp` module. This allows tests to run even if certain dependencies are not installed or configured in the test environment.

### AsyncIO Support

The MCP server uses FastAPI (an async framework), so our tests include special considerations:

- `AsyncMagicMock` class to support awaitable mock objects
- Proper patching of FastAPI components instead of HTTPServer
- Unit tests focus on logic rather than HTTP handlers

## Running Tests

### Preferred Method: Enhanced Test Runner

AutoMCP ships with an enhanced test-runner script that provides colored output,
better summaries, log-capture, and smart filtering:

```bash
# Run the complete suite (default verbosity)
python scripts/tests/run_tests.py

# Verbose output
python scripts/tests/run_tests.py --verbose

# Quiet mode – only errors
python scripts/tests/run_tests.py --quiet

# Run only tests matching a pattern
python scripts/tests/run_tests.py --filter=mcp  # any substring match

# Run a specific test module
python scripts/tests/run_tests.py --module=test_utils

# Stop on first failure
python scripts/tests/run_tests.py --failfast
```

Run `python scripts/tests/run_tests.py --help` to see the full list of
available options (mirrors the docstring at the top of the script).

### Alternative Methods

If you prefer, you can still execute the tests directly with `unittest` or
`pytest`.

#### Unit Tests with Unittest

```bash
# Run all tests
python -m unittest discover -s tests

# Run specific test file
python -m unittest tests/mcp/test_server.py

# Run specific test class
python -m unittest tests.mcp.test_server.TestMCPServer

# Run specific test method
python -m unittest tests.mcp.test_server.TestMCPServer.test_init

# Run OpenAPI module tests
python -m unittest discover -s tests/openapi
```

#### Unit Tests with Pytest

```bash
# Install pytest if not already installed
pip install pytest pytest-cov

# Run all tests
pytest

# Run specific test file
pytest tests/mcp/test_server.py

# Run with coverage report
pytest --cov=src tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/

# Run only OpenAPI tests
pytest tests/openapi/

# Run only pagination tests
pytest tests/openapi/test_pagination.py

# Run specific pagination test
pytest tests/openapi/test_pagination.py::TestPaginationHandler::test_parse_link_header
```

## Integration Tests

The integration tests require running an actual HTTP server and making real HTTP requests. They are **skipped by default** due to their dependency on a functioning FastAPI environment.

To run integration tests (needs FastAPI, uvicorn and other dependencies):

```bash
# First, install required dependencies
pip install fastapi uvicorn

# Then run only integration tests with skip directive removed
pytest tests/mcp/test_integration.py -k "test_mcp_endpoints"
```

### Testing Pagination with Real APIs

To test pagination with real APIs, you may want to set up integration tests with services that support various pagination mechanisms:

- GitHub API (Link header-based)
- Twitter API (cursor-based)
- Standard RESTful APIs (offset/limit or page-based)

These tests should verify:
1. Proper detection of pagination mechanism
2. Correct parameter generation for subsequent pages
3. Accurate combining of multi-page results
4. Respecting max_pages limits
5. Error handling for pagination edge cases

## Test Fixtures

Common test fixtures are defined in `conftest.py` and include:

- `sample_mcp_config`: A sample MCP configuration
- `sample_openapi_spec`: A sample OpenAPI specification
- `sample_api_config`: A sample API configuration

Use these fixtures in your tests to maintain consistent test data.

## OpenAPI Testing Details

### Model Testing

The `test_models.py` module tests the data models used throughout the application:
- Tests initialization with default and custom values
- Tests property behaviors
- Verifies model relationships

### Spec Parser Testing

The `test_spec.py` file verifies the OpenAPI specification parser functionality:
- Loading specs from different sources (JSON/YAML/dictionary)
- Extracting endpoints and their details
- Obtaining authentication schemes
- Reducing specs to essential components

### Utility Testing

The utility tests focus on:
- Rate limiting implementation (token bucket algorithm)
- Retry mechanism with exponential backoff
- Error handling

#### Rate Limiter Testing

For the rate limiter, tests verify:
- Proper token consumption based on configured rates
- Token refilling over time
- Wait time calculations for depleted tokens
- Proper behavior when rate limiting is disabled

#### Retry Handler Testing

For the retry handler, tests verify:
- Status code-based retry decisions
- Backoff time calculations
- Proper behavior with different retry configurations
- Retry disabling functionality

#### Pagination Handler Testing

For the pagination handler, tests verify:
- Link header parsing (RFC 5988)
- Cursor extraction from response data
- Result combining from multiple pages
- Parameter generation for different pagination mechanisms:
  - Link header-based pagination
  - Cursor-based pagination
  - Offset/limit-based pagination
  - Page-based pagination
- Maximum page limit enforcement

The pagination system supports four common pagination mechanisms:

1. **Link Header-based Pagination**: Parses `Link` headers according to RFC 5988, commonly used by GitHub and other APIs
2. **Cursor-based Pagination**: Uses a cursor/token from the response to request the next page
3. **Offset/Limit Pagination**: Increments an offset parameter based on the limit
4. **Page-based Pagination**: Increments a page number parameter

The system can also auto-detect the pagination mechanism at runtime based on response structure.

Example pagination configuration:
```python
pagination_config = PaginationConfig(
    enabled=True,
    mechanism="auto",  # or "link", "cursor", "offset", "page"
    max_pages=5,
    cursor_param="cursor",
    cursor_response_field="next_cursor",
    offset_param="offset",
    limit_param="limit",
    page_param="page",
    results_field="items"
)
```

## Troubleshooting

If you encounter import errors related to external dependencies:

1. Ensure that all mocked modules are properly defined in the test files
2. Check for circular imports in your actual code
3. For async-related errors, ensure you're using `AsyncMagicMock` for any awaitable objects

## FastAPI Testing Considerations

When testing FastAPI applications:

1. Use `AsyncMagicMock` for async components
2. Consider using `TestClient` from FastAPI for API testing (requires additional setup)
3. Focus on testing the business logic rather than the API mechanics when possible
4. For full API tests, consider using a separate test environment with dependencies installed

## Adding New Tests

When adding new tests:

1. Create test modules that match the structure of the `src` directory
2. Use proper assertions and test utilities
3. Add common fixtures to `conftest.py`
4. Follow the existing naming conventions for test classes and methods 

## Mock Usage Notes

For tests involving API calls, we use mocks to:
- Simulate network requests without making actual calls
- Verify correct parameters and headers are provided
- Test error handling scenarios
- Control response timing for rate limiting tests

Example:
```python
@patch('requests.get')
def test_api_call(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_get.return_value = mock_response
    
    # Test your function that makes API calls
    result = your_function()
    
    # Verify the mock was called correctly
    mock_get.assert_called_once()
    # Test the result
    self.assertEqual(result, "expected") 