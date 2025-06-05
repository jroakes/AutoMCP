import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models import MCPToolsetConfig
from src.openapi.tools import OpenAPIToolkit
from src.documentation.resources import ResourceManager


class TestMCPToolsetConfig(unittest.TestCase):

    def test_server_name_normalization(self):
        """Test that server_name properly normalizes various name formats."""
        test_cases = [
            ("My Test Service", "my_test_service"),
            ("API-Service-V2", "api-service-v2"),
            ("test_api", "test_api"),
            ("CamelCaseAPI", "camelcaseapi"),
            ("Service with (special) chars!", "service_with_(special)_chars!"),
            ("", ""),  # Edge case: empty string
        ]
        
        mock_toolkit = MagicMock(spec=OpenAPIToolkit)
        mock_resource_manager = MagicMock(spec=ResourceManager)
        
        for name, expected_server_name in test_cases:
            with self.subTest(name=name):
                config = MCPToolsetConfig(
                    name=name,
                    api_description="Test service",
                    toolkit=mock_toolkit,
                    resource_manager=mock_resource_manager,
                    prompts=[]
                )
                self.assertEqual(config.server_name, expected_server_name)


if __name__ == '__main__':
    unittest.main() 