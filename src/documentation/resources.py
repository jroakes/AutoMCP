"""
Name: Document Resource Management.
Description: Manages documentation resources, providing storage, indexing, and retrieval capabilities for documentation content through vector search.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import chromadb
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field

from ..constants import (
    DEFAULT_DB_DIRECTORY,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_SENTENCE_TRANSFORMER_MODEL,
)

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
        db_directory: str = DEFAULT_DB_DIRECTORY,
        embedding_type: str = "openai",
        embedding_model: Optional[str] = None,
        server_name: str = "default",
    ):
        """Initialize the resource manager.

        Args:
            db_directory: Directory to store the vector database
            embedding_type: Type of embedding function to use ('openai' or 'huggingface')
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
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for OpenAI embeddings"
                )

            model = embedding_model or DEFAULT_OPENAI_MODEL
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_api_key, model_name=model
            )
        elif embedding_type == "huggingface":
            huggingface_api_key = os.environ.get("HUGGINGFACE_API_KEY")

            model = embedding_model or DEFAULT_SENTENCE_TRANSFORMER_MODEL
            self.embedding_function = embedding_functions.HuggingFaceEmbeddingFunction(
                api_key=huggingface_api_key if huggingface_api_key else None,
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
        """Normalize a URL by removing scheme, query parameters and fragments.

        This creates a document ID suitable for use in MCP URIs.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL string without scheme
        """
        parsed = urlparse(url)

        # Create a path that includes netloc and path but no scheme
        doc_id = parsed.netloc + parsed.path

        # Remove trailing slash if present
        if doc_id.endswith("/"):
            doc_id = doc_id[:-1]

        return doc_id

    def add_resource(self, resource: DocumentationResource) -> None:
        """Add a documentation resource to the manager.

        Args:
            resource: The documentation resource to add
        """
        # Normalize the URL to use as a canonical ID (without scheme)
        doc_id = self.normalize_url(resource.url)
        original_url = resource.url

        # Add to ChromaDB without embeddings
        try:
            # Chroma expects *lists* for every field when performing ``upsert``.
            # The document collection does **not** need real embeddings because it
            # is used only for look-ups / listing, so we omit the ``embeddings``
            # argument entirely – this avoids shape-mismatch errors that were
            # silently preventing the pages from being stored.

            self.docs_collection.upsert(
                ids=[doc_id],
                documents=[resource.content],
                metadatas=[
                    {
                        "url": original_url,  # Store the original URL as metadata
                        "doc_id": doc_id,  # Store the doc_id as metadata
                        "title": resource.title,
                        **resource.metadata,
                    }
                ],
            )

            logger.debug(f"Added resource to document collection: {doc_id}")
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
                    {
                        "url": chunk.url,  # Original URL
                        "doc_id": self.normalize_url(
                            chunk.url
                        ),  # Add doc_id to metadata
                        "title": chunk.title,
                        **chunk.metadata,
                    }
                    for chunk in chunks
                ],
            )
            logger.debug(f"Added {len(chunks)} chunks to vector DB")
        except Exception as e:
            logger.error(f"Error adding chunks to vector DB: {e}")

    def get_resource(self, doc_id: str) -> Optional[DocumentationResource]:
        """Get a documentation resource by doc_id.

        Args:
            doc_id: The document ID (normalized URL without scheme)

        Returns:
            The documentation resource, or None if not found
        """
        try:
            result = self.docs_collection.get(ids=[doc_id])
            if result and result["documents"] and len(result["documents"]) > 0:
                metadata = result["metadatas"][0] if result["metadatas"] else {}
                # Get the original URL from metadata if available
                original_url = metadata.get("url", "")

                return DocumentationResource(
                    id=doc_id,
                    url=original_url,
                    title=metadata.get("title", ""),
                    content=result["documents"][0],
                    metadata={
                        k: v
                        for k, v in metadata.items()
                        if k not in ["url", "title", "doc_id"]
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

                # Original URL can be obtained from metadata
                original_url = metadata.get("url", "")

                # Format as MCP resource with proper URI format
                resources.append(
                    {
                        "uri": f"docs://{doc_id}",
                        "name": title,
                        "description": f"Documentation page: {title}",
                        "content": results["documents"][i],
                        "metadata": {
                            "original_url": original_url,
                            # Include other metadata that might be useful
                            "doc_id": doc_id,
                        },
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
            List of matching chunks
        """
        try:
            if not query:
                return []

            # Search the chunks collection
            results = self.chunks_collection.query(
                query_texts=[query],
                n_results=limit,
            )

            # Format results for consumption
            formatted_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else None
                if not metadata:
                    continue

                # Get necessary metadata
                url = metadata.get("url", "")
                title = metadata.get("title", "Untitled")
                content = results["documents"][0][i]

                # Add to results
                formatted_results.append(
                    {
                        "id": doc_id,
                        "url": url,
                        "title": title,
                        "content": content,
                        "score": (
                            results["distances"][0][i]
                            if "distances" in results
                            else None
                        ),
                    }
                )

            return formatted_results
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []

    def clear(self) -> None:
        """Clear all data in the resource manager."""
        try:
            # Get collection names for this server
            docs_collection_name = f"{self.server_name}_docs"
            chunks_collection_name = f"{self.server_name}_chunks"

            # Delete collections if they exist
            try:
                self.client.delete_collection(docs_collection_name)
                self.client.delete_collection(chunks_collection_name)
            except Exception:
                # Collections might not exist, ignore
                pass

            # Recreate collections
            self.docs_collection = self.client.get_or_create_collection(
                name=docs_collection_name
            )
            self.chunks_collection = self.client.get_or_create_collection(
                name=chunks_collection_name, embedding_function=self.embedding_function
            )

            logger.info(f"Cleared all data for server: {self.server_name}")
        except Exception as e:
            logger.error(f"Error clearing resources: {e}")

    def is_empty(self) -> bool:
        """Check if the resource manager is empty.

        Returns:
            True if empty, False otherwise
        """
        try:
            # Check if docs collection is empty
            results = self.docs_collection.get()
            return len(results.get("ids", [])) == 0
        except Exception:
            # If there's an error (e.g., collection doesn't exist), consider it empty
            return True

    def exists(self) -> bool:
        """Check if the database for this resource manager exists.

        Returns:
            True if the database exists, False otherwise
        """
        if not os.path.exists(self.db_directory):
            return False

        try:
            # Get collection names for this server
            docs_collection_name = f"{self.server_name}_docs"
            chunks_collection_name = f"{self.server_name}_chunks"

            # Check if collections exist in the database
            return docs_collection_name in [
                c.name for c in self.client.list_collections()
            ] and chunks_collection_name in [
                c.name for c in self.client.list_collections()
            ]
        except Exception:
            # If there's an error accessing the database, consider it doesn't exist
            return False
