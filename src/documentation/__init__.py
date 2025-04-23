"""Documentation handling module for AutoMCP."""

from .crawler import DocumentationCrawler
from .resources import DocumentationResource, DocumentationChunk, ResourceManager

__all__ = [
    "DocumentationCrawler",
    "DocumentationResource",
    "DocumentationChunk",
    "ResourceManager",
]
