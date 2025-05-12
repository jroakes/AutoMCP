import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastmcp.prompts import Prompt
# Import PromptArgument from its specific module
from fastmcp.prompts.prompt import PromptArgument

from src.prompt.generator import PromptGenerator
# Import templates to verify formatting
from src.prompt.templates import (
    API_OVERVIEW_TEMPLATE,
    TOOL_USAGE_GUIDE_TEMPLATE,
    RESOURCE_USAGE_GUIDE_TEMPLATE,
)

class TestPromptGenerator(unittest.TestCase):

    def setUp(self):
        self.api_name = "Test API"
        self.api_description = "A cool test API."
        self.tools = [
            {"name": "get_user", "description": "Get user details"},
            {"name": "create_item", "description": "Create a new item"}
        ]
        self.resources = {
            "res://data/1": {"uri": "res://data/1", "description": "Resource 1"},
            "res://config": {"uri": "res://config", "description": "Config resource"}
        }
        self.custom_prompts = [
            {
                "name": "Greeting", 
                "description": "Generate a greeting",
                "content": "Hello {name}! Welcome to {api}.",
                "variables": ["name", "api"]
            },
            {
                "name": "Static Info",
                "content": "This is static info."
            },
            {
                "name": "Conversation Example",
                "description": "A sample chat",
                "content": [
                    {"role": "user", "text": "Hi"},
                    {"role": "assistant", "text": "Hello there!"}
                ]
            }
        ]
        self.generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=self.custom_prompts
        )

    def test_init(self):
        self.assertEqual(self.generator.api_name, self.api_name)
        self.assertEqual(self.generator.api_description, self.api_description)
        self.assertEqual(self.generator.tools, self.tools)
        self.assertEqual(self.generator.resources, self.resources)
        self.assertEqual(self.generator.custom_prompts, self.custom_prompts)

    def test_build_custom_prompt_template(self):
        prompt_data = {
            "name": "Template Test", 
            "description": "Test templating",
            "content": "Input: {input_val}",
            "variables": ["input_val"]
        }
        prompt = self.generator._build_custom_prompt(prompt_data, 0)
        self.assertIsInstance(prompt, Prompt)
        self.assertEqual(prompt.name, "template_test") # Lowercase and underscore
        self.assertEqual(prompt.description, "Test templating")
        self.assertEqual(len(prompt.arguments), 1)
        self.assertEqual(prompt.arguments[0].name, "input_val")
        self.assertTrue(prompt.arguments[0].required)
        # Test the generated function
        self.assertEqual(prompt.fn(input_val="world"), "Input: world")

    def test_build_custom_prompt_static(self):
        prompt_data = {
            "name": "Static Test", 
            "content": "Static content."
        }
        prompt = self.generator._build_custom_prompt(prompt_data, 1)
        self.assertEqual(prompt.name, "static_test")
        self.assertEqual(len(prompt.arguments), 0)
        self.assertEqual(prompt.fn(), "Static content.")

    def test_build_custom_prompt_conversation(self):
        messages = [
            {"role": "user", "text": "Question?"},
            {"role": "assistant", "text": "Answer!"}
        ]
        prompt_data = {
            "name": "Convo Test", 
            "content": messages
        }
        prompt = self.generator._build_custom_prompt(prompt_data, 2)
        self.assertEqual(prompt.name, "convo_test")
        self.assertEqual(len(prompt.arguments), 0)
        self.assertEqual(prompt.fn(), messages) # Function should return the list of messages

    def test_generate_prompts_standard_prompts(self):
        prompts = self.generator.generate_prompts()
        # Check standard prompts (first 3)
        self.assertGreaterEqual(len(prompts), 3)
        
        api_overview = prompts[0]
        tool_usage = prompts[1]
        resource_usage = prompts[2]

        # API Overview
        self.assertEqual(api_overview.name, "api_overview")
        expected_overview_content = API_OVERVIEW_TEMPLATE.format(
            api_name=self.api_name,
            api_description=self.api_description,
            tool_list="get_user, create_item"
        )
        self.assertEqual(api_overview.fn(), expected_overview_content)

        # Tool Usage
        self.assertEqual(tool_usage.name, "tool_usage_guide")
        expected_tool_usage_content = TOOL_USAGE_GUIDE_TEMPLATE.format(
            api_name=self.api_name,
            tool_list="get_user, create_item"
        )
        self.assertEqual(tool_usage.fn(), expected_tool_usage_content)

        # Resource Usage
        self.assertEqual(resource_usage.name, "resource_usage_guide")
        expected_resource_usage_content = RESOURCE_USAGE_GUIDE_TEMPLATE.format(
            api_name=self.api_name,
            resource_count=len(self.resources)
        )
        self.assertEqual(resource_usage.fn(), expected_resource_usage_content)

    def test_generate_prompts_custom_prompts(self):
        prompts = self.generator.generate_prompts()
        # Standard prompts + custom prompts
        self.assertEqual(len(prompts), 3 + len(self.custom_prompts))

        # Check custom prompts (index 3, 4, 5)
        greeting_prompt = prompts[3]
        static_prompt = prompts[4]
        convo_prompt = prompts[5]

        # Greeting (template)
        self.assertEqual(greeting_prompt.name, "greeting")
        self.assertEqual(len(greeting_prompt.arguments), 2)
        self.assertEqual(greeting_prompt.arguments[0].name, "name")
        self.assertEqual(greeting_prompt.fn(name="Bob", api="Test API"), "Hello Bob! Welcome to Test API.")

        # Static Info
        self.assertEqual(static_prompt.name, "static_info")
        self.assertEqual(len(static_prompt.arguments), 0)
        self.assertEqual(static_prompt.fn(), "This is static info.")
        
        # Conversation Example
        self.assertEqual(convo_prompt.name, "conversation_example")
        self.assertEqual(len(convo_prompt.arguments), 0)
        expected_messages = [
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "Hello there!"}
        ]
        self.assertEqual(convo_prompt.fn(), expected_messages)

    def test_to_mcp_prompts_legacy(self):
        prompts_dict = self.generator.to_mcp_prompts()
        prompts_list = self.generator.generate_prompts()
        
        self.assertEqual(len(prompts_dict), len(prompts_list))
        for prompt_obj in prompts_list:
            self.assertIn(prompt_obj.name, prompts_dict)
            # Compare relevant attributes, not the Prompt objects themselves
            dict_prompt = prompts_dict[prompt_obj.name]
            self.assertEqual(dict_prompt.name, prompt_obj.name)
            self.assertEqual(dict_prompt.description, prompt_obj.description)
            # Compare argument names and required status (more robust than comparing PromptArgument objects)
            self.assertEqual(
                [(arg.name, arg.required) for arg in dict_prompt.arguments],
                [(arg.name, arg.required) for arg in prompt_obj.arguments]
            )
            # Skip comparing fn() results as lambdas are different objects

if __name__ == '__main__':
    unittest.main() 