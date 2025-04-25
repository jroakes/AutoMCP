"""Tests for the manager module."""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.manager import prepare_resource_manager
from src.utils import ApiConfig


class TestResourceManager(unittest.TestCase):
    """Tests for the resource manager functions."""

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_prepare_resource_manager_with_config_db(
        self, mock_crawler_class, mock_resource_manager
    ):
        """Test prepare_resource_manager using db_directory from config."""
        # Setup resource manager mock
        mock_instance = MagicMock()
        mock_instance.is_empty.return_value = True
        mock_resource_manager.return_value = mock_instance

        # Setup crawler mock to prevent actual crawling
        mock_crawler_instance = MagicMock()
        mock_crawler_class.return_value = mock_crawler_instance
        mock_crawler_instance.crawl.return_value = []

        # Create a config with db_directory
        api_config = ApiConfig(
            name="test-api",
            description="Test API",
            openapi_spec_url="https://api.example.com/openapi.json",
            documentation_url="https://api.example.com/docs",
            db_directory="./custom_db_path",
        )

        # Call the function
        prepare_resource_manager(api_config, db_directory="./default_db")

        # Verify ResourceManager was created with the config db_directory
        mock_resource_manager.assert_called_once()
        args, kwargs = mock_resource_manager.call_args
        self.assertEqual(kwargs["db_directory"], "./custom_db_path")

        # Verify server_name is passed correctly
        self.assertEqual(kwargs["server_name"], "test-api")

        # Verify that crawl was called
        mock_crawler_instance.crawl.assert_called_once()

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_prepare_resource_manager_with_default_db(
        self, mock_crawler_class, mock_resource_manager
    ):
        """Test prepare_resource_manager using default db_directory."""
        # Setup resource manager mock
        mock_instance = MagicMock()
        mock_instance.is_empty.return_value = True
        mock_resource_manager.return_value = mock_instance

        # Setup crawler mock to prevent actual crawling
        mock_crawler_instance = MagicMock()
        mock_crawler_class.return_value = mock_crawler_instance
        mock_crawler_instance.crawl.return_value = []

        # Create a config without db_directory
        api_config = ApiConfig(
            name="test-api",
            description="Test API",
            openapi_spec_url="https://api.example.com/openapi.json",
            documentation_url="https://api.example.com/docs",
        )

        # Call the function
        prepare_resource_manager(api_config, db_directory="./default_db")

        # Verify ResourceManager was created with the derived path
        mock_resource_manager.assert_called_once()
        args, kwargs = mock_resource_manager.call_args
        self.assertEqual(
            kwargs["db_directory"], os.path.join("./default_db", "test-api")
        )

        # Verify server_name is passed correctly
        self.assertEqual(kwargs["server_name"], "test-api")

        # Verify that crawl was called
        mock_crawler_instance.crawl.assert_called_once()

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_prepare_resource_manager_crawls_when_empty(
        self, mock_crawler_class, mock_resource_manager
    ):
        """Test that prepare_resource_manager crawls when the database is empty."""
        # Setup resource manager mock
        mock_instance = MagicMock()
        mock_instance.is_empty.return_value = True
        mock_resource_manager.return_value = mock_instance

        # Setup crawler mock to prevent actual crawling
        mock_crawler_instance = MagicMock()
        mock_crawler_class.return_value = mock_crawler_instance
        mock_crawler_instance.crawl.return_value = []

        # Create a config
        api_config = ApiConfig(
            name="test-api",
            description="Test API",
            openapi_spec_url="https://api.example.com/openapi.json",
            documentation_url="https://api.example.com/docs",
        )

        # Call the function
        prepare_resource_manager(api_config)

        # Verify crawler was created and crawl was called
        mock_crawler_class.assert_called_once()
        mock_crawler_instance.crawl.assert_called_once()

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_prepare_resource_manager_skips_crawl_when_not_empty(
        self, mock_crawler_class, mock_resource_manager
    ):
        """Test that prepare_resource_manager skips crawling when the database is not empty."""
        # Setup resource manager mock
        mock_instance = MagicMock()
        mock_instance.is_empty.return_value = False
        mock_resource_manager.return_value = mock_instance

        # Create a config
        api_config = ApiConfig(
            name="test-api",
            description="Test API",
            openapi_spec_url="https://api.example.com/openapi.json",
            documentation_url="https://api.example.com/docs",
        )

        # Call the function
        prepare_resource_manager(api_config)

        # Verify crawler was not created
        mock_crawler_class.assert_not_called()

    @patch("src.manager.ResourceManager")
    def test_prepare_resource_manager_returns_none_without_doc_url(
        self, mock_resource_manager
    ):
        """Test that prepare_resource_manager returns None when documentation_url is missing."""
        # Create a config without documentation_url
        api_config = ApiConfig(
            name="test-api",
            description="Test API",
            openapi_spec_url="https://api.example.com/openapi.json",
        )

        # Call the function
        result = prepare_resource_manager(api_config)

        # Verify ResourceManager was not created
        mock_resource_manager.assert_not_called()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
