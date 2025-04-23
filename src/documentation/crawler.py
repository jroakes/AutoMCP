"""Documentation crawler for gathering API documentation using Crawl4AI."""

import asyncio
import logging
import time
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BFSDeepCrawlStrategy,
    BrowserConfig,
    CacheMode,
)
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .resources import DocumentationResource, DocumentationChunk, ResourceManager

logger = logging.getLogger(__name__)


class DocumentationCrawler:
    """Crawler for API documentation using Crawl4AI."""

    def __init__(
        self,
        base_url: str,
        resource_manager: ResourceManager,
        max_pages: int = 20,
        max_depth: int = 3,
        rate_limit_delay: Optional[Tuple[float, float]] = None,
        user_agent: str = "Mozilla/5.0 Documentation Crawler",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        bypass_cache: bool = False,
        remove_nav_elements: bool = True,
        word_count_threshold: int = 50,
    ):
        """Initialize the documentation crawler.

        Args:
            base_url: The base URL for the documentation
            resource_manager: The resource manager to store crawled content
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth to crawl
            rate_limit_delay: Tuple of (min, max) seconds for rate limiting
            user_agent: User agent to use for requests
            chunk_size: Size of content chunks for vectorization (in words)
            chunk_overlap: Overlap between chunks (in words)
            bypass_cache: Whether to bypass the cache
            remove_nav_elements: Whether to remove navigation elements from content
            word_count_threshold: Minimum number of words for a content block to be considered
        """
        self.base_url = base_url
        self.resource_manager = resource_manager
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.bypass_cache = bypass_cache
        self.remove_nav_elements = remove_nav_elements
        self.word_count_threshold = word_count_threshold

        # Parse the base_url to extract the domain for filtering
        parsed_url = urlparse(base_url)
        self.base_domain = parsed_url.netloc

    def create_markdown_generator(self) -> DefaultMarkdownGenerator:
        """Create a markdown generator with content filtering.

        Returns:
            DefaultMarkdownGenerator instance
        """
        # Create a content filter to focus on main content
        content_filter = PruningContentFilter(
            threshold=0.45,  # Adjust based on content quality
            threshold_type="dynamic",
            min_word_threshold=10,
        )

        # Create markdown generator with the filter
        return DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_links": False,  # Keep links for reference
                "body_width": 0,  # No wrapping
                "escape_html": True,
                "skip_internal_links": True,  # Skip internal page anchors
                "include_sup_sub": True,  # Better handling of sup/sub elements
                "citations": True,  # Generate citations for links
            },
        )

    def create_browser_config(self) -> BrowserConfig:
        """Create a browser configuration.

        Returns:
            BrowserConfig instance
        """
        return BrowserConfig(
            headless=True,
            user_agent=self.user_agent,
            viewport_width=1280,
            viewport_height=800,
            ignore_https_errors=True,
        )

    def create_crawler_config(self, **kwargs) -> CrawlerRunConfig:
        """Create a crawler configuration with consistent settings.

        Args:
            **kwargs: Additional configuration parameters to override defaults

        Returns:
            CrawlerRunConfig instance
        """
        # Create a markdown generator
        md_generator = kwargs.pop(
            "markdown_generator", self.create_markdown_generator()
        )

        # Default excluded tags
        excluded_tags = ["script", "style", "iframe", "noscript"]
        if self.remove_nav_elements:
            excluded_tags.extend(["nav", "header", "footer"])

        # Override with any tags provided in kwargs
        if "excluded_tags" in kwargs:
            excluded_tags = kwargs.pop("excluded_tags")

        # Create base config
        config = CrawlerRunConfig(
            markdown_generator=md_generator,
            excluded_tags=excluded_tags,
            word_count_threshold=self.word_count_threshold,
            cache_mode=CacheMode.BYPASS if self.bypass_cache else CacheMode.ENABLED,
            page_timeout=60000,  # 60 seconds
            wait_for="networkidle",
            **kwargs,  # Additional parameters that override defaults
        )

        return config

    def chunk_markdown(
        self, text: str, url: str, title: str
    ) -> List[DocumentationChunk]:
        """Split markdown content into chunks using Crawl4AI's chunking strategies.

        Args:
            text: Markdown content to split
            url: URL of the content
            title: Title of the content

        Returns:
            List of document chunks
        """
        if not text:
            return []

        try:
            # Use TextTilingTokenizer for topic-based segmentation
            from crawl4ai.chunking_strategy import (
                TopicSegmentationChunking,
                SlidingWindowChunking,
            )

            # Try to use topic segmentation first
            chunker = None
            try:
                chunker = TopicSegmentationChunking()
                chunks_text = chunker.chunk(text)
            except (ImportError, Exception) as e:
                logger.warning(
                    f"TopicSegmentationChunking failed, falling back to SlidingWindowChunking: {e}"
                )
                # Fallback to sliding window if TextTilingTokenizer isn't available or fails
                chunker = SlidingWindowChunking(
                    window_size=self.chunk_size,
                    step=self.chunk_size - self.chunk_overlap,
                )
                chunks_text = chunker.chunk(text)

            # Create chunks with metadata
            chunks = []
            for i, chunk_text in enumerate(chunks_text):
                # Skip empty chunks
                if not chunk_text.strip():
                    continue

                # Create a unique ID for this chunk
                chunk_id = f"{self.resource_manager.normalize_url(url)}_{i}"

                # Create chunk with metadata
                chunk = DocumentationChunk(
                    id=chunk_id,
                    content=chunk_text,
                    url=url,
                    title=title,
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(chunks_text),
                        "chunking_method": chunker.__class__.__name__,
                    },
                )

                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error chunking markdown: {e}")
            return []

    async def crawl_page(self, url: str) -> Optional[DocumentationResource]:
        """Crawl a single page using Crawl4AI.

        Args:
            url: URL to crawl

        Returns:
            DocumentationResource if successful, None otherwise
        """
        try:
            # Create browser config
            browser_config = self.create_browser_config()

            # Create crawler config
            run_config = self.create_crawler_config()

            # Create crawler
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Crawl the page
                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    logger.error(f"Failed to crawl {url}: {result.error_message}")
                    return None

                # Get normalized URL
                normalized_url = self.resource_manager.normalize_url(url)

                # Extract title
                title = result.metadata.get("title", "Untitled")

                # Get markdown content
                markdown_content = result.markdown.raw_markdown
                fit_markdown = (
                    getattr(result.markdown, "fit_markdown", None) or markdown_content
                )

                # Create resource
                resource = DocumentationResource(
                    id=normalized_url,
                    url=normalized_url,
                    title=title,
                    content=fit_markdown,
                    metadata={"original_url": url, "crawled_at": time.time()},
                )

                return resource

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None

    async def crawl_documentation(self) -> List[DocumentationResource]:
        """Crawl documentation pages from the base URL.

        Returns:
            List of crawled documentation resources
        """
        logger.info(f"Starting documentation crawl from {self.base_url}")

        # Create browser config
        browser_config = self.create_browser_config()

        # Track resources
        resources = []

        # Create crawler
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Configure deep crawl strategy
            deep_crawl_config = self.create_crawler_config(
                deep_crawl_strategy=BFSDeepCrawlStrategy(
                    max_depth=self.max_depth,
                    include_external=False,
                    max_pages=self.max_pages,
                ),
                stream=True,  # Enable streaming results
            )

            # Create dispatcher with rate limiting if needed
            if self.rate_limit_delay:
                from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher
                from crawl4ai import RateLimiter

                dispatcher = MemoryAdaptiveDispatcher(
                    memory_threshold_percent=85.0,
                    check_interval=1.0,
                    max_session_permit=10,
                    rate_limiter=RateLimiter(
                        base_delay=self.rate_limit_delay, max_retries=3
                    ),
                )
                logger.info(
                    f"Using memory adaptive dispatcher with rate limiting: {self.rate_limit_delay}"
                )
            else:
                dispatcher = None
                logger.info("Using default dispatcher without rate limiting")

            # Run deep crawl with streaming
            logger.info(f"Running deep crawl from {self.base_url}")

            try:
                # Use streaming to process results as they arrive
                async for result in await crawler.arun(
                    url=self.base_url, config=deep_crawl_config, dispatcher=dispatcher
                ):
                    if not result.success:
                        logger.warning(f"Failed to crawl page: {result.error_message}")
                        continue

                    # Add the URL to the crawled set
                    normalized_url = self.resource_manager.normalize_url(result.url)

                    # Extract title
                    title = result.metadata.get("title", "Untitled")

                    # Get markdown content from result
                    if not hasattr(result, "markdown") or not result.markdown:
                        logger.warning(f"No markdown content for {result.url}")
                        continue

                    # Use fit_markdown if available, otherwise use raw_markdown
                    markdown_content = result.markdown.raw_markdown
                    fit_markdown = (
                        getattr(result.markdown, "fit_markdown", None)
                        or markdown_content
                    )

                    # Create resource
                    resource = DocumentationResource(
                        id=normalized_url,
                        url=normalized_url,
                        title=title,
                        content=fit_markdown,
                        metadata={
                            "original_url": result.url,
                            "crawled_at": time.time(),
                            "depth": (
                                result.metadata.get("depth", 0)
                                if hasattr(result, "metadata")
                                else 0
                            ),
                        },
                    )

                    # Add resource to list
                    resources.append(resource)

                    # Add to resource manager
                    self.resource_manager.add_resource(resource)

                    # Chunk the content for vector search
                    chunks = self.chunk_markdown(fit_markdown, normalized_url, title)

                    # Add chunks to resource manager
                    if chunks:
                        self.resource_manager.add_chunks(chunks)
                        logger.info(f"Added {len(chunks)} chunks for {normalized_url}")

                    # Log progress
                    logger.info(
                        f"Processed page: {normalized_url} (Total: {len(resources)})"
                    )

            except Exception as e:
                logger.error(f"Error during deep crawl: {e}")

        logger.info(f"Crawled {len(resources)} documentation pages")
        return resources

    def crawl(self) -> List[DocumentationResource]:
        """Synchronous wrapper for crawl_documentation.

        Returns:
            List of crawled documentation resources
        """
        return asyncio.run(self.crawl_documentation())
