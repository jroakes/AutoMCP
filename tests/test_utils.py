import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import sys
import datetime
import yaml

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import (
    load_spec_from_file,
    load_spec_from_url,
    substitute_env_vars,
    ApiConfig,
    ServerRegistry,
    CrawlConfig, # Import CrawlConfig
)
from src.openapi.models import ApiAuthConfig, RateLimitConfig, RetryConfig
from src.constants import DEFAULT_REGISTRY_FILE


class TestLoadSpecFromFile(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    def test_load_json_file(self, mock_file):
        mock_file.return_value.read.return_value = '{"openapi": "3.0.0"}'
        spec = load_spec_from_file("test.json")
        self.assertEqual(spec, {"openapi": "3.0.0"})
        mock_file.assert_called_once_with("test.json", "r")

    @patch("src.utils.yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_yaml_file(self, mock_file, mock_yaml_load):
        mock_yaml_load.return_value = {"openapi": "3.0.0"}
        mock_file.return_value.read.return_value = "openapi: 3.0.0"
        
        spec = load_spec_from_file("test.yaml")
        self.assertEqual(spec, {"openapi": "3.0.0"})
        mock_file.assert_called_once_with("test.yaml", "r")
        mock_yaml_load.assert_called_once()

    @patch("src.utils.yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_yml_file(self, mock_file, mock_yaml_load):
        mock_yaml_load.return_value = {"openapi": "3.0.0"}
        mock_file.return_value.read.return_value = "openapi: 3.0.0"

        spec = load_spec_from_file("test.yml")
        self.assertEqual(spec, {"openapi": "3.0.0"})
        mock_file.assert_called_once_with("test.yml", "r")
        mock_yaml_load.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_unsupported_extension(self, mock_file):
        mock_file.return_value.read.return_value = "some text"
        with self.assertRaises(ValueError) as context:
            load_spec_from_file("test.txt")
        self.assertIn("Unsupported file extension: .txt", str(context.exception))


class TestLoadSpecFromUrl(unittest.TestCase):

    @patch("src.utils.requests.get")
    def test_load_json_from_url_content_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"openapi": "3.0.0"}
        mock_get.return_value = mock_response

        spec = load_spec_from_url("http://example.com/spec.json")
        self.assertEqual(spec, {"openapi": "3.0.0"})
        mock_get.assert_called_once_with("http://example.com/spec.json", timeout=30)
        mock_response.raise_for_status.assert_called_once()

    @patch("src.utils.requests.get")
    def test_load_yaml_from_url_content_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/x-yaml"}
        mock_response.text = "openapi: 3.0.0"
        mock_get.return_value = mock_response

        spec = load_spec_from_url("http://example.com/spec.yaml")
        self.assertEqual(spec, {"openapi": "3.0.0"})

    @patch("src.utils.requests.get")
    def test_load_yaml_from_url_extension(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"} # Non-specific content type
        mock_response.text = "openapi: 3.0.0"
        mock_get.return_value = mock_response

        spec = load_spec_from_url("http://example.com/spec.yml")
        self.assertEqual(spec, {"openapi": "3.0.0"})

    @patch("src.utils.requests.get")
    def test_load_from_url_fallback_json_then_yaml(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"}
        # First, make it fail JSON parsing, then succeed YAML
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_response.text = "openapi: 3.0.0" # Valid YAML
        mock_get.return_value = mock_response

        spec = load_spec_from_url("http://example.com/spec_fallback")
        self.assertEqual(spec, {"openapi": "3.0.0"})
        mock_response.json.assert_called_once() # Attempted JSON
        
    @patch("src.utils.requests.get")
    def test_load_from_url_failed_parsing(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        # Make yaml.safe_load also fail
        with patch("src.utils.yaml.safe_load", side_effect=yaml.YAMLError("yaml err")):
            mock_get.return_value = mock_response
            with self.assertRaises(ValueError) as context:
                load_spec_from_url("http://example.com/spec_fail_all")
            self.assertIn("Unable to parse response as JSON or YAML", str(context.exception))


class TestSubstituteEnvVars(unittest.TestCase):
    """Test environment variable substitution logic."""

    @patch.dict(os.environ, {"MY_VAR": "my_value", "OTHER_VAR": "other_value"})
    def test_substitute_single_var(self):
        result = substitute_env_vars("Hello {MY_VAR}")
        self.assertEqual(result, "Hello my_value")

    @patch.dict(os.environ, {})  # No vars
    def test_missing_var(self):
        result = substitute_env_vars("Value: {MISSING_VAR}")
        self.assertEqual(result, "Value: {MISSING_VAR}")  # Should remain unchanged

    def test_none_input(self):
        result = substitute_env_vars(None)
        self.assertIsNone(result)


class TestApiConfig(unittest.TestCase):
    """Test API configuration processing logic."""

    def test_basic_instantiation(self):
        config = ApiConfig(
            name="Test API",
            description="A test API",
            openapi_spec_url="http://example.com/spec.json",
        )
        self.assertEqual(config.name, "Test API")
        self.assertEqual(config.server_name, "test_api") # Test property

    def test_server_name_property(self):
        """Test server name normalization."""
        config = ApiConfig(
            name="My Awesome API V2",
            description="Desc",
            openapi_spec_url="url"
        )
        self.assertEqual(config.server_name, "my_awesome_api_v2")
        config_no_name = ApiConfig(name="", description="d", openapi_spec_url="u")
        self.assertEqual(config_no_name.server_name, "")

    def test_auth_conversion_apikey_in_to_in_field(self):
        data = {
            "name": "API", "description": "d", "openapi_spec_url": "url",
            "authentication": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
        }
        config = ApiConfig(**data)
        self.assertIsInstance(config.authentication, ApiAuthConfig)
        self.assertEqual(config.authentication.type, "apiKey")
        self.assertEqual(config.authentication.in_field, "header")
        self.assertEqual(config.authentication.name, "X-API-Key")

    def test_auth_conversion_bearer_token_correction(self):
        """Test automatic Bearer token format correction."""
        data = {
            "name": "API", "description": "d", "openapi_spec_url": "url",
            "authentication": {
                "type": "apiKey", 
                "in": "header", 
                "name": "Authorization", 
                "value": "Bearer mysecrettoken"
            }
        }
        with patch("src.utils.logger") as mock_logger:
            config = ApiConfig(**data)
            mock_logger.info.assert_called_with("Converting Bearer token from apiKey to http authentication format")
        
        self.assertIsInstance(config.authentication, ApiAuthConfig)
        self.assertEqual(config.authentication.type, "http")
        self.assertEqual(config.authentication.scheme, "bearer")
        self.assertEqual(config.authentication.value, "mysecrettoken")

    def test_nested_config_conversion(self):
        """Test proper conversion of nested configuration objects."""
        data = {
            "name": "Full API", "description": "d", "openapi_spec_url": "url",
            "rate_limits": {"requests_per_minute": 10, "max_tokens_per_minute": 1000},
            "retry": {"max_retries": 5, "wait_fixed": 2},
            "crawl": {"max_pages": 20, "rendering": True}
        }
        config = ApiConfig(**data)
        self.assertIsInstance(config.rate_limits, RateLimitConfig)
        self.assertEqual(config.rate_limits.requests_per_minute, 10)
        self.assertIsInstance(config.retry, RetryConfig)
        self.assertEqual(config.retry.max_retries, 5)
        self.assertIsInstance(config.crawl, CrawlConfig)
        self.assertEqual(config.crawl.max_pages, 20)
        self.assertTrue(config.crawl.rendering)


class TestServerRegistry(unittest.TestCase):
    """Test server registry functionality."""
    
    MOCK_REGISTRY_PATH = "test_registry.json"

    def setUp(self):
        if os.path.exists(self.MOCK_REGISTRY_PATH):
            os.remove(self.MOCK_REGISTRY_PATH)

    def tearDown(self):
        if os.path.exists(self.MOCK_REGISTRY_PATH):
            os.remove(self.MOCK_REGISTRY_PATH)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_init_creates_file_if_not_exists(self, mock_makedirs, mock_path_exists, mock_file):
        mock_path_exists.side_effect = [True, False]  # Dir exists, file doesn't
        registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
        
        # Ensure file was "created" (opened for writing with empty dict)
        mock_file.assert_called_once_with(self.MOCK_REGISTRY_PATH, "w")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_list_servers(self, mock_path_exists, mock_file):
        """Test listing registered servers."""
        mock_path_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "api1": {"name": "api1", "config_path": "/path/to/api1.json"},
            "api2": {"name": "api2", "config_path": "/path/to/api2.json"}
        })
        
        registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
        servers = registry.list_servers()
        
        self.assertEqual(len(servers), 2)
        # list_servers returns list of server config dicts, not just names
        server_names = [server["name"] for server in servers]
        self.assertIn("api1", server_names)
        self.assertIn("api2", server_names)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_get_server(self, mock_path_exists, mock_file):
        """Test retrieving specific server configuration."""
        mock_file.return_value.read.return_value = json.dumps({
            "test_api": {"config_path": "/path/to/test.json", "db_directory": "/data/test"}
        })
        
        registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
        server_info = registry.get_server("test_api")
        
        self.assertIsNotNone(server_info)
        self.assertEqual(server_info["config_path"], "/path/to/test.json")

    @patch("os.path.exists", return_value=True)
    def test_delete_server(self, mock_path_exists):
        initial_data = {"Server1": {"name": "Server1"}, "Server2": {"name": "Server2"}}
        initial_json = json.dumps(initial_data)
        expected_data_after_delete = {"Server2": {"name": "Server2"}}
        final_json_after_delete = json.dumps(expected_data_after_delete, indent=2)
        
        m = mock_open()
        with patch("builtins.open", m):
            # Simulate file content for ServerRegistry._load_registry
            # First call to _load_registry (in __init__)
            m.return_value.read.return_value = initial_json 
            registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
            
            # delete_server calls _load_registry again before modifying (or uses in-memory)
            # Ensure the mock read is set up correctly if it re-reads.
            # If ServerRegistry.delete_server loads from self.servers (already loaded in __init__),
            # this second read setup might not be strictly necessary but is safe.
            m.return_value.read.return_value = initial_json
            deleted = registry.delete_server("Server1")
            self.assertTrue(deleted)
            
            # Verify the write call content
            # If _save_registry uses json.dump(obj, f, indent=2), it performs multiple writes.
            # We need to capture all data written.
            write_handle = m() # This is the mock file handle
            self.assertGreater(write_handle.write.call_count, 0, "File write was not called.")
            
            # Concatenate all arguments from all calls to write_handle.write
            written_content = "".join(call_args[0][0] for call_args in write_handle.write.call_args_list)
            self.assertEqual(written_content, final_json_after_delete)

            # Reset mock read for the next operation and clear write call list for this handle for subsequent checks
            write_call_count_before_non_existent = write_handle.write.call_count
            write_handle.reset_mock() # Clears call_args_list for write_handle.write

            # For deleting a non-existent server, ensure _load_registry reflects the state after deletion
            # (or that it loads from the current self.servers)
            current_registry_state_after_delete = json.dumps(expected_data_after_delete)
            m.return_value.read.return_value = current_registry_state_after_delete
            
            not_deleted = registry.delete_server("NotFound")
            self.assertFalse(not_deleted)
            # Ensure write wasn't called again if not_deleted
            # write_handle.write.assert_not_called() would be better if we are sure no writes should happen.
            # If the previous reset_mock() is effective, call_count here would be 0.
            self.assertEqual(write_handle.write.call_count, 0, "Write was called when deleting a non-existent server.")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_get_all_config_paths(self, mock_path_exists, mock_file):
        registry_data = {
            "Server1": {"config_path": "path1"},
            "Server2": {"config_path": "path2"},
        }
        mock_file.return_value.read.return_value = json.dumps(registry_data)
        registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
        paths = registry.get_all_config_paths()
        self.assertEqual(len(paths), 2)
        self.assertIn("path1", paths)
        self.assertIn("path2", paths)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_get_db_directory(self, mock_path_exists, mock_file):
        registry_data = {"Server1": {"db_directory": "db_path_1"}}
        mock_file.return_value.read.return_value = json.dumps(registry_data)
        registry = ServerRegistry(registry_path=self.MOCK_REGISTRY_PATH)
        
        db_dir = registry.get_db_directory("Server1")
        self.assertEqual(db_dir, "db_path_1")

        db_dir_none = registry.get_db_directory("NotFound")
        self.assertIsNone(db_dir_none)


if __name__ == "__main__":
    unittest.main() 