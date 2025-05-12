import unittest
from unittest.mock import patch, MagicMock, mock_open, ANY, call
import json
import os
import sys
import tempfile
from fastmcp.prompts import Prompt

# Add patch for dotenv.load_dotenv at the top level
patch("dotenv.load_dotenv", return_value=True).start()

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.manager import (
    process_config,
    prepare_resource_manager,
    create_mcp_config,
    start_mcp_server,
    generate_prompts,
    DEFAULT_DB_DIRECTORY,
    DEFAULT_EMBEDDING_TYPE,
    DEFAULT_EMBEDDING_MODEL,
)
from src.utils import ApiConfig
from src.models import MCPToolsetConfig
from src.documentation.resources import ResourceManager
from src.openapi.tools import OpenAPIToolkit
from src.openapi.models import RateLimitConfig, RetryConfig


class TestProcessConfig(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.manager.load_spec_from_url")
    def test_process_config_basic(self, mock_load_spec, mock_file_open):
        config_data = {
            "name": "Test API",
            "server_name": "test_api_server",
            "description": "A test API.",
            "openapi_spec_url": "http://example.com/openapi.json",
            "documentation_url": "http://example.com/docs",
        }
        mock_file_open.return_value.read.return_value = json.dumps(config_data)
        mock_load_spec.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}

        api_config = process_config("dummy_path.json")

        self.assertEqual(api_config.name, "Test API")
        # The server_name transformation from "test_api_server" to "test_api" is intended
        # process_config normalizes server names by removing '_server' suffix for compatibility
        self.assertEqual(api_config.server_name, "test_api")
        self.assertEqual(api_config.openapi_spec_url, "http://example.com/openapi.json")
        self.assertIsNotNone(api_config.openapi_spec)
        mock_load_spec.assert_called_once_with("http://example.com/openapi.json")

    @patch("builtins.open", new_callable=mock_open)
    @patch.dict(os.environ, {"TEST_API_KEY": "secretkey123"})
    def test_process_config_with_env_vars(self, mock_file_open):
        config_data = {
            "name": "Test Auth API",
            "server_name": "test_auth_api",
            "description": "An API with auth.",
            "openapi_spec_url": "http://example.com/auth_openapi.json",
            "documentation_url": "http://example.com/auth_docs",
            "authentication": {
                "type": "bearer",
                "value": "Bearer {TEST_API_KEY}",
            },
        }
        mock_file_open.return_value.read.return_value = json.dumps(config_data)
        
        # We don't need to load spec for this test
        with patch("src.manager.load_spec_from_url", return_value=None):
             api_config = process_config("dummy_auth_path.json")

        self.assertEqual(api_config.authentication.value, "Bearer secretkey123")

    @patch("builtins.open", new_callable=mock_open)
    @patch.dict(os.environ, {"TEST_USER": "user", "TEST_PASS": "pass"})
    def test_process_config_basic_auth_env_vars(self, mock_file_open):
        config_data = {
            "name": "Test Basic Auth API",
            "server_name": "test_basic_auth_api",
            "description": "An API with basic auth.",
            "openapi_spec_url": "http://example.com/basic_auth_openapi.json",
            "documentation_url": "http://example.com/basic_auth_docs",
            "authentication": {
                "type": "basic",
                "username": "{TEST_USER}",
                "password": "{TEST_PASS}",
            },
        }
        mock_file_open.return_value.read.return_value = json.dumps(config_data)
        with patch("src.manager.load_spec_from_url", return_value=None):
            api_config = process_config("dummy_basic_auth_path.json")

        self.assertEqual(api_config.authentication.username, "user")
        self.assertEqual(api_config.authentication.password, "pass")


