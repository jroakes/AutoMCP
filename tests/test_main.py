import unittest
from unittest.mock import patch, MagicMock
import argparse
import os
import sys

# Add the project root to the Python path
# This allows us to import modules from the 'src' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.main import main
from src.constants import DEFAULT_REGISTRY_FILE, DEFAULT_HOST, DEFAULT_PORT

class TestMainCLI(unittest.TestCase):

    @patch('src.main.add_command')
    def test_add_command_single_file(self, mock_add_command):
        """Test the 'add' command with a single config file."""
        test_args = ['add', '--config', 'dummy_config.json']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_add_command.assert_called_once()
        called_args = mock_add_command.call_args[0][0]
        self.assertEqual(called_args.config, 'dummy_config.json')
        self.assertEqual(called_args.registry_file, DEFAULT_REGISTRY_FILE)

    @patch('src.main.add_command')
    def test_add_command_directory(self, mock_add_command):
        """Test the 'add' command with a directory."""
        test_args = ['add', '--config', 'dummy_config_dir/']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_add_command.assert_called_once()
        called_args = mock_add_command.call_args[0][0]
        self.assertEqual(called_args.config, 'dummy_config_dir/')

    @patch('src.main.list_servers_command')
    def test_list_servers_command(self, mock_list_servers_command):
        """Test the 'list-servers' command."""
        test_args = ['list-servers']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_list_servers_command.assert_called_once()
        called_args = mock_list_servers_command.call_args[0][0]
        self.assertEqual(called_args.registry_file, DEFAULT_REGISTRY_FILE)

    @patch('src.main.remove_command')
    def test_remove_command(self, mock_remove_command):
        """Test the 'remove' command."""
        test_args = ['remove', '--name', 'test_server']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_remove_command.assert_called_once()
        called_args = mock_remove_command.call_args[0][0]
        self.assertEqual(called_args.name, 'test_server')
        self.assertFalse(called_args.keep_data)
        self.assertEqual(called_args.registry_file, DEFAULT_REGISTRY_FILE)

    @patch('src.main.remove_command')
    def test_remove_command_keep_data(self, mock_remove_command):
        """Test the 'remove' command with --keep-data."""
        test_args = ['remove', '--name', 'test_server', '--keep-data']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_remove_command.assert_called_once()
        called_args = mock_remove_command.call_args[0][0]
        self.assertEqual(called_args.name, 'test_server')
        self.assertTrue(called_args.keep_data)

    @patch('src.main.delete_command') # Testing legacy delete
    def test_delete_command_legacy(self, mock_delete_command):
        """Test the legacy 'delete' command."""
        test_args = ['delete', '--name', 'test_server_del']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_delete_command.assert_called_once()
        called_args = mock_delete_command.call_args[0][0]
        self.assertEqual(called_args.name, 'test_server_del')
        self.assertFalse(called_args.clean)

    @patch('src.main.serve_command')
    def test_serve_command_no_config(self, mock_serve_command):
        """Test the 'serve' command without a specific config (uses registry)."""
        test_args = ['serve']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_serve_command.assert_called_once()
        called_args = mock_serve_command.call_args[0][0]
        self.assertIsNone(called_args.config)
        self.assertEqual(called_args.host, DEFAULT_HOST)
        self.assertEqual(called_args.port, DEFAULT_PORT)
        self.assertFalse(called_args.debug)
        self.assertEqual(called_args.registry_file, DEFAULT_REGISTRY_FILE)

    @patch('src.main.serve_command')
    def test_serve_command_with_config_file(self, mock_serve_command):
        """Test the 'serve' command with a specific config file."""
        test_args = ['serve', '--config', 'my_api.json', '--host', '127.0.0.1', '--port', '9000', '--debug']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_serve_command.assert_called_once()
        called_args = mock_serve_command.call_args[0][0]
        self.assertEqual(called_args.config, 'my_api.json')
        self.assertEqual(called_args.host, '127.0.0.1')
        self.assertEqual(called_args.port, 9000)
        self.assertTrue(called_args.debug)

    @patch('src.main.install_claude_command')
    def test_install_claude_command_default(self, mock_install_claude_command):
        """Test the 'install claude' command with default options."""
        test_args = ['install', 'claude']
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_install_claude_command.assert_called_once()
        called_args = mock_install_claude_command.call_args[0][0]
        self.assertIsNone(called_args.config)
        self.assertEqual(called_args.host, 'localhost') # Default in main.py for claude install
        self.assertEqual(called_args.port, DEFAULT_PORT)
        self.assertEqual(called_args.output, '.claude.json')
        self.assertEqual(called_args.registry_file, DEFAULT_REGISTRY_FILE)

    @patch('src.main.install_claude_command')
    def test_install_claude_command_custom(self, mock_install_claude_command):
        """Test the 'install claude' command with custom options."""
        test_args = [
            'install', 'claude',
            '--config', 'claude_config.json',
            '--host', '0.0.0.0',
            '--port', '9999',
            '--output', 'custom_claude.json',
            '--registry-file', 'custom_registry.json'
        ]
        with patch('sys.argv', ['automcp'] + test_args):
            main()
        mock_install_claude_command.assert_called_once()
        called_args = mock_install_claude_command.call_args[0][0]
        self.assertEqual(called_args.config, 'claude_config.json')
        self.assertEqual(called_args.host, '0.0.0.0')
        self.assertEqual(called_args.port, 9999)
        self.assertEqual(called_args.output, 'custom_claude.json')
        self.assertEqual(called_args.registry_file, 'custom_registry.json')

    @patch('argparse.ArgumentParser.print_help')
    def test_main_no_command(self, mock_print_help):
        """Test calling main without any command."""
        with patch('sys.argv', ['automcp']):
            main()
        mock_print_help.assert_called_once()


if __name__ == '__main__':
    unittest.main() 