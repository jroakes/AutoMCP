"""Tests for the main module and CLI commands."""

import unittest
import sys
from argparse import Namespace
from unittest.mock import patch, MagicMock, mock_open
from src.main import (
    add_command,
    list_servers_command,
    delete_command,
    remove_command,
    serve_command,
    install_claude_command,
)

# Mock the fastmcp module and other dependencies before importing main
mock_fastmcp = MagicMock()
mock_fastmcp.server = MagicMock()
mock_fastmcp.server.server = MagicMock()
mock_fastmcp.server.server.FastMCP = MagicMock()
sys.modules["fastmcp"] = mock_fastmcp
sys.modules["fastmcp.server"] = mock_fastmcp.server
sys.modules["fastmcp.server.server"] = mock_fastmcp.server.server
sys.modules["mcp.server.lowlevel.helper_types"] = MagicMock()


class TestCliCommands(unittest.TestCase):
    """Tests for CLI commands."""

    def setUp(self):
        """Set up common test fixtures."""
        # Mock registry instance setup that can be reused across tests
        self.mock_registry_instance = MagicMock()
        self.mock_registry_instance.get_server.return_value = {
            "name": "api1",
            "config_path": "/path/to/api1.json",
            "db_directory": "/path/to/db1",
            "added_at": "2023-01-01",
        }
        self.mock_registry_instance.delete_server.return_value = True

        # Create common api_config mock
        self.api_config = MagicMock()
        self.api_config.name = "test-api"
        self.api_config.db_directory = None

    @patch("src.main.process_config")
    @patch("src.main.prepare_resource_manager")
    @patch("src.main.ServerRegistry")
    def test_add_command(self, mock_registry, mock_prepare, mock_process):
        """Test add_command with different configurations."""
        # Setup mocks
        mock_registry.return_value = self.mock_registry_instance
        mock_process.return_value = self.api_config

        test_cases = [
            {
                "name": "single_file",
                "is_dir": False,
                "config": "test.json",
                "glob_result": None,
                "expected_process_calls": 1,
            },
            {
                "name": "directory",
                "is_dir": True,
                "config": "./configs",
                "glob_result": ["api1.json", "api2.json"],
                "expected_process_calls": 2,
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Reset mock call counts
                mock_registry.reset_mock()
                mock_process.reset_mock()
                mock_prepare.reset_mock()
                self.mock_registry_instance.add_server.reset_mock()

                # Setup args
                args = Namespace(
                    config=case["config"],
                    db_directory="./test_db",
                    registry_file="./test_registry.json",
                )

                # Call command with appropriate mocks
                with patch("os.path.isdir", return_value=case["is_dir"]):
                    if case["is_dir"]:
                        with patch(
                            "src.main.glob.glob", return_value=case["glob_result"]
                        ):
                            add_command(args)
                    else:
                        add_command(args)

                # Verify calls
                mock_registry.assert_called_with("./test_registry.json")
                self.assertEqual(
                    mock_process.call_count, case["expected_process_calls"]
                )
                self.assertEqual(
                    mock_prepare.call_count, case["expected_process_calls"]
                )
                self.assertEqual(
                    self.mock_registry_instance.add_server.call_count,
                    case["expected_process_calls"],
                )

    @patch("builtins.print")
    @patch("src.main.ServerRegistry")
    def test_list_servers_command(self, mock_registry, mock_print):
        """Test list_servers_command with different server lists."""
        test_cases = [
            {
                "name": "empty_list",
                "servers": [],
                "expected_message": "No API servers registered.",
            },
            {
                "name": "with_servers",
                "servers": [
                    {
                        "name": "api1",
                        "config_path": "/path/to/api1.json",
                        "db_directory": "/path/to/db1",
                        "added_at": "2023-01-01",
                    }
                ],
                "expected_min_prints": 3,  # Header + details lines
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Reset mocks
                mock_registry.reset_mock()
                mock_print.reset_mock()

                # Setup mock registry
                mock_registry_instance = MagicMock()
                mock_registry_instance.list_servers.return_value = case["servers"]
                mock_registry.return_value = mock_registry_instance

                # Setup args
                args = Namespace(registry_file="./test_registry.json")

                # Call command
                list_servers_command(args)

                # Verify calls
                mock_registry.assert_called_with("./test_registry.json")

                if case["name"] == "empty_list":
                    mock_print.assert_called_with(case["expected_message"])
                else:
                    self.assertGreaterEqual(
                        mock_print.call_count, case["expected_min_prints"]
                    )

    @patch("shutil.rmtree")
    @patch("src.main.ServerRegistry")
    def test_server_removal_commands(self, mock_registry, mock_rmtree):
        """Test delete_command and remove_command with different options."""
        test_cases = [
            {
                "name": "delete_command_no_clean",
                "command_func": delete_command,
                "args": Namespace(
                    name="api1", clean=False, registry_file="./test_registry.json"
                ),
                "should_remove_dir": False,
            },
            {
                "name": "delete_command_with_clean",
                "command_func": delete_command,
                "args": Namespace(
                    name="api1", clean=True, registry_file="./test_registry.json"
                ),
                "should_remove_dir": True,
            },
            {
                "name": "remove_command_keep_data",
                "command_func": remove_command,
                "args": Namespace(
                    name="api1", keep_data=True, registry_file="./test_registry.json"
                ),
                "should_remove_dir": False,
            },
            {
                "name": "remove_command_remove_data",
                "command_func": remove_command,
                "args": Namespace(
                    name="api1", keep_data=False, registry_file="./test_registry.json"
                ),
                "should_remove_dir": True,
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Reset mocks
                mock_registry.reset_mock()
                mock_rmtree.reset_mock()

                # Setup mock registry
                mock_registry.return_value = self.mock_registry_instance

                # Call command with path exists check for rmtree
                with patch("os.path.exists", return_value=True):
                    case["command_func"](case["args"])

                # Verify common calls
                mock_registry.assert_called_with("./test_registry.json")
                self.mock_registry_instance.get_server.assert_called_with("api1")
                self.mock_registry_instance.delete_server.assert_called_with("api1")

                # Verify directory removal based on the case
                if case["should_remove_dir"]:
                    mock_rmtree.assert_called_with("/path/to/db1")
                else:
                    mock_rmtree.assert_not_called()

    @patch("src.main.start_mcp_server")
    @patch("src.main.ServerRegistry")
    def test_serve_command(self, mock_registry, mock_start_server):
        """Test serve_command with different configurations."""
        test_cases = [
            {
                "name": "from_registry",
                "config": None,
                "is_dir": False,
                "glob_result": None,
                "registry_paths": ["/path/to/api1.json", "/path/to/api2.json"],
                "expected_paths": ["/path/to/api1.json", "/path/to/api2.json"],
            },
            {
                "name": "from_single_file",
                "config": "test.json",
                "is_dir": False,
                "glob_result": None,
                "registry_paths": [],
                "expected_paths": ["test.json"],
            },
            {
                "name": "from_directory",
                "config": "./configs",
                "is_dir": True,
                "glob_result": ["api1.json", "api2.json"],
                "registry_paths": [],
                "expected_paths": ["api1.json", "api2.json"],
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Reset mocks
                mock_registry.reset_mock()
                mock_start_server.reset_mock()

                # Setup mock registry
                mock_registry_instance = MagicMock()
                mock_registry_instance.get_all_config_paths.return_value = case[
                    "registry_paths"
                ]
                mock_registry.return_value = mock_registry_instance

                # Setup args
                args = Namespace(
                    config=case["config"],
                    host="localhost",
                    port=8080,
                    debug=True,
                    db_directory="./test_db",
                    registry_file="./test_registry.json",
                )

                # Call command with appropriate mocks
                with patch("os.path.isdir", return_value=case["is_dir"]):
                    if case["is_dir"] and case["config"]:
                        with patch(
                            "src.main.glob.glob", return_value=case["glob_result"]
                        ):
                            serve_command(args)
                    else:
                        serve_command(args)

                # Verify calls
                mock_registry.assert_called_with("./test_registry.json")

                if case["config"] is None:
                    mock_registry_instance.get_all_config_paths.assert_called_once()

                mock_start_server.assert_called_with(
                    config_paths=case["expected_paths"],
                    host="localhost",
                    port=8080,
                    debug=True,
                    db_directory="./test_db",
                )

    @patch("src.main.json.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.main.ServerRegistry")
    def test_install_claude_command(self, mock_registry, mock_file, mock_dump):
        """Test install_claude_command."""
        # Setup mocks
        mock_registry_instance = MagicMock()
        mock_registry_instance.get_all_config_paths.return_value = [
            "/path/to/api1.json",
            "/path/to/api2.json",
        ]
        mock_registry.return_value = mock_registry_instance

        # Setup args
        args = Namespace(
            config=None,
            host="localhost",
            port=8080,
            output="./.claude.json",
            registry_file="./test_registry.json",
        )

        # Call command
        install_claude_command(args)

        # Verify calls
        mock_registry.assert_called_with("./test_registry.json")
        mock_registry_instance.get_all_config_paths.assert_called_once()
        mock_file.assert_called_with("./.claude.json", "w")
        mock_dump.assert_called_once()

        # Check the structure of the Claude config
        tools_arg = mock_dump.call_args[0][0]
        self.assertIn("tools", tools_arg)
        self.assertEqual(len(tools_arg["tools"]), 2)


if __name__ == "__main__":
    unittest.main()
