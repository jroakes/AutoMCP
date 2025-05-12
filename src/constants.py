"""
Name: Constants and settings.
Description: Centralized location for constants and settings used throughout the AutoMCP application.
This file contains default values, configuration paths, and other constants to maintain consistency.
"""


# Database settings
DEFAULT_DB_DIRECTORY = "./.chromadb"

# Registry settings
DEFAULT_REGISTRY_FILE = "./.automcp_cache/registry.json"

# Embedding model settings
DEFAULT_EMBEDDING_TYPE = "openai"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Crawling settings
DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_DEPTH = 3
DEFAULT_RATE_LIMIT_DELAY = (1.0, 3.0)

# Server settings
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# Retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# Rate limit settings
DEFAULT_REQUESTS_PER_MINUTE = 60

# Default tools and endpoints
DEFAULT_TOOLS_ENDPOINT = "/tools"
DEFAULT_RESOURCES_ENDPOINT = "/resources"
DEFAULT_PROMPTS_ENDPOINT = "/prompts"

# Resource search settings
DEFAULT_MAX_SEARCH_RESULTS = 5
DEFAULT_SEARCH_THRESHOLD = 0.7

# Tool settings
DEFAULT_SUMMARY_TRUNCATION = 120
