"""
Name: Documentation resources.
Description: Implements ResourceManager for managing documentation chunks with vector search capabilities using OpenAI embeddings. Provides functionality for storing, retrieving, and semantically searching API documentation content.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from urllib.parse import urlparse, urlunparse

import numpy as np
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
        server_name: str = "default",
    ):
        """Initialize the resource manager.

        Args:
            db_directory: Directory to store the vector database
            embedding_type: Type of embedding function to use ('openai' or 'huggingface')
            openai_api_key: API key for OpenAI (if using OpenAI embeddings)
            huggingface_api_key: API key for HuggingFace (if using HuggingFace embeddings)
            embedding_model: Model name to use for embeddings
            server_name: Name of the server for collection namespacing
        """
        self.db_directory = db_directory
        self.server_name = server_name
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

        # Create collections for documents and chunks with server namespacing
        self.docs_collection = self.client.get_or_create_collection(
            name=f"{server_name}_docs",
            # default embedding function will be used
        )

        self.chunks_collection = self.client.get_or_create_collection(
            name=f"{server_name}_chunks", embedding_function=self.embedding_function
        )

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

        # Add to ChromaDB without embeddings
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
                embeddings=np.zeros(384),  # fill with zeroes
            )
            logger.debug(f"Added resource to document collection: {normalized_url}")
        except Exception as e:
            logger.error(
                f"Error adding resource to document collection: {e} in upsert."
            )

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
            logger.debug(f"Added {len(chunks)} chunks to vector DB")
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

        try:
            result = self.docs_collection.get(ids=[normalized_url])
            if result and result["documents"] and len(result["documents"]) > 0:
                metadata = result["metadatas"][0] if result["metadatas"] else {}
                return DocumentationResource(
                    id=normalized_url,
                    url=normalized_url,
                    title=metadata.get("title", ""),
                    content=result["documents"][0],
                    metadata={
                        k: v for k, v in metadata.items() if k not in ["url", "title"]
                    },
                )
        except Exception as e:
            logger.error(f"Error retrieving resource: {e}")

        return None

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all available documentation resources.

        Returns:
            List of resource metadata for MCP consumption
        """
        try:
            # Get all documents from docs collection
            results = self.docs_collection.get()

            resources = []
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                title = metadata.get("title", "Untitled")

                # Format as MCP resource - use proper URI format
                resources.append(
                    {
                        "uri": f"docs://{doc_id}",
                        "name": title,
                        "description": f"Documentation page: {title}",
                    }
                )

            # Add a special search resource with template URI
            resources.append(
                {
                    "uri": "search://{query}",
                    "name": "Search Documentation",
                    "description": "Search across all documentation chunks with a query parameter",
                }
            )

            return resources

        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            return []

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

    def clear(self) -> None:
        """Clear all resources from memory and the vector database."""
        # Clear vector database collections
        self.docs_collection.delete(where={})
        self.chunks_collection.delete(where={})
        logger.debug("Cleared vector database")

    def is_empty(self) -> bool:
        """Check if the resource manager is empty.

        Returns:
            True if the resource manager has no documents, False otherwise
        """
        try:
            # Check if collections exist and have documents
            collection_names = [c.name for c in self.client.list_collections()]

            docs_collection_name = f"{self.server_name}_docs"
            chunks_collection_name = f"{self.server_name}_chunks"

            if (
                docs_collection_name not in collection_names
                or chunks_collection_name not in collection_names
            ):
                return True

            return (
                self.docs_collection.count() == 0 or self.chunks_collection.count() == 0
            )
        except Exception as e:
            logger.warning(f"Error checking if collections are empty: {e}")
            # If there's an error, assume it's empty
            return True

    def exists(self) -> bool:
        """Check if the resource manager database exists.

        Returns:
            True if the database directory exists and collections are created, False otherwise
        """
        try:
            # Check if directory exists
            if not os.path.exists(self.db_directory):
                return False

            # Check if collections exist with proper namespace
            collection_names = [c.name for c in self.client.list_collections()]
            docs_collection_name = f"{self.server_name}_docs"
            chunks_collection_name = f"{self.server_name}_chunks"

            return (
                docs_collection_name in collection_names
                and chunks_collection_name in collection_names
            )
        except Exception as e:
            logger.warning(f"Error checking if database exists: {e}")
            return False
