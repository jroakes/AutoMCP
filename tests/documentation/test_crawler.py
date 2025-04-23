"""Tests for the DocumentationCrawler class in the documentation module."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.documentation.crawler import DocumentationCrawler
from src.documentation.resources import (
    ResourceManager,
    DocumentationResource,
    DocumentationChunk,
)


class TestDocumentationCrawler(unittest.TestCase):
    """Tests for the DocumentationCrawler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock ResourceManager
        self.mock_resource_manager = MagicMock(spec=ResourceManager)

        # Set up a crawler for testing
        self.base_url = "https://example.com/docs"
        self.crawler = DocumentationCrawler(
            base_url=self.base_url,
            resource_manager=self.mock_resource_manager,
            max_pages=5,
            max_depth=2,
            bypass_cache=True,
        )

    def test_init(self):
        """Test crawler initialization."""
        # Check if attributes are properly set
        self.assertEqual(self.crawler.base_url, self.base_url)
        self.assertEqual(self.crawler.resource_manager, self.mock_resource_manager)
        self.assertEqual(self.crawler.max_pages, 5)
        self.assertEqual(self.crawler.max_depth, 2)
        self.assertTrue(self.crawler.bypass_cache)
        self.assertEqual(self.crawler.base_domain, "example.com")

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
        # Create browser config
        browser_config = self.crawler.create_browser_config()

        # Test that config is set correctly
        self.assertTrue(browser_config.headless)
        self.assertEqual(browser_config.user_agent, self.crawler.user_agent)
        self.assertEqual(browser_config.viewport_width, 1280)
        self.assertEqual(browser_config.viewport_height, 800)
        self.assertTrue(browser_config.ignore_https_errors)

    def test_create_crawler_config(self):
        """Test the creation of crawler configuration."""
        # Mock markdown generator
        mock_md_generator = MagicMock()

        # Create crawler config
        crawler_config = self.crawler.create_crawler_config(
            markdown_generator=mock_md_generator, excluded_tags=["test"]
        )

        # Test that config is set correctly
        self.assertEqual(crawler_config.markdown_generator, mock_md_generator)
        self.assertEqual(crawler_config.excluded_tags, ["test"])

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

    @patch("crawl4ai.chunking_strategy.TopicSegmentationChunking")
    def test_chunk_markdown_with_topic_segmentation(self, mock_topic_chunking):
        """Test chunking with TopicSegmentationChunking."""
        # Mock chunker
        mock_chunker = MagicMock()
        mock_topic_chunking.return_value = mock_chunker

        # Mock chunks
        mock_chunker.chunk.return_value = ["Chunk 1", "Chunk 2"]

        # Mock normalize_url
        self.mock_resource_manager.normalize_url.return_value = (
            "https://example.com/docs"
        )

        # Test chunking
        chunks = self.crawler.chunk_markdown(
            "Sample text", "https://example.com/docs", "Test Doc"
        )

        # Verify chunking was performed
        mock_chunker.chunk.assert_called_once_with("Sample text")

        # Verify chunks were created correctly
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].id, "https://example.com/docs_0")
        self.assertEqual(chunks[0].content, "Chunk 1")
        self.assertEqual(chunks[0].url, "https://example.com/docs")
        self.assertEqual(chunks[0].title, "Test Doc")

        self.assertEqual(chunks[1].id, "https://example.com/docs_1")
        self.assertEqual(chunks[1].content, "Chunk 2")

    @patch("crawl4ai.chunking_strategy.TopicSegmentationChunking")
    @patch("crawl4ai.chunking_strategy.SlidingWindowChunking")
    def test_chunk_markdown_fallback(self, mock_sliding_chunking, mock_topic_chunking):
        """Test chunking fallback to SlidingWindowChunking."""
        # Make TopicSegmentationChunking fail
        mock_topic_chunking.side_effect = ImportError("Test error")

        # Mock sliding window chunker
        mock_chunker = MagicMock()
        mock_sliding_chunking.return_value = mock_chunker

        # Mock chunks
        mock_chunker.chunk.return_value = ["Chunk 1", "Chunk 2"]

        # Mock normalize_url
        self.mock_resource_manager.normalize_url.return_value = (
            "https://example.com/docs"
        )

        # Test chunking
        chunks = self.crawler.chunk_markdown(
            "Sample text", "https://example.com/docs", "Test Doc"
        )

        # Verify sliding chunker was created with correct parameters
        mock_sliding_chunking.assert_called_once_with(
            window_size=self.crawler.chunk_size,
            step=self.crawler.chunk_size - self.crawler.chunk_overlap,
        )

        # Verify chunking was performed
        mock_chunker.chunk.assert_called_once_with("Sample text")

        # Verify chunks were created correctly
        self.assertEqual(len(chunks), 2)


