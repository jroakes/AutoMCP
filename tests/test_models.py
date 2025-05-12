import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models import MCPToolsetConfig
# We need to mock these classes as they are complex dependencies
from src.openapi.tools import OpenAPIToolkit
from src.documentation.resources import ResourceManager
from fastmcp.prompts import Prompt # Assuming Prompt is a class

class TestMCPToolsetConfig(unittest.TestCase):

    def test_instantiation_and_server_name(self):
        """Test basic instantiation and the server_name property."""
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_resource_manager = MagicMock(spec=ResourceManager)
        mock_prompt = MagicMock(spec=Prompt)

        config_data = {
            "name": "My Test Service",
            "api_description": "A service for testing.",
            "openapi_spec": {"openapi": "3.0.0", "info": {"title": "Test Spec"}},
            "toolkit": mock_toolkit,
            "resource_manager": mock_resource_manager,
            "prompts": [mock_prompt]
        }

        mcp_config = MCPToolsetConfig(**config_data)

        self.assertEqual(mcp_config.name, "My Test Service")
        self.assertEqual(mcp_config.api_description, "A service for testing.")
        self.assertEqual(mcp_config.openapi_spec, {"openapi": "3.0.0", "info": {"title": "Test Spec"}})
        self.assertEqual(mcp_config.toolkit, mock_toolkit)
        self.assertEqual(mcp_config.resource_manager, mock_resource_manager)
        self.assertEqual(mcp_config.prompts, [mock_prompt])

        # Test server_name property
        self.assertEqual(mcp_config.server_name, "my_test_service")

    def test_server_name_empty(self):
        """Test server_name property with an empty name."""
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_resource_manager = MagicMock(spec=ResourceManager)

        config_data = {
            "name": "",
            "api_description": "Empty name service.",
            "toolkit": mock_toolkit,
            "resource_manager": mock_resource_manager,
            "prompts": []
        }
        mcp_config = MCPToolsetConfig(**config_data)
        self.assertEqual(mcp_config.server_name, "")

    def test_optional_openapi_spec(self):
        """Test that openapi_spec is optional."""
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_resource_manager = MagicMock(spec=ResourceManager)

        config_data = {
            "name": "No Spec Service",
            "api_description": "A service without a spec.",
            # openapi_spec is omitted
            "toolkit": mock_toolkit,
            "resource_manager": mock_resource_manager,
            "prompts": []
        }
        mcp_config = MCPToolsetConfig(**config_data)
        self.assertIsNone(mcp_config.openapi_spec)
        self.assertEqual(mcp_config.server_name, "no_spec_service")


if __name__ == '__main__':
    unittest.main() 