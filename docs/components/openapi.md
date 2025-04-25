# OpenAPI Integration

AutoMCP uses OpenAPI specifications to automatically generate MCP-compatible tools for your APIs.

## OpenAPI Specifications

[OpenAPI](https://www.openapis.org/) (formerly known as Swagger) is the industry standard for describing RESTful APIs. AutoMCP works with OpenAPI 3.0 and 3.1 specifications in JSON or YAML format.

OpenAPI specifications define:

- Available endpoints and operations
- Operation parameters
- Input and output schemas
- Authentication methods
- API metadata

## How AutoMCP Uses OpenAPI

AutoMCP parses OpenAPI specifications to:

1. **Discover Endpoints**: Find all available API endpoints and operations
2. **Generate Tools**: Convert API operations to MCP-compatible tools
3. **Extract Metadata**: Use descriptions, summaries, and schemas for better context
4. **Detect Authentication**: Identify authentication requirements

## Example OpenAPI Specification

Here's a simplified example of an OpenAPI specification:

```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0
  description: An example API for demonstration
paths:
  /users/{userId}:
    get:
      operationId: getUser
      summary: Get a user by ID
      description: Retrieves detailed information about a user
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
```

## From OpenAPI to MCP Tools

AutoMCP converts each operation in the OpenAPI specification to an MCP tool:

```json
{
  "name": "getUser",
  "description": "Get a user by ID - Retrieves detailed information about a user",
  "parameters": {
    "type": "object",
    "properties": {
      "userId": {
        "type": "string",
        "description": "The ID of the user"
      }
    },
    "required": ["userId"]
  }
}
```

## Providing OpenAPI Specifications

You can provide OpenAPI specifications in several ways:

1. **URL**: Point to a publicly accessible OpenAPI specification
   ```json
   "openapi_spec_url": "https://example.com/openapi.json"
   ```

2. **Local File**: Reference a local file
   ```json
   "openapi_spec_url": "./specs/my_api.json"
   ```

3. **Embedded**: Include the specification directly in your configuration
   ```json
   "openapi_spec": {
     "openapi": "3.0.0",
     "info": { ... },
     "paths": { ... }
   }
   ```

## Best Practices

For optimal results with AutoMCP:

1. Use descriptive `operationId` values for each operation
2. Provide detailed `summary` and `description` fields
3. Include comprehensive parameter descriptions
4. Use schema references (`$ref`) for consistent types
5. Document authentication requirements clearly

AutoMCP works best with well-documented OpenAPI specifications that follow these practices. 