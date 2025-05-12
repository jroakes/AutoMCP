import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import httpx

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Corrected path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.openapi.tools import RestApiTool, OpenAPIToolkit, FastMCPOpenAPITool, execute_tool
from src.openapi.models import ApiEndpoint, ApiParameter, ApiAuthConfig, RateLimitConfig, RetryConfig
from src.openapi.spec import OpenAPISpecParser # Used for mocking
from fastmcp.tools.tool import _convert_to_content # For FastMCPOpenAPITool test


class TestRestApiTool(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_endpoint = MagicMock(spec=ApiEndpoint)
        self.mock_endpoint.path = "/test/{id}/items"
        self.mock_endpoint.method = "GET"
        mock_param_id = MagicMock(spec=ApiParameter, name="id", location="path", required=True, schema_definition={"type": "integer"}, description="Item ID")
        mock_param_id.name = "id" # Explicitly set
        mock_param_filter = MagicMock(spec=ApiParameter, name="filter", location="query", required=False, schema_definition={"type": "string"}, description="Filter string")
        mock_param_filter.name = "filter" # Explicitly set
        self.mock_endpoint.parameters = [mock_param_id, mock_param_filter]
        self.mock_endpoint.request_body = None
        self.mock_toolkit = MagicMock(spec=OpenAPIToolkit) # Mock the toolkit for RestApiTool

    @patch('src.openapi.tools.auth_helpers')
    def test_init_with_auth(self, mock_auth_helpers):
        mock_auth_helpers.token_to_scheme_credential.return_value = ("Bearer", "token123")
        auth_config = ApiAuthConfig(type="http", scheme="bearer", value="token123")
        
        tool = RestApiTool(
            name="TestTool", description="A test tool", endpoint=self.mock_endpoint,
            base_url="http://api.example.com", auth_config=auth_config
        )
        self.assertEqual(tool.name, "TestTool")
        self.assertEqual(tool.auth_scheme, "Bearer")
        self.assertEqual(tool.auth_credential, "token123")
        mock_auth_helpers.token_to_scheme_credential.assert_called_once()

    def test_to_schema_basic(self):
        tool = RestApiTool(
            name="GetItem", description="Get an item by ID", endpoint=self.mock_endpoint,
            base_url="http://api.example.com"
        )
        schema = tool.to_schema()
        self.assertEqual(schema["name"], "GetItem")
        self.assertEqual(schema["description"], "Get an item by ID")
        self.assertIn("id", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["properties"]["id"]["type"], "integer")
        self.assertIn("id", schema["parameters"]["required"])
        self.assertIn("filter", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["properties"]["filter"]["type"], "string")
        self.assertNotIn("filter", schema["parameters"]["required"])

    def test_to_schema_with_request_body(self):
        self.mock_endpoint.method = "POST"
        self.mock_endpoint.request_body = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "value": {"type": "number"}},
                        "required": ["name"]
                    }
                }
            }
        }
        tool = RestApiTool(
            name="CreateItem", description="Create an item", endpoint=self.mock_endpoint,
            base_url="http://api.example.com"
        )
        schema = tool.to_schema()
        self.assertIn("name", schema["parameters"]["properties"])
        self.assertEqual(schema["parameters"]["properties"]["name"]["type"], "string")
        self.assertIn("name", schema["parameters"]["required"])
        self.assertIn("value", schema["parameters"]["properties"])
        self.assertNotIn("value", schema["parameters"]["required"])

    @patch('anyio.run')
    def test_execute_sync_wrapper(self, mock_anyio_run):
        tool = RestApiTool(
            name="TestTool", description="desc", endpoint=self.mock_endpoint,
            base_url="http://api.example.com"
        )
        tool.execute_async = AsyncMock(return_value={"data": "test"})
        tool.execute(id=1, filter="abc")
        mock_anyio_run.assert_called_once_with(tool.execute_async, id=1, filter="abc")
        
    async def test_execute_async_flow(self):
        self.mock_toolkit.request = AsyncMock(return_value={"status": "success"})
        
        tool = RestApiTool(
            name="TestTool", description="A test tool", endpoint=self.mock_endpoint,
            base_url="http://api.example.com"
        )
        tool._toolkit = self.mock_toolkit # Assign the mock toolkit

        await tool.execute_async(id=123, filter="test_filter")

        self.mock_toolkit.request.assert_awaited_once_with(
            "get",
            "/test/123/items", # URL with path param substituted
            params={"filter": "test_filter"}, # Query params
            headers={}, # Header params (empty in this case)
            json=None # JSON body (None for GET)
        )


