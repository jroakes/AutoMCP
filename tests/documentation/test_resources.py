"""Tests for the ResourceManager class in the documentation module."""

import os
import shutil
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from src.documentation.resources import (
    ResourceManager,
    DocumentationResource,
    DocumentationChunk,
)


class TestResourceManager(unittest.TestCase):
    """Tests for the ResourceManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for ChromaDB
        self.temp_dir = tempfile.mkdtemp()
        self.mock_openai_key = "test-openai-key"

        # Mock environment variable
        os.environ["OPENAI_API_KEY"] = self.mock_openai_key

    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Remove mock environment variable
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_init(self, mock_embedding_function, mock_persistent_client):
        """Test ResourceManager initialization."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Initialize ResourceManager
        manager = ResourceManager(db_directory=self.temp_dir, embedding_type="openai")

        # Check if the client was correctly initialized
        mock_persistent_client.assert_called_once_with(path=self.temp_dir)

        # Check if embedding function was created with correct parameters
        mock_embedding_function.assert_called_once()
        self.assertEqual(
            mock_embedding_function.call_args[1]["api_key"], self.mock_openai_key
        )

        # Check if collections were created
        self.assertEqual(mock_client.get_or_create_collection.call_count, 2)

    def test_normalize_url(self):
        """Test URL normalization."""
        test_urls = [
            # URL, Expected result
            ("https://example.com/docs?query=test#section", "https://example.com/docs"),
            ("https://example.com/docs/", "https://example.com/docs/"),
            (
                "https://example.com/docs/page?id=123&sort=asc",
                "https://example.com/docs/page",
            ),
            ("https://example.com/docs#section", "https://example.com/docs"),
        ]

        for url, expected in test_urls:
            result = ResourceManager.normalize_url(url)
            self.assertEqual(result, expected)

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_add_resource(self, mock_embedding_function, mock_persistent_client):
        """Test adding a resource to the manager."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Initialize ResourceManager
        manager = ResourceManager(db_directory=self.temp_dir, embedding_type="openai")

        # Create a test resource
        resource = DocumentationResource(
            id="https://example.com/docs",
            url="https://example.com/docs?query=test",
            title="Test Document",
            content="This is a test document.",
            metadata={"author": "Tester"},
        )

        # Add the resource
        manager.add_resource(resource)

        # Check if the resource was added to the collection
        mock_collection.upsert.assert_called_once()

        # Verify the resource was stored in memory
        normalized_url = manager.normalize_url(resource.url)
        self.assertIn(normalized_url, manager.resources)
        self.assertEqual(manager.resources[normalized_url], resource)

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_add_chunks(self, mock_embedding_function, mock_persistent_client):
        """Test adding chunks to the manager."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Initialize ResourceManager
        manager = ResourceManager(db_directory=self.temp_dir, embedding_type="openai")

        # Create test chunks
        chunks = [
            DocumentationChunk(
                id="chunk1",
                content="This is chunk 1",
                url="https://example.com/docs",
                title="Test Document",
                metadata={"index": 0},
            ),
            DocumentationChunk(
                id="chunk2",
                content="This is chunk 2",
                url="https://example.com/docs",
                title="Test Document",
                metadata={"index": 1},
            ),
        ]

        # Add chunks
        manager.add_chunks(chunks)

        # Check if chunks were added to the collection
        mock_collection.upsert.assert_called_once()

        # Verify the call arguments
        call_args = mock_collection.upsert.call_args[1]
        self.assertEqual(len(call_args["ids"]), 2)
        self.assertEqual(call_args["ids"], ["chunk1", "chunk2"])
        self.assertEqual(call_args["documents"], ["This is chunk 1", "This is chunk 2"])

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_get_resource(self, mock_embedding_function, mock_persistent_client):
        """Test retrieving a resource."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Initialize ResourceManager
        manager = ResourceManager(db_directory=self.temp_dir, embedding_type="openai")

        # Create a test resource
        resource = DocumentationResource(
            id="https://example.com/docs",
            url="https://example.com/docs",
            title="Test Document",
            content="This is a test document.",
            metadata={"author": "Tester"},
        )

        # Add the resource
        manager.resources[resource.url] = resource

        # Test retrieving the resource
        retrieved = manager.get_resource("https://example.com/docs")
        self.assertEqual(retrieved, resource)

        # Test retrieving with URL parameters
        retrieved = manager.get_resource("https://example.com/docs?query=test")
        self.assertEqual(retrieved, resource)

        # Test retrieving non-existent resource
        retrieved = manager.get_resource("https://example.com/nonexistent")
        self.assertIsNone(retrieved)

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_search_chunks(self, mock_embedding_function, mock_persistent_client):
        """Test searching for chunks."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Set up mock return for query
        mock_collection.query.return_value = {
            "ids": [["chunk1", "chunk2"]],
            "documents": [["Content of chunk 1", "Content of chunk 2"]],
            "metadatas": [
                [
                    {
                        "url": "https://example.com/docs",
                        "title": "Test Document",
                        "index": 0,
                    },
                    {
                        "url": "https://example.com/docs",
                        "title": "Test Document",
                        "index": 1,
                    },
                ]
            ],
            "distances": [[0.1, 0.3]],
        }

        # Initialize ResourceManager
        manager = ResourceManager(db_directory=self.temp_dir, embedding_type="openai")

        # Search for chunks
        results = manager.search_chunks("test query", limit=2)

        # Verify search was performed correctly
        mock_collection.query.assert_called_once_with(
            query_texts=["test query"], n_results=2
        )

        # Verify results format
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["content"], "Content of chunk 1")
        self.assertEqual(results[0]["url"], "https://example.com/docs")
        self.assertEqual(results[0]["title"], "Test Document")
        self.assertAlmostEqual(results[0]["relevance_score"], 0.95)  # 1.0 - (0.1/2)

        # Check second result
        self.assertEqual(results[1]["content"], "Content of chunk 2")
        self.assertAlmostEqual(results[1]["relevance_score"], 0.85)  # 1.0 - (0.3/2)

    @patch("chromadb.PersistentClient")
    @patch("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction")
    def test_huggingface_initialization(
        self, mock_openai_embedding, mock_persistent_client
    ):
        """Test initialization with HuggingFace embeddings."""
        # Set up mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch(
            "chromadb.utils.embedding_functions.HuggingFaceEmbeddingFunction"
        ) as mock_hf_embedding:
            # Initialize ResourceManager with HuggingFace
            ResourceManager(
                db_directory=self.temp_dir,
                embedding_type="huggingface",
                huggingface_api_key="test-hf-key",
            )

            # Check that HuggingFace embedding function was created
            mock_hf_embedding.assert_called_once()
            self.assertEqual(mock_hf_embedding.call_args[1]["api_key"], "test-hf-key")

            # Check that OpenAI embedding function was NOT used
            mock_openai_embedding.assert_not_called()


if __name__ == "__main__":
    unittest.main()