class TestPrepareResourceManager(unittest.TestCase):

    def test_skip_if_no_documentation_url(self):
        api_config = ApiConfig(
            name="No Docs API",
            server_name="no_docs_api",
            description="API without documentation URL.",
            openapi_spec_url="http://nodoc.com/spec.json",
            documentation_url=None, # No docs URL
        )
        rm = prepare_resource_manager(api_config, "dummy_db_dir")
        self.assertIsNone(rm)

    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_crawl_if_db_empty(self, MockDocumentationCrawler, MockResourceManager):
        api_config = ApiConfig(
            name="Crawl API",
            server_name="crawl_api",
            description="API that needs crawling.",
            openapi_spec_url="http://crawl.com/spec.json",
            documentation_url="http://crawl.com/docs",
            crawl={"max_pages": 10, "rendering": True}
        )
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.is_empty.return_value = True # DB is empty

        db_dir = os.path.join(DEFAULT_DB_DIRECTORY, "crawl_api")
        rm = prepare_resource_manager(api_config, db_dir)

        MockResourceManager.assert_called_once_with(
            db_directory=db_dir,
            embedding_type=DEFAULT_EMBEDDING_TYPE,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name="crawl_api",
        )
        mock_rm_instance.is_empty.assert_called_once()
        MockDocumentationCrawler.assert_called_once()
        mock_crawler_instance = MockDocumentationCrawler.return_value
        mock_crawler_instance.crawl.assert_called_once()
        
        # Check that crawl parameters are passed correctly
        _, kwargs = MockDocumentationCrawler.call_args
        self.assertEqual(kwargs['max_pages'], 10)
        self.assertTrue(kwargs['rendering'])


    @patch("src.manager.ResourceManager")
    @patch("src.manager.DocumentationCrawler")
    def test_skip_crawl_if_db_not_empty(
        self, MockDocumentationCrawler, MockResourceManager
    ):
        api_config = ApiConfig(
            name="No Crawl API",
            server_name="no_crawl_api",
            description="API that doesn't need crawling.",
            openapi_spec_url="http://nocrawl.com/spec.json",
            documentation_url="http://nocrawl.com/docs",
        )
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.is_empty.return_value = False # DB is NOT empty

        db_dir = os.path.join(DEFAULT_DB_DIRECTORY, "no_crawl_api")
        rm = prepare_resource_manager(api_config, db_dir)

        MockResourceManager.assert_called_once_with(
            db_directory=db_dir,
            embedding_type=DEFAULT_EMBEDDING_TYPE,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name="no_crawl_api",
        )
        mock_rm_instance.is_empty.assert_called_once()
        MockDocumentationCrawler.assert_not_called()


class TestGeneratePrompts(unittest.TestCase):
    @patch("src.manager.PromptGenerator")
    def test_generate_prompts_basic(self, MockPromptGenerator):
        api_config = ApiConfig(
            name="Prompt API",
            server_name="prompt_api",
            description="API for testing prompts.",
            openapi_spec_url="http://prompt.com/spec.json",
            documentation_url="http://prompt.com/docs",
            prompts=[{"name": "custom_prompt", "template": "Test template"}],
        )
        mock_tools = [{"name": "tool1", "description": "A test tool"}]
        
        mock_rm = MagicMock(spec=ResourceManager)
        mock_rm.list_resources.return_value = [
            {"uri": "res://data", "description": "A resource"}
        ]
        
        expected_prompts_list = [MagicMock()] # e.g. [Prompt(...)]
        mock_generator_instance = MockPromptGenerator.return_value
        mock_generator_instance.generate_prompts.return_value = expected_prompts_list

        prompts = generate_prompts(api_config, mock_tools, mock_rm)

        MockPromptGenerator.assert_called_once_with(
            api_name="Prompt API",
            api_description="API for testing prompts.",
            tools=mock_tools,
            resources={"res://data": {"uri": "res://data", "description": "A resource"}},
            custom_prompts=[{"name": "custom_prompt", "template": "Test template"}],
        )
        mock_generator_instance.generate_prompts.assert_called_once()
        self.assertEqual(prompts, expected_prompts_list)

    @patch("src.manager.PromptGenerator")
    def test_generate_prompts_no_resource_manager(self, MockPromptGenerator):
        api_config = ApiConfig(
            name="No RM Prompt API",
            server_name="no_rm_prompt_api",
            description="API for testing prompts without RM.",
            openapi_spec_url="http://norrmprompt.com/spec.json",
            documentation_url=None, # No RM
        )
        mock_tools = [{"name": "tool2", "description": "Another test tool"}]
        
        expected_prompts_list = [MagicMock()]
        mock_generator_instance = MockPromptGenerator.return_value
        mock_generator_instance.generate_prompts.return_value = expected_prompts_list

        prompts = generate_prompts(api_config, mock_tools, None) # No ResourceManager

        MockPromptGenerator.assert_called_once_with(
            api_name="No RM Prompt API",
            api_description="API for testing prompts without RM.",
            tools=mock_tools,
            resources={}, # Empty resources
            custom_prompts=None, # No custom prompts in this config
        )
        mock_generator_instance.generate_prompts.assert_called_once()
        self.assertEqual(prompts, expected_prompts_list)


