# Authentication

AutoMCP supports various authentication methods for API integrations. This page explains how to configure authentication for your APIs.

## Supported Authentication Methods

AutoMCP currently supports the following authentication methods:

- **API Key**: Authentication using an API key in a header or query parameter
- **HTTP Authentication**: 
  - **Bearer Token**: Authentication using a Bearer token (commonly used with OAuth2)
  - **Basic Auth**: Username and password authentication
- **Environment Variables**: Dynamic authentication values from environment variables

## API Key Authentication

API key authentication is the most common method and can be configured in the header or query string:

```json
{
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
    "value": "your-api-key-here"
  }
}
```

### Header-based API Key

```json
{
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key",
    "value": "your-api-key-here"
  }
}
```

### Custom Authorization Header

```json
{
  "authentication": {
    "type": "apiKey",
    "in": "header",
    "name": "Authorization",
    "value": "ApiKey your-api-key-here"
  }
}
```

### Query Parameter API Key

```json
{
  "authentication": {
    "type": "apiKey",
    "in": "query",
    "name": "api_key",
    "value": "your-api-key-here"
  }
}
```

## Bearer Token Authentication

Bearer tokens (commonly used with OAuth2) use the HTTP authentication type with the bearer scheme:

```json
{
  "authentication": {
    "type": "http",
    "scheme": "bearer",
    "value": "your-token-here"
  }
}
```

The system will automatically add the "Bearer" prefix to the token when sending requests.

## Basic Authentication

For APIs that use HTTP Basic authentication:

```json
{
  "authentication": {
    "type": "http",
    "scheme": "basic",
    "username": "your-username",
    "password": "your-password"
  }
}
```

Alternatively, you can provide a pre-formatted value:

```json
{
  "authentication": {
    "type": "http",
    "scheme": "basic",
    "value": "your-username:your-password"
  }
}
```

## Using Environment Variables

For added security, you can reference environment variables in your configuration:

```json
{
  "authentication": {
    "type": "http",
    "scheme": "bearer",
    "value": "${API_TOKEN}"
  }
}
```

AutoMCP will replace `${API_TOKEN}` with the value of the `API_TOKEN` environment variable.

## Multiple Authentication Methods

Some APIs require multiple authentication methods. Currently, AutoMCP supports a single authentication method per API integration.

## Auto-Detection from OpenAPI Specification

AutoMCP automatically detects authentication requirements from the OpenAPI specification. If your specification includes security schemes, AutoMCP will validate your configuration against them:

```yaml
components:
  securitySchemes:
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
    bearerAuth:
      type: http
      scheme: bearer
```

Your configuration must match the security scheme type defined in the OpenAPI specification.

## Best Practices

1. **Use Environment Variables**: Instead of hardcoding credentials, use environment variables
2. **Minimum Privileges**: Use API keys with the minimum required permissions
3. **Separate Keys for Development/Production**: Use different keys for different environments
4. **Regular Rotation**: Regularly rotate API keys and tokens
5. **Secure Storage**: Keep your `.env` file or environment variables secure and never commit them to version control 

## Troubleshooting

If you encounter authentication errors, check:

1. **Match OpenAPI Spec**: Ensure your authentication type matches what's declared in the OpenAPI spec
2. **Correct Format**: API requires HTTP authentication but config provided apiKey
3. **Valid Credentials**: Verify your credentials are valid and not expired
4. **Environment Variables**: Confirm environment variables are set properly if used 