"""
Test cases for prompt generator functionality.
"""

import unittest
from unittest.mock import Mock

from src.prompt.generator import PromptGenerator
from fastmcp.prompts import Prompt


class TestPromptGenerator(unittest.TestCase):
    """Test the PromptGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_name = "Test API"
        self.api_description = "A test API for testing"
        self.tools = [
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"}
        ]
        self.resources = {
            "resource1": {"uri": "resource1", "content": "Resource 1 content"},
            "resource2": {"uri": "resource2", "content": "Resource 2 content"}
        }

    def test_generate_prompts_empty_custom_prompts(self):
        """Test that no prompts are generated when custom_prompts is empty."""
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=[]
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 0)

    def test_generate_prompts_no_custom_prompts(self):
        """Test that no prompts are generated when custom_prompts is None."""
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=None
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 0)

    def test_generate_prompts_with_simple_custom_prompt(self):
        """Test generating a simple custom prompt."""
        custom_prompts = [
            {
                "name": "Simple Prompt",
                "description": "A simple test prompt",
                "content": "This is a simple prompt content"
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 1)
        
        prompt = prompts[0]
        self.assertIsInstance(prompt, Prompt)
        self.assertEqual(prompt.name, "simple_prompt")
        self.assertEqual(prompt.description, "A simple test prompt")
        self.assertEqual(len(prompt.arguments), 0)
        
        # Test the prompt function
        result = prompt.fn()
        self.assertEqual(result, "This is a simple prompt content")

    def test_generate_prompts_with_template_variables(self):
        """Test generating a prompt with template variables."""
        custom_prompts = [
            {
                "name": "Template Prompt",
                "description": "A prompt with variables",
                "content": "Hello {name}, welcome to {place}!",
                "variables": ["name", "place"]
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 1)
        
        prompt = prompts[0]
        self.assertIsInstance(prompt, Prompt)
        self.assertEqual(prompt.name, "template_prompt")
        self.assertEqual(prompt.description, "A prompt with variables")
        self.assertEqual(len(prompt.arguments), 2)
        
        # Check argument names
        arg_names = [arg.name for arg in prompt.arguments]
        self.assertIn("name", arg_names)
        self.assertIn("place", arg_names)
        
        # Test the prompt function with variables
        result = prompt.fn(name="John", place="AutoMCP")
        self.assertEqual(result, "Hello John, welcome to AutoMCP!")

    def test_generate_prompts_with_conversation_style(self):
        """Test generating a conversation-style prompt."""
        custom_prompts = [
            {
                "name": "Conversation Prompt",
                "description": "A conversation-style prompt",
                "content": [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Hello, how can you help me?"}
                ]
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 1)
        
        prompt = prompts[0]
        self.assertIsInstance(prompt, Prompt)
        self.assertEqual(prompt.name, "conversation_prompt")
        self.assertEqual(prompt.description, "A conversation-style prompt")
        self.assertEqual(len(prompt.arguments), 0)
        
        # Test the prompt function
        result = prompt.fn()
        expected_messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, how can you help me?"}
        ]
        self.assertEqual(result, expected_messages)

    def test_generate_prompts_multiple_custom_prompts(self):
        """Test generating multiple custom prompts."""
        custom_prompts = [
            {
                "name": "First Prompt",
                "description": "First test prompt",
                "content": "First prompt content"
            },
            {
                "name": "Second Prompt",
                "description": "Second test prompt",
                "content": "Welcome {user}!",
                "variables": ["user"]
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 2)
        
        # Check that both prompts are Prompt instances
        for prompt in prompts:
            self.assertIsInstance(prompt, Prompt)
        
        # Check prompt names
        prompt_names = [prompt.name for prompt in prompts]
        self.assertIn("first_prompt", prompt_names)
        self.assertIn("second_prompt", prompt_names)

    def test_generate_prompts_with_robust_handling(self):
        """Test that the prompt generator handles various edge cases robustly."""
        custom_prompts = [
            {
                "name": "Valid Prompt",
                "description": "A valid prompt",
                "content": "Valid content"
            },
            {
                "name": "Edge Case Prompt",
                "description": "A prompt with string variables (edge case)",
                "content": "Template with {t}{h}{i}{s}",
                "variables": "this"  # String instead of list - should still work by iterating chars
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        
        # Should generate both prompts since the generator is robust
        self.assertEqual(len(prompts), 2)
        prompt_names = [prompt.name for prompt in prompts]
        self.assertIn("valid_prompt", prompt_names)
        self.assertIn("edge_case_prompt", prompt_names)

    def test_to_mcp_prompts_compatibility(self):
        """Test the legacy to_mcp_prompts method."""
        custom_prompts = [
            {
                "name": "Test Prompt",
                "description": "A test prompt",
                "content": "Test content"
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts_dict = generator.to_mcp_prompts()
        self.assertIsInstance(prompts_dict, dict)
        self.assertIn("test_prompt", prompts_dict)
        self.assertIsInstance(prompts_dict["test_prompt"], Prompt)

    def test_prompt_name_normalization(self):
        """Test that prompt names are properly normalized."""
        custom_prompts = [
            {
                "name": "Test Prompt With Spaces",
                "description": "A test prompt",
                "content": "Test content"
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0].name, "test_prompt_with_spaces")

    def test_default_prompt_name_when_missing(self):
        """Test that default names are used when prompt name is missing."""
        custom_prompts = [
            {
                "description": "A test prompt without name",
                "content": "Test content"
            }
        ]
        
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts
        )
        
        prompts = generator.generate_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0].name, "custom_prompt_0")


if __name__ == "__main__":
    unittest.main() 