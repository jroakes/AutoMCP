"""
Name: Documentation crawler.
Description: Implements DocumentationCrawler for scraping and processing API documentation from websites. Uses Crawl4AI to extract content, convert to markdown, split into semantic chunks, and store in the vector database for retrieval.

The crawler can operate in two modes:
1. Static mode (default): JavaScript rendering is disabled for faster crawling of static content. Most documentation sites are server-side rendered and don't require JavaScript.
2. Dynamic mode: JavaScript rendering is enabled for sites that require client-side rendering. This is slower but necessary for single-page applications or sites with dynamic content.

Rendering can be controlled with the 'rendering' parameter (default: False).
"""

import asyncio
import logging
import time
from typing import List, Optional, Tuple, Any
from urllib.parse import urlparse
from pydantic import ValidationError

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BestFirstCrawlingStrategy,
    BrowserConfig,
    CacheMode,
    RateLimiter,
)
from crawl4ai.chunking_strategy import SlidingWindowChunking
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, ContentTypeFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

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
        bypass_cache: bool = True,
        remove_nav_elements: bool = False,
        word_count_threshold: int = 50,
        rendering: bool = True,
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
            rendering: Whether to enable JavaScript rendering (default: False)
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
        self.rendering = rendering

        # Parse the base_url to extract the domain for filtering
        parsed_url = urlparse(base_url)
        self.base_domain = parsed_url.netloc

    def create_markdown_generator(self) -> DefaultMarkdownGenerator:
        """Create a markdown generator with content filtering.

        Returns:
            DefaultMarkdownGenerator instance
        """
        return DefaultMarkdownGenerator(
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
            java_script_enabled=self.rendering,
        )

    def create_crawler_config(self, **kwargs: Any) -> CrawlerRunConfig:
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

        # Create filter chain
        logger.debug(f"Creating filter chain for {self.base_domain}")
        filter_chain = FilterChain(
            [
                # Domain boundaries
                DomainFilter(
                    allowed_domains=[self.base_domain],
                ),
                # Content type filtering
                ContentTypeFilter(allowed_types=["text/html"]),
            ]
        )

        # Use deep crawl strategy unless it's explicitly a single page request
        crawl_strategy = BestFirstCrawlingStrategy(
            max_depth=self.max_depth,
            include_external=False,
            filter_chain=filter_chain,
            max_pages=self.max_pages,
        )

        # Default excluded tags
        excluded_tags = ["script", "style", "iframe", "noscript"]
        if self.remove_nav_elements:
            excluded_tags.extend(["nav", "header", "footer"])

        # Override with any tags provided in kwargs
        if "excluded_tags" in kwargs:
            excluded_tags = kwargs.pop("excluded_tags")

        # Set wait_until based on rendering setting
        wait_until = kwargs.pop(
            "wait_until", "networkidle" if self.rendering else "domcontentloaded"
        )

        # Create base config
        config = CrawlerRunConfig(
            markdown_generator=md_generator,
            excluded_tags=excluded_tags,
            word_count_threshold=self.word_count_threshold,
            cache_mode=CacheMode.BYPASS if self.bypass_cache else CacheMode.ENABLED,
            page_timeout=60000,  # 60 seconds
            check_robots_txt=True,
            exclude_external_links=True,
            exclude_external_images=True,
            wait_until=wait_until,
            deep_crawl_strategy=crawl_strategy,

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
            # Get doc_id by normalizing the URL (removes scheme)
            doc_id = self.resource_manager.normalize_url(url)

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

                # Create a unique ID for this chunk using doc_id
                chunk_id = f"{doc_id}_{i}"

                # Create chunk with metadata
                chunk = DocumentationChunk(
                    id=chunk_id,
                    content=chunk_text,
                    url=url,  # Keep original URL
                    title=title,
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(chunks_text),
                        "chunking_method": chunker.__class__.__name__,
                        "doc_id": doc_id,  # Add doc_id to metadata
                    },
                )

                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error chunking markdown: {e}")
            return []

    async def crawl_documentation(
        self, start_url: Optional[str] = None
    ) -> List[DocumentationResource]:
        """Crawl documentation pages starting from a given URL.

        Args:
            start_url: The URL to start crawling from (defaults to self.base_url).

        Returns:
            List of crawled documentation resources.
        """
        # Determine crawl parameters, using instance defaults if not provided
        _start_url = start_url or self.base_url

        log_prefix = f"crawl_documentation(start={_start_url})"
        logger.info(f"{log_prefix}: Starting documentation crawl")

        # Create browser config
        browser_config = self.create_browser_config()

        # Track resources
        resources = []

        # Create crawler
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Configure crawl strategy

            # Create crawler config
            run_config = self.create_crawler_config(
                stream=True,
            )

            # Create dispatcher with rate limiting if needed
            if self.rate_limit_delay:
                dispatcher = MemoryAdaptiveDispatcher(
                    memory_threshold_percent=85.0,
                    check_interval=1.0,
                    max_session_permit=10,  # Consider making this configurable
                    rate_limiter=RateLimiter(
                        base_delay=self.rate_limit_delay, max_retries=3
                    ),
                )
                logger.debug(
                    f"Using memory adaptive dispatcher with rate limiting: {self.rate_limit_delay}"
                )
            else:
                dispatcher = None
                logger.debug("Using default dispatcher without rate limiting")

            # Run the crawl
            logger.info(f"Running crawl from {_start_url}")

            try:
                # Use streaming to process results as they arrive
                # The arun method handles both single URL and deep crawls based on config
                async for result in await crawler.arun(
                    url=_start_url, config=run_config, dispatcher=dispatcher
                ):
                    if not result.success:
                        logger.warning(
                            f"Failed to process page {result.url}: {result.error_message}"
                        )
                        continue

                    # Get normalized URL and ensure it's a valid string
                    normalized_url = self.resource_manager.normalize_url(result.url)
                    if not isinstance(normalized_url, str) or not normalized_url:
                        logger.warning(
                            f"Skipping result with invalid normalized URL from {result.url}"
                        )
                        continue

                    # Original URL for storing as metadata
                    original_url = result.url

                    # Extract title, provide default if None or invalid
                    title = result.metadata.get("title")
                    if not isinstance(title, str) or not title:
                        original_title = title  # Keep original for logging
                        title = f"Untitled - {normalized_url}"
                        logger.warning(
                            f"Page {original_url} has invalid title '{original_title}'. Using default: '{title}'"
                        )
                    logger.debug(f"Processing: {original_url} (Title: {title})")

                    # Get markdown content from result
                    if not hasattr(result, "markdown") or not result.markdown:
                        logger.warning(f"No markdown content for {original_url}")
                        continue

                    # Use fit_markdown if available, otherwise use raw_markdown
                    markdown_content = result.markdown.raw_markdown
                    fit_markdown = (
                        getattr(result.markdown, "fit_markdown", None)
                        or markdown_content
                    )

                    # Skip if content is empty after processing
                    if not fit_markdown or not fit_markdown.strip():
                        logger.warning(
                            f"Skipping {original_url} due to empty content after processing."
                        )
                        continue

                    try:
                        # Create resource
                        resource = DocumentationResource(
                            id=normalized_url,
                            url=original_url,  # Store original URL
                            title=title,
                            content=fit_markdown,
                            metadata={
                                "original_url": original_url,
                                "doc_id": normalized_url,
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

                        # Add to resource manager (only if not single page? No, RM should handle duplicates)
                        self.resource_manager.add_resource(resource)

                        # Chunk the content for vector search
                        chunks = self.chunk_markdown(
                            fit_markdown, normalized_url, title
                        )

                        # Add chunks to resource manager
                        if chunks:
                            self.resource_manager.add_chunks(chunks)
                            logger.debug(
                                f"Added {len(chunks)} chunks for {normalized_url}"
                            )

                        # Log progress
                        logger.debug(
                            f"Successfully processed page: {normalized_url} (Total found: {len(resources)})"
                        )

                    except ValidationError as ve:
                        logger.error(
                            f"Pydantic validation failed for {normalized_url}: {ve}"
                        )
                        # Continue to the next page instead of stopping the crawl
                        continue
                    except Exception as page_proc_e:
                        # Catch other unexpected errors during resource/chunk processing
                        logger.error(
                            f"Error processing page data for {normalized_url}: {page_proc_e}",
                            exc_info=True,
                        )
                        continue

            except Exception as e:
                # Catch errors during the crawler.arun() call itself
                logger.error(f"Fatal error during crawl execution: {e}", exc_info=True)

        logger.info(
            f"{log_prefix}: Crawl finished. Found {len(resources)} documentation pages"
        )
        return resources

    def crawl(self) -> List[DocumentationResource]:
        """Synchronous wrapper for crawl_documentation.

        Returns:
            List of crawled documentation resources
        """
        return asyncio.run(self.crawl_documentation())