class TestCreateMcpConfig(unittest.TestCase):

    @patch("src.manager.OpenAPIToolkit")
    @patch("src.manager.generate_prompts")
    def test_create_mcp_config_flow(self, mock_generate_prompts, MockOpenAPIToolkit):
        api_config = ApiConfig(
            name="MCP Config API",
            server_name="mcp_config_api",
            description="API for MCP config testing.",
            openapi_spec={"openapi": "3.0.1"},
            openapi_spec_url="http://mcpconfig.com/spec.json",
            documentation_url="http://mcpconfig.com/docs",
            authentication={"type": "none"},
            rate_limits=RateLimitConfig(),
            retry=RetryConfig(),
        )
        mock_rm = MagicMock(spec=ResourceManager)
        
        mock_toolkit_instance = MockOpenAPIToolkit.return_value
        mock_toolkit_instance.__class__ = OpenAPIToolkit
        mock_tool_schemas = [{"name": "openapi_tool"}]
        mock_toolkit_instance.get_tool_schemas.return_value = mock_tool_schemas
        
        mock_prompt_instance = MagicMock(spec=Prompt)
        mock_prompt_instance.__class__ = Prompt
        mock_generated_prompts = [mock_prompt_instance]
        mock_generate_prompts.return_value = mock_generated_prompts

        mcp_toolset_config = create_mcp_config(api_config, mock_rm)

        MockOpenAPIToolkit.assert_called_once_with(
            api_config.openapi_spec,
            auth_config=api_config.authentication,
            rate_limit_config=api_config.rate_limits,
            retry_config=api_config.retry,
        )
        mock_generate_prompts.assert_called_once_with(
            api_config, mock_tool_schemas, mock_rm
        )
        
        self.assertIsInstance(mcp_toolset_config, MCPToolsetConfig)
        self.assertEqual(mcp_toolset_config.name, "MCP Config API")
        self.assertEqual(mcp_toolset_config.api_description, "API for MCP config testing.")
        self.assertEqual(mcp_toolset_config.openapi_spec, {"openapi": "3.0.1"})
        self.assertTrue(isinstance(mcp_toolset_config.toolkit, OpenAPIToolkit))
        self.assertEqual(mcp_toolset_config.resource_manager, mock_rm)
        self.assertTrue(all(isinstance(p, Prompt) for p in mcp_toolset_config.prompts))
        self.assertEqual(len(mcp_toolset_config.prompts), 1)


