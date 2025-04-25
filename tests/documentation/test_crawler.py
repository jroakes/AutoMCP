"""Tests for the DocumentationCrawler class in the documentation module."""

import asyncio
import unittest
import sys
from unittest.mock import patch, MagicMock


# Set up mocks for modules that might not exist in the test environment
# Create async-compatible mocks
class AsyncMagicMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMagicMock, self).__call__(*args, **kwargs)

    def __await__(self):
        return self().__await__()


# Mock the fastmcp module and other dependencies before importing crawler
mock_fastmcp = MagicMock()
mock_fastmcp.server = MagicMock()
mock_fastmcp.server.server = MagicMock()
mock_fastmcp.server.server.FastMCP = AsyncMagicMock
sys.modules["fastmcp"] = mock_fastmcp
sys.modules["fastmcp.server"] = mock_fastmcp.server
sys.modules["fastmcp.server.server"] = mock_fastmcp.server.server
sys.modules["mcp.server.lowlevel.helper_types"] = MagicMock()

# Now try importing the crawler modules
try:
    from src.documentation.crawler import DocumentationCrawler
    from src.documentation.resources import (
        ResourceManager,
        DocumentationResource,
    )

    SKIP_TESTS = False
    SKIP_REASON = None
except ImportError as e:
    print(f"DEBUG - Import error in test_crawler.py: {e}")
    import traceback

    traceback.print_exc()
    SKIP_TESTS = True
    SKIP_REASON = f"Failed to import required modules: {str(e)}"


@unittest.skipIf(SKIP_TESTS, SKIP_REASON)
class TestDocumentationCrawler(unittest.TestCase):
    """Tests for the DocumentationCrawler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mocks
        self.mock_resource_manager = MagicMock(spec=ResourceManager)

        # Set up normalize_url mock return value
        self.mock_resource_manager.normalize_url.return_value = (
            "https://example.com/docs"
        )

        # Initialize crawler
        self.crawler = DocumentationCrawler(
            base_url="https://example.com/docs",
            resource_manager=self.mock_resource_manager,
            max_pages=2,
            max_depth=1,
            rendering=False,
        )

    def test_init(self):
        """Test crawler initialization."""
        # Check if attributes are properly set
        self.assertEqual(self.crawler.base_url, "https://example.com/docs")
        self.assertEqual(self.crawler.resource_manager, self.mock_resource_manager)
        self.assertEqual(self.crawler.max_pages, 2)
        self.assertEqual(self.crawler.max_depth, 1)
        self.assertEqual(self.crawler.base_domain, "example.com")
        self.assertFalse(self.crawler.rendering)  # Default should be False

        # Test with rendering enabled
        crawler = DocumentationCrawler(
            base_url="https://example.com/docs",
            resource_manager=self.mock_resource_manager,
            rendering=True,
        )
        self.assertTrue(crawler.rendering)

    def test_create_markdown_generator(self):
        """Test the creation of markdown generator."""
        # Create a markdown generator
        markdown_generator = self.crawler.create_markdown_generator()

        # Test that options are set correctly
        options = markdown_generator.options
        self.assertFalse(options.get("ignore_links"))
        self.assertEqual(options.get("body_width"), 0)
        self.assertTrue(options.get("escape_html"))
        self.assertTrue(options.get("skip_internal_links"))
        self.assertTrue(options.get("include_sup_sub"))
        self.assertTrue(options.get("citations"))

    def test_create_browser_config(self):
        """Test the creation of browser configuration."""
        # Test with rendering disabled (default)
        browser_config = self.crawler.create_browser_config()

        # Test that config is set correctly
        self.assertTrue(browser_config.headless)
        self.assertEqual(browser_config.user_agent, self.crawler.user_agent)
        self.assertEqual(browser_config.viewport_width, 1280)
        self.assertEqual(browser_config.viewport_height, 800)
        self.assertTrue(browser_config.ignore_https_errors)
        self.assertFalse(
            browser_config.java_script_enabled
        )  # JS should be disabled by default

        # Test with rendering enabled
        self.crawler.rendering = True
        browser_config = self.crawler.create_browser_config()
        self.assertTrue(
            browser_config.java_script_enabled
        )  # JS should be enabled when rendering is True

    def test_create_crawler_config(self):
        """Test the creation of crawler configuration."""
        # Mock markdown generator
        mock_md_generator = MagicMock()

        # Test with rendering disabled (default)
        self.crawler.rendering = False
        crawler_config = self.crawler.create_crawler_config(
            markdown_generator=mock_md_generator, excluded_tags=["test"]
        )

        # Test that config is set correctly
        self.assertEqual(crawler_config.markdown_generator, mock_md_generator)
        self.assertEqual(crawler_config.excluded_tags, ["test"])
        self.assertEqual(
            crawler_config.wait_until, "domcontentloaded"
        )  # Should use domcontentloaded when rendering is False

        # Test with rendering enabled
        self.crawler.rendering = True
        crawler_config = self.crawler.create_crawler_config(
            markdown_generator=mock_md_generator, excluded_tags=["test"]
        )
        self.assertEqual(
            crawler_config.wait_until, "networkidle"
        )  # Should use networkidle when rendering is True

        # Test default tags when remove_nav_elements is True
        self.crawler.remove_nav_elements = True
        config = self.crawler.create_crawler_config()
        self.assertIn("nav", config.excluded_tags)
        self.assertIn("header", config.excluded_tags)
        self.assertIn("footer", config.excluded_tags)

        # Test default tags when remove_nav_elements is False
        self.crawler.remove_nav_elements = False
        config = self.crawler.create_crawler_config()
        self.assertNotIn("nav", config.excluded_tags)
        self.assertNotIn("header", config.excluded_tags)
        self.assertNotIn("footer", config.excluded_tags)

    def test_chunk_markdown_no_text(self):
        """Test chunking with empty text."""
        chunks = self.crawler.chunk_markdown("", "https://example.com/docs", "Test")
        self.assertEqual(chunks, [])

    def test_chunk_markdown(self):
        """Test chunking markdown content."""
        # Mock resource manager normalize_url
        self.mock_resource_manager.normalize_url.return_value = (
            "https://example.com/test"
        )

        # Call method with test content
        test_content = "# Test Document\n\nThis is a test document.\n\n## Section 1\n\nContent in section 1.\n\n## Section 2\n\nContent in section 2."
        chunks = self.crawler.chunk_markdown(
            test_content, "https://example.com/test", "Test Document"
        )

        # Verify chunks
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].url, "https://example.com/test")
        self.assertEqual(chunks[0].title, "Test Document")

    @patch("src.documentation.crawler.AsyncWebCrawler")
    def test_crawl_documentation(self, mock_crawler_class):
        """Test the synchronous wrapper for crawl_documentation."""
        # Setup for asyncio.run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create a simple mock for the crawl_documentation method
        async def mock_crawl_documentation():
            return [
                DocumentationResource(
                    id="https://example.com/docs",
                    url="https://example.com/docs",
                    title="Test Documentation",
                    content="# Test Documentation",
                    metadata={},
                )
            ]

        # Patch the crawl_documentation method
        with patch.object(
            self.crawler, "crawl_documentation", mock_crawl_documentation
        ):
            # Call the synchronous wrapper
            results = self.crawler.crawl()

            # Verify results
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Test Documentation")

        # Clean up the event loop
        loop.close()


if __name__ == "__main__":
    unittest.main()
