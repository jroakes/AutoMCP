# Prompt Generator

The Prompt Generator component in AutoMCP allows you to define and serve prompts that help LLMs effectively use your API.

## Overview

The Prompt Generator:

1. Manages prompts defined in API configurations
2. Makes prompts accessible through the MCP server
3. Provides context and guidance for LLMs interacting with your API
4. Enables standardized responses for common tasks

## Prompt Configuration

Prompts are defined in your API configuration file:

```json
{
  "prompts": {
    "introduction": {
      "description": "Introduction to the API",
      "content": "This API provides access to user data and analytics..."
    },
    "authentication": {
      "description": "How to authenticate with the API",
      "content": "To authenticate, you need to provide an API key in the Authorization header..."
    },
    "common_use_cases": {
      "description": "Common use cases for the API",
      "content": "Here are some common tasks you can perform with this API..."
    }
  }
}
```

## Prompt Types

AutoMCP supports several types of prompts:

### Instructional Prompts

These explain how to use the API:

```json
{
  "prompts": {
    "api_usage": {
      "description": "How to use the API effectively",
      "content": "When using this API, consider these best practices..."
    }
  }
}
```

### Example Prompts

These provide examples of API usage:

```json
{
  "prompts": {
    "search_example": {
      "description": "Example of searching for users",
      "content": "To search for users, call the searchUsers tool with parameters: { \"query\": \"john\", \"limit\": 10 }"
    }
  }
}
```

### Error Handling Prompts

These guide error responses:

```json
{
  "prompts": {
    "rate_limit_handling": {
      "description": "How to handle rate limiting errors",
      "content": "If you encounter a 429 error, wait for the specified time and try again..."
    }
  }
}
```

## MCP Prompts Endpoint

Prompts are accessible through the MCP Prompts endpoint:

### List Prompts

```http
GET /api_name/prompts
```

Returns:
```json
{
  "prompts": [
    {
      "id": "introduction",
      "description": "Introduction to the API"
    },
    {
      "id": "authentication",
      "description": "How to authenticate with the API"
    }
  ]
}
```

### Call Prompt

```http
POST /api_name/prompts/call
Content-Type: application/json

{
  "id": "introduction"
}
```

Returns:
```json
{
  "content": "This API provides access to user data and analytics...",
  "metadata": {
    "description": "Introduction to the API"
  }
}
```

## Usage in LLMs

LLMs can use prompts to:

1. **Understand APIs**: Get an overview of what the API does
2. **Learn Authentication**: Understand how to authenticate requests
3. **Follow Best Practices**: Learn recommended usage patterns
4. **Handle Errors**: Properly respond to error conditions
5. **Generate Consistent Responses**: Maintain consistent format when presenting API results

## Best Practices

1. **Keep Prompts Focused**: Each prompt should address a specific topic
2. **Include Common Scenarios**: Cover the most frequent use cases
3. **Update Regularly**: Keep prompts in sync with API changes
4. **Use Markdown**: Format content with markdown for better readability
5. **Be Concise**: Keep prompts clear and to the point 