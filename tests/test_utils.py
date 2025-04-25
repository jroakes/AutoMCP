"""Tests for utility functions."""

import json
import os
import tempfile
import unittest

from src.utils import ServerRegistry, ApiConfig


class TestServerRegistry(unittest.TestCase):
    """Tests for the ServerRegistry class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.write(b"{}")
        self.temp_registry_file = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.temp_registry_file):
            os.unlink(self.temp_registry_file)

    def test_init_creates_registry_file(self):
        """Test that initializing ServerRegistry creates the registry file."""
        # Delete the file first to ensure it's created by the registry
        if os.path.exists(self.temp_registry_file):
            os.unlink(self.temp_registry_file)

        _registry = ServerRegistry(self.temp_registry_file)
        self.assertTrue(os.path.exists(self.temp_registry_file))

        # Check that it's a valid JSON file with an empty dict
        with open(self.temp_registry_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data, {})

    def test_add_server(self):
        """Test adding a server to the registry."""
        registry = ServerRegistry(self.temp_registry_file)

        registry.add_server("test-api", "/path/to/config.json", "/path/to/db")

        # Verify the server was added
        servers = registry.list_servers()
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["name"], "test-api")
        self.assertEqual(servers[0]["config_path"], "/path/to/config.json")
        self.assertEqual(servers[0]["db_directory"], "/path/to/db")
        self.assertIn("added_at", servers[0])

    def test_list_servers(self):
        """Test listing servers from the registry."""
        registry = ServerRegistry(self.temp_registry_file)

        # Add some servers
        registry.add_server("api1", "/path/to/api1.json", "/path/to/db1")
        registry.add_server("api2", "/path/to/api2.json", "/path/to/db2")

        # List servers
        servers = registry.list_servers()
        self.assertEqual(len(servers), 2)
        self.assertEqual({s["name"] for s in servers}, {"api1", "api2"})

    def test_get_server(self):
        """Test getting a server by name."""
        registry = ServerRegistry(self.temp_registry_file)

        # Add a server
        registry.add_server("api1", "/path/to/api1.json", "/path/to/db1")

        # Get the server
        server = registry.get_server("api1")
        self.assertEqual(server["name"], "api1")
        self.assertEqual(server["config_path"], "/path/to/api1.json")

        # Non-existent server
        self.assertIsNone(registry.get_server("nonexistent"))

    def test_delete_server(self):
        """Test deleting a server."""
        registry = ServerRegistry(self.temp_registry_file)

        # Add servers
        registry.add_server("api1", "/path/to/api1.json", "/path/to/db1")
        registry.add_server("api2", "/path/to/api2.json", "/path/to/db2")

        # Delete one server
        success = registry.delete_server("api1")
        self.assertTrue(success)

        # Check it was deleted
        servers = registry.list_servers()
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["name"], "api2")

        # Try to delete non-existent server
        success = registry.delete_server("nonexistent")
        self.assertFalse(success)

    def test_get_all_config_paths(self):
        """Test getting all config paths."""
        registry = ServerRegistry(self.temp_registry_file)

        # Add servers
        registry.add_server("api1", "/path/to/api1.json", "/path/to/db1")
        registry.add_server("api2", "/path/to/api2.json", "/path/to/db2")

        # Get config paths
        paths = registry.get_all_config_paths()
        self.assertEqual(len(paths), 2)
        self.assertEqual(set(paths), {"/path/to/api1.json", "/path/to/api2.json"})

    def test_get_db_directory(self):
        """Test getting database directory for a server."""
        registry = ServerRegistry(self.temp_registry_file)

        # Add servers
        registry.add_server("api1", "/path/to/api1.json", "/path/to/db1")
        registry.add_server("api2", "/path/to/api2.json", "/path/to/db2")

        # Get db directory for existing server
        db_dir = registry.get_db_directory("api1")
        self.assertEqual(db_dir, "/path/to/db1")

        # Get db directory for non-existent server
        db_dir = registry.get_db_directory("nonexistent")
        self.assertIsNone(db_dir)


class TestApiConfig(unittest.TestCase):
    """Tests for the ApiConfig model."""

    def test_api_config_with_db(self):
        """Test creating an ApiConfig with a db_directory."""
        config_data = {
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
        config = ApiConfig(**config_data)
        self.assertEqual(config.name, "test-api-db")
        self.assertEqual(config.db_directory, "./test_custom_db")

    def test_api_config_without_db(self):
        """Test creating an ApiConfig without a db_directory."""
        config_data = {
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
        }
        config = ApiConfig(**config_data)
        self.assertEqual(config.name, "test-api")
        self.assertIsNone(config.db_directory)


if __name__ == "__main__":
    unittest.main()