class TestOpenAPIToolkit(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_spec_parser = MagicMock(spec=OpenAPISpecParser)
        self.mock_spec_parser.get_base_url.return_value = "http://localhost:8000/api"
        self.mock_spec_parser.get_security_schemes.return_value = {}
        self.mock_spec_parser.get_security_requirements.return_value = []
        self.mock_spec_parser.get_endpoints.return_value = [] # Default to no endpoints

    @patch('src.openapi.tools.OpenAPISpecParser')
    @patch('src.openapi.tools.auth_helpers.build_httpx_auth')
    @patch('src.openapi.tools.httpx.AsyncClient')
    def test_init_basic(self, MockAsyncClient, mock_build_auth, MockSpecParser):
        MockSpecParser.return_value = self.mock_spec_parser
        mock_build_auth.return_value = ({}, None) # headers, httpx_auth

        toolkit = OpenAPIToolkit(spec={})
        
        MockSpecParser.assert_called_once_with({})
        self.mock_spec_parser.get_base_url.assert_called_once()
        mock_build_auth.assert_called_once_with(None) # No auth_config initially
        MockAsyncClient.assert_called_once()
        self.assertIsNotNone(toolkit._rate_limiter)
        self.assertIsNotNone(toolkit._retry_handler)
        self.assertEqual(toolkit.tools, []) # Since get_endpoints returns []

    @patch('src.openapi.tools.OpenAPISpecParser')
    def test_init_auth_validation_required_not_provided(self, MockSpecParser):
        self.mock_spec_parser.get_security_schemes.return_value = {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
        }
        self.mock_spec_parser.get_security_requirements.return_value = [{"ApiKeyAuth": []}]
        MockSpecParser.return_value = self.mock_spec_parser

        with self.assertRaisesRegex(ValueError, "API requires 'apiKey' authentication.*"):
            OpenAPIToolkit(spec={}, auth_config=None)

    @patch('src.openapi.tools.OpenAPISpecParser')
    def test_init_auth_validation_type_mismatch(self, MockSpecParser):
        self.mock_spec_parser.get_security_schemes.return_value = {
            "HttpAuth": {"type": "http", "scheme": "bearer"}
        }
        self.mock_spec_parser.get_security_requirements.return_value = [{"HttpAuth": []}]
        MockSpecParser.return_value = self.mock_spec_parser
        
        auth_config = ApiAuthConfig(type="apiKey", name="X-Token", in_field="header", value="xyz")
        with self.assertRaisesRegex(ValueError, "API requires HTTP authentication but config provided apiKey"):
            OpenAPIToolkit(spec={}, auth_config=auth_config)

    @patch('src.openapi.tools.OpenAPISpecParser')
    @patch('src.openapi.tools.auth_helpers.build_httpx_auth')
    @patch('src.openapi.tools.httpx.AsyncClient')
    def test_create_tools(self, MockAsyncClient, mock_build_auth, MockSpecParser):
        endpoint1_spec = {
            "operationId": "get_item", "summary": "Get an item",
            "parameters": [{"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "responses": {"200": {"description": "success"}}
        }
        endpoint2_spec = {
            "operationId": "create_item", "summary": "Create an item",
            "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
            "responses": {"201": {"description": "created"}}
        }
        self.mock_spec_parser.get_endpoints.return_value = [
            ("GET /items/{item_id}", "Get an item by ID", endpoint1_spec),
            ("POST /items", "Create a new item", endpoint2_spec),
            ("PUT /items/{item_id}", "Update an item", {}) # Should be skipped (not GET/POST)
        ]
        MockSpecParser.return_value = self.mock_spec_parser
        mock_build_auth.return_value = ({}, None)

        toolkit = OpenAPIToolkit(spec={})
        self.assertEqual(len(toolkit.tools), 2)
        self.assertEqual(toolkit.tools[0].name, "get_item")
        self.assertEqual(toolkit.tools[1].name, "create_item")
        # Ensure toolkit is set on the tool
        self.assertEqual(toolkit.tools[0]._toolkit, toolkit)

    async def test_request_method_success(self):
        # Basic setup for toolkit
        with patch('src.openapi.tools.OpenAPISpecParser', return_value=self.mock_spec_parser),\
             patch('src.openapi.tools.auth_helpers.build_httpx_auth', return_value=({}, None)),\
             patch('src.openapi.tools.httpx.AsyncClient') as MockClientConstructor:
            
            mock_http_client_instance = MockClientConstructor.return_value
            mock_response = AsyncMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.content = b'{"data": "success"}'
            mock_response.json.return_value = {"data": "success"}
            mock_http_client_instance.request = AsyncMock(return_value=mock_response)

            toolkit = OpenAPIToolkit(spec={})
            toolkit._rate_limiter.consume_token_async = AsyncMock() # Mock rate limiter

            result = await toolkit.request("get", "/test_path")

            toolkit._rate_limiter.consume_token_async.assert_awaited_once()
            mock_http_client_instance.request.assert_awaited_once_with(
                "get", "/test_path", params=None, headers=None, json=None
            )
            mock_response.raise_for_status.assert_called_once()
            self.assertEqual(result, {"data": "success"})


    async def test_aclose(self):
        with patch('src.openapi.tools.OpenAPISpecParser', return_value=self.mock_spec_parser),\
             patch('src.openapi.tools.auth_helpers.build_httpx_auth', return_value=({}, None)),\
             patch('src.openapi.tools.httpx.AsyncClient') as MockClientConstructor:
            
            mock_http_client_instance = MockClientConstructor.return_value
            mock_http_client_instance.aclose = AsyncMock()
            
            toolkit = OpenAPIToolkit(spec={})
            await toolkit.aclose()
            mock_http_client_instance.aclose.assert_awaited_once()

class TestFastMCPOpenAPITool(unittest.IsolatedAsyncioTestCase):

    async def test_run_method(self):
        mock_rest_tool = MagicMock(spec=RestApiTool)
        mock_rest_tool.name = "MyRestTool"
        mock_rest_tool.description = "REST tool description"
        # Mock to_schema to return something simple for FastMCPOpenAPITool constructor
        mock_rest_tool.to_schema.return_value = {"parameters": {"type": "object", "properties": {}}}
        
        # Mock the async execution method of RestApiTool
        raw_result = {"key": "value", "number": 123}
        mock_rest_tool.execute_async = AsyncMock(return_value=raw_result)

        # Expected FastMCP content
        expected_content = _convert_to_content(raw_result)

        fmc_tool = FastMCPOpenAPITool(mock_rest_tool)
        
        # Check basic properties inherited/set
        self.assertEqual(fmc_tool.name, "MyRestTool")
        self.assertEqual(fmc_tool.description, "REST tool description")

        # Call the _run method (which is what FastMCP calls)
        result_content = await fmc_tool._run(param1="test")

        mock_rest_tool.execute_async.assert_awaited_once_with(param1="test")
        self.assertEqual(result_content, expected_content)


class TestExecuteToolFunction(unittest.IsolatedAsyncioTestCase):
    async def test_execute_tool_success(self):
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_tool_instance = MagicMock(spec=RestApiTool)
        mock_tool_instance.execute_async = AsyncMock(return_value={"result": "done"})
        
        mock_toolkit.get_tool.return_value = mock_tool_instance
        
        tool_schema = {"name": "my_tool_name"}
        parameters = {"arg1": 1, "arg2": "val"}
        
        result = await execute_tool(tool_schema, mock_toolkit, parameters)
        
        mock_toolkit.get_tool.assert_called_once_with("my_tool_name")
        mock_tool_instance.execute_async.assert_awaited_once_with(arg1=1, arg2="val")
        self.assertEqual(result, {"result": "done"})

    async def test_execute_tool_schema_missing_name(self):
        mock_toolkit = MagicMock()
        with self.assertRaisesRegex(ValueError, "Tool schema missing 'name' field"):
            await execute_tool({}, mock_toolkit, {})

    async def test_execute_tool_not_found(self):
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_toolkit.get_tool.return_value = None # Tool not found
        tool_schema = {"name": "unknown_tool"}
        
        with self.assertRaisesRegex(ValueError, "Tool 'unknown_tool' not found in toolkit"):
            await execute_tool(tool_schema, mock_toolkit, {})


if __name__ == '__main__':
    unittest.main() 