# Using unittest specific classes for async testing
class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases."""

    def run_async(self, coro):
        """Run an async function in the event loop."""
        return asyncio.get_event_loop().run_until_complete(coro)


class TestDocumentationCrawlerAsync(AsyncTestCase):
    """Async tests for DocumentationCrawler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock ResourceManager
        self.mock_resource_manager = MagicMock(spec=ResourceManager)

        # Set up a crawler for testing
        self.base_url = "https://example.com/docs"
        self.crawler = DocumentationCrawler(
            base_url=self.base_url,
            resource_manager=self.mock_resource_manager,
            max_pages=5,
            max_depth=2,
            bypass_cache=True,
        )

    @patch("src.documentation.crawler.AsyncWebCrawler")
    def test_crawl_page(self, mock_crawler_class):
        """Test crawling a single page."""
        # Mock AsyncWebCrawler instance
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        # Mock the run result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = {"title": "Test Page"}
        mock_result.markdown = MagicMock()
        mock_result.markdown.raw_markdown = "Test content"
        mock_result.markdown.fit_markdown = "Filtered test content"

        mock_crawler.arun.return_value = mock_result

        # Mock normalize_url
        self.mock_resource_manager.normalize_url.return_value = (
            "https://example.com/page"
        )

        # Test crawling a page
        resource = self.run_async(self.crawler.crawl_page("https://example.com/page"))

        # Verify crawler was called correctly
        mock_crawler.arun.assert_called_once()

        # Verify resource was created correctly
        self.assertIsNotNone(resource)
        self.assertEqual(resource.id, "https://example.com/page")
        self.assertEqual(resource.url, "https://example.com/page")
        self.assertEqual(resource.title, "Test Page")
        self.assertEqual(resource.content, "Filtered test content")
        self.assertEqual(resource.metadata["original_url"], "https://example.com/page")

    @patch("src.documentation.crawler.AsyncWebCrawler")
    def test_crawl_page_failure(self, mock_crawler_class):
        """Test crawling a page that fails."""
        # Mock AsyncWebCrawler instance
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        # Mock the run result with failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Failed to crawl"

        mock_crawler.arun.return_value = mock_result

        # Test crawling a page that fails
        resource = self.run_async(
            self.crawler.crawl_page("https://example.com/error-page")
        )

        # Verify resource is None
        self.assertIsNone(resource)

    # Properly test the synchronous crawl method without unawaited coroutines
    def test_crawl_sync_wrapper(self):
        """Test the synchronous crawl wrapper."""
        # Create a mock for the crawl_documentation method
        mock_result = [MagicMock(spec=DocumentationResource)]

        # Replace the actual async method with a Mock object
        self.crawler.crawl_documentation = MagicMock()

        # Mock asyncio.run to return our expected result
        with patch("asyncio.run", return_value=mock_result) as mock_run:
            # Call the synchronous wrapper
            result = self.crawler.crawl()

            # Verify that asyncio.run was called (but don't compare the exact mock object)
            self.assertEqual(mock_run.call_count, 1)

            # Verify that the result is correct
            self.assertEqual(result, mock_result)


# Using TestCase.skipIf for a complex test that requires more mocking
@unittest.skip("Integration test requiring more complex mocking")
class TestDocumentationCrawlerIntegration(unittest.TestCase):
    """Integration tests for DocumentationCrawler class."""

    @patch("src.documentation.crawler.AsyncWebCrawler")
    async def test_crawl_documentation(self, mock_crawler_class):
        """Test crawling multiple documentation pages."""
        # This test would be more complex and require mocking the streaming iterator
        # for the deep crawl, along with a lot of other mocks.
        pass


if __name__ == "__main__":
    unittest.main()
