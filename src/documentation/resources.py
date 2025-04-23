"""Resource management for documentation content and search capabilities."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from urllib.parse import urlparse, urlunparse

import chromadb
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentationChunk(BaseModel):
    """A chunk of documentation content for vectorization."""

    id: str
    content: str
    url: str
    title: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentationResource(BaseModel):
    """A documentation resource for MCP."""

    id: str
    url: str
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceManager:
    """Manager for documentation resources and vector search."""

    def __init__(
        self,
        db_directory: str = "./.chromadb",
        embedding_type: str = "openai",
        openai_api_key: Optional[str] = None,
        huggingface_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """Initialize the resource manager.

        Args:
            db_directory: Directory to store the vector database
            embedding_type: Type of embedding function to use ('openai' or 'huggingface')
            openai_api_key: API key for OpenAI (if using OpenAI embeddings)
            huggingface_api_key: API key for HuggingFace (if using HuggingFace embeddings)
            embedding_model: Model name to use for embeddings
        """
        self.db_directory = db_directory
        Path(db_directory).mkdir(parents=True, exist_ok=True)

        # Set up ChromaDB client
        self.client = chromadb.PersistentClient(path=db_directory)

        # Set up embedding function based on type
        if embedding_type == "openai":
            self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")

            model = embedding_model or "text-embedding-3-small"
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.openai_api_key, model_name=model
            )
        elif embedding_type == "huggingface":
            self.huggingface_api_key = huggingface_api_key or os.environ.get(
                "HUGGINGFACE_API_KEY"
            )

            model = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
            self.embedding_function = embedding_functions.HuggingFaceEmbeddingFunction(
                api_key=self.huggingface_api_key if self.huggingface_api_key else None,
                model_name=model,
            )
        else:
            raise ValueError(f"Unsupported embedding type: {embedding_type}")

        # Create collections for documents and chunks
        self.docs_collection = self.client.get_or_create_collection(
            name="documentation_pages", embedding_function=self.embedding_function
        )

        self.chunks_collection = self.client.get_or_create_collection(
            name="documentation_chunks", embedding_function=self.embedding_function
        )

        # In-memory cache for resource metadata
        self.resources: Dict[str, DocumentationResource] = {}

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize a URL by removing query parameters and fragments.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                "",  # Remove params
                "",  # Remove query
                "",  # Remove fragment
            )
        )

    def add_resource(self, resource: DocumentationResource) -> None:
        """Add a documentation resource to the manager.

        Args:
            resource: The documentation resource to add
        """
        # Normalize the URL to use as a canonical ID
        normalized_url = self.normalize_url(resource.url)

        # Store the resource in memory
        self.resources[normalized_url] = resource

        # Add to ChromaDB for vector search
        try:
            self.docs_collection.upsert(
                ids=[normalized_url],
                documents=[resource.content],
                metadatas=[
                    {
                        "url": normalized_url,
                        "title": resource.title,
                        **resource.metadata,
                    }
                ],
            )
            logger.info(f"Added resource to vector DB: {normalized_url}")
        except Exception as e:
            logger.error(f"Error adding resource to vector DB: {e}")

    def add_chunks(self, chunks: List[DocumentationChunk]) -> None:
        """Add documentation chunks to the vector database.

        Args:
            chunks: List of documentation chunks to add
        """
        # Batch add chunks to ChromaDB
        try:
            self.chunks_collection.upsert(
                ids=[chunk.id for chunk in chunks],
                documents=[chunk.content for chunk in chunks],
                metadatas=[
                    {"url": chunk.url, "title": chunk.title, **chunk.metadata}
                    for chunk in chunks
                ],
            )
            logger.info(f"Added {len(chunks)} chunks to vector DB")
        except Exception as e:
            logger.error(f"Error adding chunks to vector DB: {e}")

    def get_resource(self, url: str) -> Optional[DocumentationResource]:
        """Get a documentation resource by URL.

        Args:
            url: The URL of the resource

        Returns:
            The documentation resource, or None if not found
        """
        normalized_url = self.normalize_url(url)
        return self.resources.get(normalized_url)

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all available documentation resources.

        Returns:
            List of resource metadata
        """
        return [
            {
                "uri": url,
                "name": resource.title,
                "description": f"Documentation page: {resource.title}",
            }
            for url, resource in self.resources.items()
        ]

    def search_chunks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documentation chunks matching a query.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of matching chunks with metadata
        """
        results = self.chunks_collection.query(query_texts=[query], n_results=limit)

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, (doc, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    (
                        results["distances"][0]
                        if "distances" in results
                        else [0] * len(results["documents"][0])
                    ),
                )
            ):
                formatted_results.append(
                    {
                        "content": doc,
                        "url": metadata.get("url", ""),
                        "title": metadata.get("title", ""),
                        "relevance_score": (
                            1.0 - (distance / 2) if distance else 1.0
                        ),  # Normalize distance to a score
                        "metadata": {
                            k: v
                            for k, v in metadata.items()
                            if k not in ["url", "title"]
                        },
                    }
                )

        return formatted_results

    def clear_database(self) -> None:
        """Clear all data from the vector database."""
        self.client.reset()
        self.resources = {}

        # Recreate collections
        self.docs_collection = self.client.get_or_create_collection(
            name="documentation_pages", embedding_function=self.embedding_function
        )

        self.chunks_collection = self.client.get_or_create_collection(
            name="documentation_chunks", embedding_function=self.embedding_function
        )

        logger.info("Cleared vector database")
