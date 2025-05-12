import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Assuming these are the locations based on previous tests
from src.server.mcp import MCPServer
from src.models import MCPToolsetConfig
from src.openapi.tools import OpenAPIToolkit, RestApiTool, FastMCPOpenAPITool
from src.documentation.resources import ResourceManager
from fastmcp.prompts import Prompt

# Mock the actual FastMCPOpenAPITool to avoid its complexities during MCPServer tests
# We just need to know it was called.
class MockFastMCPOpenAPITool:
    def __init__(self, rest_tool):
        self.rest_tool = rest_tool
        self.name = rest_tool.name

@patch('src.server.mcp.FastMCPOpenAPITool', new=MockFastMCPOpenAPITool)
@patch('src.server.mcp.FastMCP')
class TestMCPServer(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Mock MCPToolsetConfig and its components
        self.mock_mcp_config = MagicMock(spec=MCPToolsetConfig)
        self.mock_mcp_config.name = "TestMCPApp"
        self.mock_mcp_config.api_description = "Test API Description"
        
        self.mock_api_toolkit = MagicMock(spec=OpenAPIToolkit)
        self.mock_resource_manager = MagicMock(spec=ResourceManager)
        self.mock_prompts = [MagicMock(spec=Prompt), MagicMock(spec=Prompt)]

        self.mock_mcp_config.toolkit = self.mock_api_toolkit
        self.mock_mcp_config.resource_manager = self.mock_resource_manager
        self.mock_mcp_config.prompts = self.mock_prompts
        
    def test_init_stores_config_and_creates_mcp(self, MockFastMCP):
        """Test that __init__ stores config and calls _create_mcp_instance."""
        server = MCPServer(self.mock_mcp_config, host="host", port=123, debug=True, db_directory="db")
        
        self.assertEqual(server.mcp_config, self.mock_mcp_config)
        self.assertEqual(server.host, "host")
        self.assertEqual(server.port, 123)
        self.assertTrue(server.debug)
        self.assertEqual(server.db_directory, "db")
        self.assertEqual(server.resource_manager, self.mock_resource_manager)
        self.assertEqual(server.api_toolkit, self.mock_api_toolkit)
        MockFastMCP.assert_called_once_with("TestMCPApp", description="Test API Description")
        self.assertIsNotNone(server.mcp) # Should be the instance returned by MockFastMCP



    def test_create_mcp_instance_with_tools(self, MockFastMCP):
        """Test tool registration."""
        # Create mock for FastMCP instance with public methods
        mock_mcp_instance = MockFastMCP.return_value
        mock_mcp_instance.tool = MagicMock()
        
        # Setup toolkit mocks
        mock_rest_tool1 = MagicMock(spec=RestApiTool, name="tool_one")
        mock_rest_tool1.name = "tool_one"
        mock_rest_tool1.description = "Tool One Description"
        
        mock_rest_tool2 = MagicMock(spec=RestApiTool, name="tool_two")
        mock_rest_tool2.name = "tool_two"
        mock_rest_tool2.description = "Tool Two Description"
        
        tool_schema1 = {"name": "tool_one", "description": "Tool One Description"}
        tool_schema2 = {"name": "tool_two", "description": "Tool Two Description"}
        self.mock_api_toolkit.get_tool_schemas.return_value = [tool_schema1, tool_schema2]
        self.mock_api_toolkit.get_tool.side_effect = lambda name: mock_rest_tool1 if name == "tool_one" else mock_rest_tool2

        # Make RM and prompts empty for this test
        self.mock_mcp_config.resource_manager = None
        self.mock_mcp_config.prompts = []

        server = MCPServer(self.mock_mcp_config)

        # Verify toolkit methods were called to get tool information
        self.mock_api_toolkit.get_tool_schemas.assert_called_once()
        self.assertEqual(self.mock_api_toolkit.get_tool.call_count, 2)
        


    def test_create_mcp_instance_with_resources(self, MockFastMCP):
        """Test resource registration from ResourceManager."""
        # Create mock for FastMCP instance with public methods
        mock_mcp_instance = MockFastMCP.return_value
        mock_mcp_instance.resource = MagicMock()
        
        # Mock resource functions returned by ResourceManager
        mock_resource1 = MagicMock(return_value="Resource 1 content")
        mock_resource2 = MagicMock(return_value="Resource 2 content")
        
        # Set up ResourceManager to return resource functions
        resources_metadata = [
            {"uri": "docs://api/intro", "description": "API Introduction"},
            {"uri": "docs://api/usage", "description": "Usage Guide"}
        ]
        self.mock_resource_manager.list_resources.return_value = resources_metadata
        
        # Make toolkit and prompts empty for this test
        self.mock_mcp_config.toolkit = None
        self.mock_mcp_config.prompts = []
        # self.mock_mcp_config.resource_manager is set in setUp

        server = MCPServer(self.mock_mcp_config)

        # Verify ResourceManager methods were called
        self.mock_resource_manager.list_resources.assert_called_once()
        

if __name__ == '__main__':
    unittest.main() 