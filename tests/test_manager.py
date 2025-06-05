import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import sys
import tempfile

# Add patch for dotenv.load_dotenv at the top level
patch("dotenv.load_dotenv", return_value=True).start()

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.manager import process_config, prepare_resource_manager
from src.utils import ApiConfig
from src.openapi.models import RateLimitConfig, RetryConfig


class TestProcessConfig(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.manager.load_spec_from_url")
    def test_process_config_with_spec_loading(self, mock_load_spec, mock_file_open):
        """Test config processing with OpenAPI spec loading."""
        config_data = {
            "name": "Test API",
            "description": "A test API.",
            "openapi_spec_url": "http://example.com/openapi.json",
            "documentation_url": "http://example.com/docs",
        }
        mock_file_open.return_value.read.return_value = json.dumps(config_data)
        mock_load_spec.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}

        api_config = process_config("dummy_path.json")

        self.assertEqual(api_config.name, "Test API")
        self.assertIsNotNone(api_config.openapi_spec)
        mock_load_spec.assert_called_once_with("http://example.com/openapi.json")

    @patch("builtins.open", new_callable=mock_open)
    @patch.dict(os.environ, {"TEST_API_KEY": "secretkey123"})
    def test_process_config_environment_variable_substitution(self, mock_file_open):
        """Test that environment variables are properly substituted in auth config."""
        config_data = {
            "name": "Test Auth API",
            "description": "An API with auth.",
            "openapi_spec_url": "http://example.com/auth_openapi.json",
            "documentation_url": "http://example.com/auth_docs",
            "authentication": {
                "type": "http",
                "scheme": "bearer",
                "value": "{TEST_API_KEY}",
            },
        }
        mock_file_open.return_value.read.return_value = json.dumps(config_data)
        
        with patch("src.manager.load_spec_from_url", return_value=None):
             api_config = process_config("dummy_auth_path.json")

        self.assertEqual(api_config.authentication.value, "secretkey123")

    @patch("builtins.open", new_callable=mock_open)
    def test_process_config_missing_file_error(self, mock_file_open):
        """Test that missing config files raise appropriate errors."""
        mock_file_open.side_effect = FileNotFoundError("Config file not found")
        
        with self.assertRaises(FileNotFoundError):
            process_config("nonexistent_config.json")

    @patch("builtins.open", new_callable=mock_open)
    def test_process_config_invalid_json_error(self, mock_file_open):
        """Test that invalid JSON in config files raises appropriate errors."""
        mock_file_open.return_value.read.return_value = "invalid json content"
        
        with self.assertRaises(json.JSONDecodeError):
            process_config("invalid_config.json")


class TestPrepareResourceManager(unittest.TestCase):

    def test_skip_resource_manager_when_no_documentation_url(self):
        """Test that resource manager preparation is skipped when no documentation URL is provided."""
        api_config = ApiConfig(
            name="No Docs API",
            description="API without documentation URL.",
            openapi_spec_url="http://nodoc.com/spec.json",
            documentation_url=None,
        )
        rm = prepare_resource_manager(api_config, "dummy_db_dir")
        self.assertIsNone(rm)

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_crawl_triggered_when_database_empty(self, MockDocumentationCrawler, MockResourceManager):
        """Test that crawling is triggered when the database is empty."""
        api_config = ApiConfig(
            name="Crawl API",
            description="API that needs crawling.",
            openapi_spec_url="http://crawl.com/spec.json",
            documentation_url="http://crawl.com/docs",
        )
        
        # Mock empty database
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.is_empty.return_value = True

        rm = prepare_resource_manager(api_config, "/fake/db/dir")

        # Verify crawler was instantiated and crawl was called
        MockDocumentationCrawler.assert_called_once()
        mock_crawler_instance = MockDocumentationCrawler.return_value
        mock_crawler_instance.crawl.assert_called_once()

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_skip_crawl_when_database_exists(self, MockDocumentationCrawler, MockResourceManager):
        """Test that crawling is skipped when database already exists."""
        api_config = ApiConfig(
            name="Existing DB API",
            description="API with existing database.",
            openapi_spec_url="http://existing.com/spec.json",
            documentation_url="http://existing.com/docs",
        )
        
        # Mock existing database
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.is_empty.return_value = False

        rm = prepare_resource_manager(api_config, "/fake/db/dir")

        # Verify crawler was NOT called
        MockDocumentationCrawler.assert_not_called()

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_crawl_configuration_passed_correctly(self, MockDocumentationCrawler, MockResourceManager):
        """Test that crawl configuration parameters are passed correctly."""
        api_config = ApiConfig(
            name="Config Crawl API",
            description="API with crawl config.",
            openapi_spec_url="http://config.com/spec.json",
            documentation_url="http://config.com/docs",
            crawl={"max_pages": 25, "max_depth": 5, "rendering": True}
        )
        
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.is_empty.return_value = True

        prepare_resource_manager(api_config, "/fake/db/dir")

        # Verify crawler was called with correct parameters
        MockDocumentationCrawler.assert_called_once()
        call_args = MockDocumentationCrawler.call_args
        self.assertEqual(call_args.kwargs['max_pages'], 25)
        self.assertEqual(call_args.kwargs['max_depth'], 5)
        self.assertTrue(call_args.kwargs['rendering'])


if __name__ == "__main__":
    unittest.main() 