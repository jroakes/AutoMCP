"""Tests for the PromptGenerator class."""

import unittest

from src.prompt.generator import PromptGenerator


class TestPromptGenerator(unittest.TestCase):
    """Test the PromptGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_name = "Test API"
        self.api_description = "Test API Description"
        self.tools = [
            {"name": "get_user", "description": "Get a user by ID"},
            {"name": "list_users", "description": "List all users"},
        ]
        self.resources = {"resource1": "Content 1", "resource2": "Content 2"}

    def test_hardcoded_prompts(self):
        """Test that the generator creates the two required hard-coded prompts."""
        # Create a generator without custom prompts
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
        )

        # Generate prompts
        prompts = generator.to_mcp_prompts()

        # Verify there are exactly three prompts (hard-coded)
        self.assertEqual(len(prompts), 3)

        # Verify the API overview prompt
        self.assertIn("api_overview", prompts)
        self.assertEqual(
            prompts["api_overview"]["name"], f"{self.api_name} API Overview"
        )
        self.assertIn(self.api_name, prompts["api_overview"]["template"])
        self.assertIn("get_user, list_users", prompts["api_overview"]["template"])

        # Verify the tool usage guide prompt is now a list of messages
        self.assertIn("tool_usage_guide", prompts)
        self.assertTrue(
            isinstance(prompts["tool_usage_guide"], list),
            "tool_usage_guide should be a list",
        )
        self.assertEqual(
            len(prompts["tool_usage_guide"]),
            2,
            "Should have user and assistant messages",
        )

        # Check the assistant message content (second item in the list)
        self.assertEqual(prompts["tool_usage_guide"][0].role, "user")
        self.assertEqual(prompts["tool_usage_guide"][1].role, "assistant")
        self.assertIn(
            "The tools available for Test API are generated",
            prompts["tool_usage_guide"][1].content,
        )
        self.assertIn("get_user, list_users", prompts["tool_usage_guide"][1].content)

        # Verify the resource usage guide prompt is now a list of messages
        self.assertIn("resource_usage_guide", prompts)
        self.assertTrue(
            isinstance(prompts["resource_usage_guide"], list),
            "resource_usage_guide should be a list",
        )
        self.assertEqual(
            len(prompts["resource_usage_guide"]),
            2,
            "Should have user and assistant messages",
        )

        # Check the assistant message content (second item in the list)
        self.assertEqual(prompts["resource_usage_guide"][0].role, "user")
        self.assertEqual(prompts["resource_usage_guide"][1].role, "assistant")
        self.assertIn(
            "Resources are searchable chunks of documentation",
            prompts["resource_usage_guide"][1].content,
        )
        self.assertIn("Total resources: 2", prompts["resource_usage_guide"][1].content)

    def test_custom_prompts(self):
        """Test that the generator correctly adds custom prompts from config."""
        # Create custom prompts
        custom_prompts = [
            {
                "name": "General Usage",
                "description": "General guidance for using this API",
                "content": "When using this API, always consider rate limits...",
            },
            {
                "name": "Authentication Help",
                "description": "Help with API authentication",
                "content": "To authenticate with this API, you need to...",
            },
        ]

        # Create a generator with custom prompts
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts,
        )

        # Generate prompts
        prompts = generator.to_mcp_prompts()

        # Verify there are 5 prompts (3 hard-coded + 2 custom)
        self.assertEqual(len(prompts), 5)

        # Verify the custom prompts
        self.assertIn("general_usage", prompts)
        self.assertEqual(prompts["general_usage"]["name"], "General Usage")
        self.assertEqual(
            prompts["general_usage"]["description"],
            "General guidance for using this API",
        )
        self.assertEqual(
            prompts["general_usage"]["template"],
            "When using this API, always consider rate limits...",
        )

        self.assertIn("authentication_help", prompts)
        self.assertEqual(prompts["authentication_help"]["name"], "Authentication Help")
        self.assertEqual(
            prompts["authentication_help"]["description"],
            "Help with API authentication",
        )
        self.assertEqual(
            prompts["authentication_help"]["template"],
            "To authenticate with this API, you need to...",
        )

    def test_custom_prompt_id_generation(self):
        """Test that the generator correctly generates IDs for custom prompts."""
        # Create custom prompts with spaces and mixed case
        custom_prompts = [
            {
                "name": "Complex Name With Spaces",
                "description": "Test prompt with complex name",
                "content": "Test content",
            },
            {
                "name": "Another Complex PROMPT",
                "description": "Another test prompt",
                "content": "More test content",
            },
        ]

        # Create a generator with custom prompts
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts,
        )

        # Generate prompts
        prompts = generator.to_mcp_prompts()

        # Verify the IDs are correctly generated
        self.assertIn("complex_name_with_spaces", prompts)
        self.assertIn("another_complex_prompt", prompts)

    def test_empty_custom_prompts(self):
        """Test that the generator handles empty custom prompts array."""
        # Create a generator with empty custom prompts list
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=[],
        )

        # Generate prompts
        prompts = generator.to_mcp_prompts()

        # Verify there are exactly three prompts (hard-coded)
        self.assertEqual(len(prompts), 3)

    def test_malformed_custom_prompts(self):
        """Test that the generator handles malformed custom prompts."""
        # Create custom prompts with missing fields
        custom_prompts = [
            {
                # Missing name
                "description": "Incomplete prompt",
                "content": "Content with missing name",
            },
            {
                "name": "Missing Description",
                # Missing description
                "content": "Content with missing description",
            },
            {
                "name": "Missing Content",
                "description": "Prompt with missing content",
                # Missing content
            },
        ]

        # Create a generator with malformed custom prompts
        generator = PromptGenerator(
            api_name=self.api_name,
            api_description=self.api_description,
            tools=self.tools,
            resources=self.resources,
            custom_prompts=custom_prompts,
        )

        # Generate prompts (should not raise exceptions)
        prompts = generator.to_mcp_prompts()

        # Verify the prompts were still created with default values where needed
        self.assertEqual(len(prompts), 6)  # 3 hard-coded + 3 custom

        # Verify the custom prompt with missing name got a default name
        self.assertIn("custom_prompt_0", prompts)

        # Verify the custom prompt with missing description got an empty description
        self.assertIn("missing_description", prompts)
        self.assertEqual(prompts["missing_description"]["description"], "")

        # Verify the custom prompt with missing content got an empty template
        self.assertIn("missing_content", prompts)
        self.assertEqual(prompts["missing_content"]["template"], "")


if __name__ == "__main__":
    unittest.main()