class TestStartMcpServer(unittest.TestCase):

    @patch("uvicorn.run")
    @patch("fastapi.FastAPI")
    @patch("src.manager.process_config")
    @patch("src.manager.create_mcp_config")
    @patch("src.manager.MCPServer")
    @patch("src.manager.ResourceManager")
    @patch("src.manager.ServerRegistry") # Mock ServerRegistry
    def test_start_mcp_server_single_config(
        self,
        MockServerRegistry,
        MockResourceManager,
        MockMCPServer,
        mock_create_mcp_config,
        mock_process_config,
        MockFastAPI,
        mock_uvicorn_run,
    ):
        # --- Mock ApiConfig ---
        mock_api_config = MagicMock(spec=ApiConfig)
        mock_api_config.name = "TestServer1"
        mock_api_config.server_name = "testserver1" # Ensure this is set
        mock_api_config.documentation_url = "http://doc.test" # Needed for RM check
        mock_process_config.return_value = mock_api_config

        # --- Mock ResourceManager ---
        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.exists.return_value = True # DB exists

        # --- Mock MCPToolsetConfig ---
        mock_mcp_toolset_config = MagicMock(spec=MCPToolsetConfig)
        mock_create_mcp_config.return_value = mock_mcp_toolset_config

        # --- Mock MCPServer and its FastMCP instance ---
        mock_mcp_server_instance = MockMCPServer.return_value
        mock_fast_mcp_app = MagicMock() # This will be the FastAPI sub-app
        mock_mcp_server_instance.mcp.sse_app.return_value = mock_fast_mcp_app

        # --- Mock FastAPI app ---
        mock_fastapi_app_instance = MockFastAPI.return_value
        
        # --- Mock ServerRegistry ---
        mock_registry_instance = MockServerRegistry.return_value
        mock_registry_instance.get_db_directory.return_value = "/fake/db/dir/testserver1"


        config_paths = ["config1.json"]
        start_mcp_server(config_paths, host="127.0.0.1", port=8001, debug=True)

        MockFastAPI.assert_called_once_with(
            title="AutoMCP Server", description="MCP server for multiple APIs"
        )
        mock_process_config.assert_called_once_with("config1.json")
        
        # Verify ResourceManager was instantiated for the server
        db_dir_for_server1 = "/fake/db/dir/testserver1"
        MockResourceManager.assert_called_once_with(
            db_directory=db_dir_for_server1,
            embedding_type=DEFAULT_EMBEDDING_TYPE,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name="testserver1",
        )
        mock_rm_instance.exists.assert_called_once()

        mock_create_mcp_config.assert_called_once_with(
            mock_api_config, mock_rm_instance
        )
        MockMCPServer.assert_called_once_with(
            mcp_config=mock_mcp_toolset_config,
            host="127.0.0.1",
            port=8001,
            debug=True,
            db_directory=db_dir_for_server1,
        )
        # Check that the sub-application was mounted
        mock_fastapi_app_instance.mount.assert_called_once_with(
            "/testserver1/mcp", mock_fast_mcp_app
        )
        mock_uvicorn_run.assert_called_once()
        self.assertEqual(mock_uvicorn_run.call_args[0][0], mock_fastapi_app_instance)
        self.assertEqual(mock_uvicorn_run.call_args[1]['host'], "127.0.0.1")
        self.assertEqual(mock_uvicorn_run.call_args[1]['port'], 8001)

    @patch("uvicorn.run")
    @patch("fastapi.FastAPI")
    @patch("src.manager.process_config")
    @patch("src.manager.ResourceManager")
    @patch("src.manager.ServerRegistry")
    @patch("src.manager.logger")
    @patch("src.manager.create_mcp_config")
    @patch("src.manager.MCPServer")
    def test_start_mcp_server_db_not_exist(
        self,
        mock_mcp_server,
        mock_create_mcp_config,
        mock_logger,
        MockServerRegistry,
        MockResourceManager,
        mock_process_config,
        MockFastAPI,
        mock_uvicorn_run
    ):
        mock_api_config = MagicMock(spec=ApiConfig)
        mock_api_config.name = "NoDBServer"
        mock_api_config.server_name = "nodbserver"
        mock_process_config.return_value = mock_api_config

        mock_rm_instance = MockResourceManager.return_value
        mock_rm_instance.exists.return_value = False # DB does NOT exist
        
        mock_registry_instance = MockServerRegistry.return_value
        mock_registry_instance.get_db_directory.return_value = "/fake/db/dir/nodbserver"

        config_paths = ["nodb_config.json"]
        start_mcp_server(config_paths)

        mock_process_config.assert_called_once_with("nodb_config.json")
        # Ensure ResourceManager was checked
        db_dir_for_nodb = "/fake/db/dir/nodbserver"
        MockResourceManager.assert_called_once_with(
            db_directory=db_dir_for_nodb,
            embedding_type=DEFAULT_EMBEDDING_TYPE,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            server_name="nodbserver",
        )
        mock_rm_instance.exists.assert_called_once()
        
        # Assert that a warning was logged
        mock_logger.warning.assert_any_call(
            "No crawled documentation found for nodbserver. Run 'automcp add' first."
        )
        
        # Assert that MCPServer and create_mcp_config were NOT called using direct assertions
        mock_create_mcp_config.assert_not_called()
        mock_mcp_server.assert_not_called()
        
        # Server still starts with empty configuration when no APIs can be mounted
        mock_uvicorn_run.assert_called_once()


if __name__ == "__main__":
    unittest.main() 