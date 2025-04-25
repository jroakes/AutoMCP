"""Tests for the ResourceManager class in the documentation module."""

import os
import shutil
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np

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
        _manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Check if the client was correctly initialized
        mock_persistent_client.assert_called_once_with(path=self.temp_dir)

        # Check if embedding function was created with correct parameters
        mock_embedding_function.assert_called_once()
        self.assertEqual(
            mock_embedding_function.call_args[1]["api_key"], self.mock_openai_key
        )

        # Check if collections were created with proper namespacing
        self.assertEqual(mock_client.get_or_create_collection.call_count, 2)

        # Verify first call (docs collection)
        first_call_args = mock_client.get_or_create_collection.call_args_list[0][1]
        self.assertEqual(first_call_args["name"], "test_server_docs")

        # Verify second call (chunks collection)
        second_call_args = mock_client.get_or_create_collection.call_args_list[1][1]
        self.assertEqual(second_call_args["name"], "test_server_chunks")
        self.assertIsNotNone(second_call_args["embedding_function"])

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
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

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

        # Check if the resource was added to the collection with zero embeddings
        mock_collection.upsert.assert_called_once()
        upsert_args = mock_collection.upsert.call_args[1]
        self.assertEqual(upsert_args["ids"], ["https://example.com/docs"])
        self.assertEqual(upsert_args["documents"], ["This is a test document."])
        self.assertTrue(np.array_equal(upsert_args["embeddings"], np.zeros(384)))

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

        # Configure the get method to return test data
        mock_collection.get.return_value = {
            "ids": ["https://example.com/docs"],
            "documents": ["This is a test document."],
            "metadatas": [
                {
                    "title": "Test Document",
                    "author": "Tester",
                    "url": "https://example.com/docs",
                }
            ],
        }

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Test retrieving the resource
        retrieved = manager.get_resource("https://example.com/docs")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "https://example.com/docs")
        self.assertEqual(retrieved.title, "Test Document")
        self.assertEqual(retrieved.content, "This is a test document.")

        # Test retrieving with URL parameters
        retrieved = manager.get_resource("https://example.com/docs?query=test")
        self.assertIsNotNone(retrieved)

        # Configure get to return empty for non-existent resource
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

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

    @patch("chromadb.PersistentClient")
    def test_is_empty_with_empty_collections(self, mock_persistent_client):
        """Test is_empty returns True when collections are empty."""
        # Setup mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        empty_collection = MagicMock()
        empty_collection.count.return_value = 0

        # Setup collections with server-specific names
        test_docs = MagicMock()
        test_docs.name = "test_server_docs"
        test_chunks = MagicMock()
        test_chunks.name = "test_server_chunks"
        mock_client.list_collections.return_value = [test_docs, test_chunks]

        # Configure get_collection to return empty_collection
        mock_client.get_or_create_collection.return_value = empty_collection

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Call method
        result = manager.is_empty()

        # Verify result
        self.assertTrue(result)

    @patch("chromadb.PersistentClient")
    def test_is_empty_with_populated_collections(self, mock_persistent_client):
        """Test is_empty returns False when collections have documents."""
        # Setup mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        # Setup collection names with server prefix
        doc_pages = MagicMock()
        doc_pages.name = "test_server_docs"
        doc_chunks = MagicMock()
        doc_chunks.name = "test_server_chunks"
        mock_collections = [doc_pages, doc_chunks]
        mock_client.list_collections.return_value = mock_collections

        # Create mock collections with documents (non-empty)
        populated_collection = MagicMock()
        populated_collection.count.return_value = 10

        # Configure get_or_create_collection to return populated collections
        mock_client.get_or_create_collection.return_value = populated_collection

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Call method
        result = manager.is_empty()

        # Verify result
        self.assertFalse(result)

    @patch("chromadb.PersistentClient")
    def test_is_empty_with_missing_collections(self, mock_persistent_client):
        """Test is_empty returns True when collections don't exist."""
        # Setup mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        other_collection = MagicMock()
        other_collection.name = "other_collection"
        mock_client.list_collections.return_value = [other_collection]

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Call method
        result = manager.is_empty()

        # Verify result
        self.assertTrue(result)

    @patch("chromadb.PersistentClient")
    def test_is_empty_with_exception(self, mock_persistent_client):
        """Test is_empty handles exceptions gracefully."""
        # Setup mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        # Setup mock to raise an exception
        mock_client.list_collections.side_effect = Exception("Test exception")

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Call method
        result = manager.is_empty()

        # Verify result
        self.assertTrue(result)

    @patch("chromadb.PersistentClient")
    @patch("os.path.exists")
    def test_exists_method(self, mock_exists, mock_persistent_client):
        """Test exists method correctly checks if database exists."""
        # Setup mocks
        mock_client = MagicMock()
        mock_persistent_client.return_value = mock_client

        # Mock collections with proper name attributes and server prefix
        docs_collection = MagicMock()
        docs_collection.name = "test_server_docs"
        chunks_collection = MagicMock()
        chunks_collection.name = "test_server_chunks"

        # Set up list_collections to return collections with correct names
        mock_client.list_collections.return_value = [docs_collection, chunks_collection]

        # Mock directory exists
        mock_exists.return_value = True

        # Initialize ResourceManager
        manager = ResourceManager(
            db_directory=self.temp_dir,
            embedding_type="openai",
            server_name="test_server",
        )

        # Test when directory and collections exist
        self.assertTrue(manager.exists())

        # Test when directory doesn't exist
        mock_exists.return_value = False
        self.assertFalse(manager.exists())

        # Test when collections don't exist
        mock_exists.return_value = True
        other_collection = MagicMock()
        other_collection.name = "other_collection"
        mock_client.list_collections.return_value = [other_collection]
        self.assertFalse(manager.exists())


if __name__ == "__main__":
    unittest.main()
