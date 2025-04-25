# Documentation Crawler

The Documentation Crawler is a key component of AutoMCP that indexes API documentation for LLM context.

## Overview

The Documentation Crawler:

1. Crawls API documentation websites
2. Extracts content from pages
3. Segments content into manageable chunks
4. Stores chunks in a vector database
5. Provides search capabilities for LLMs

## How It Works

### Crawling Process

1. **Starting Point**: The crawler begins at the URL specified in `documentation_url`
2. **Discovery**: It finds links to other pages by analyzing HTML
3. **Depth Control**: It follows links up to the maximum depth
4. **Page Limit**: It stops after processing the maximum number of pages
5. **Content Extraction**: It extracts textual content from each page
6. **Chunking**: It breaks content into smaller, semantic chunks
7. **Indexing**: It creates embeddings for each chunk and stores them in a vector database

### Configuration Options

```json
{
  "documentation_url": "https://example.com/docs",
  "crawl": {
    "max_depth": 3,
    "max_pages": 100,
    "wait_time": 1.0,
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_depth` | number | Maximum link depth to crawl | `3` |
| `max_pages` | number | Maximum number of pages to process | `100` |
| `wait_time` | number | Wait time between requests (seconds) | `1.0` |
| `chunk_size` | number | Maximum characters per chunk | `1000` |
| `chunk_overlap` | number | Overlap between chunks (characters) | `200` |

## Vector Database

AutoMCP uses [ChromaDB](https://www.trychroma.com/) for vector storage:

1. **Embeddings**: Each chunk is converted to vector embeddings
2. **Metadata**: URLs and titles are stored with each chunk
3. **Semantic Search**: The database enables similarity-based search
4. **Persistent Storage**: Embeddings are stored in the specified database directory

## Resources API

The indexed documentation is exposed through the MCP Resources API, enabling LLMs to:

1. **List Resources**: Get a list of all available documentation resources
2. **Get Resource Content**: Retrieve specific documentation pages
3. **Search**: Find relevant documentation for queries

## Example Search

When an LLM needs information about authentication, it can search for it:

```http
POST /resources/search
Content-Type: application/json

{
  "query": "How do I authenticate with the API?",
  "limit": 3
}
```

The response includes the most relevant documentation chunks:

```json
{
  "results": [
    {
      "uri": "authentication",
      "title": "Authentication Guide",
      "content": "# Authentication Guide\n\nTo authenticate with our API, you need to provide an API key...",
      "score": 0.95
    },
    // More results...
  ]
}
```

## Best Practices

1. **Set Reasonable Limits**: Use appropriate `max_depth` and `max_pages` values
3. **Respect Rate Limits**: Adjust `wait_time` to avoid overloading the documentation server
4. **Tune Chunking**: Adjust `chunk_size` and `chunk_overlap` for better search quality 