# Pagination

AutoMCP provides automatic pagination support for API endpoints that return multiple records across multiple pages.

## Pagination Configuration

Configure pagination in your API configuration file:

```json
{
  "pagination": {
    "enabled": true,
    "mechanism": "auto",
    "max_pages": 5,
    "results_field": "items"
  }
}
```

## Pagination Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enabled` | boolean | Whether pagination is enabled | `true` |
| `mechanism` | string | Pagination mechanism (`auto`, `link`, `cursor`, `offset`, `page`) | `auto` |
| `max_pages` | number | Maximum number of pages to retrieve | `5` |
| `results_field` | string | Field containing the array of results | `"items"` |

Additional pagination mechanism-specific options:

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `cursor_param` | string | Parameter name for cursor-based pagination | `"cursor"` |
| `cursor_response_field` | string | Response field containing the next cursor | `"next_cursor"` |
| `offset_param` | string | Parameter name for offset in offset pagination | `"offset"` |
| `limit_param` | string | Parameter name for limit in offset pagination | `"limit"` |
| `page_param` | string | Parameter name for page number in page-based pagination | `"page"` |
| `page_size_param` | string | Parameter name for page size in page-based pagination | `"per_page"` |

## Supported Pagination Mechanisms

AutoMCP supports several pagination mechanisms:

### Link-Based Pagination (RFC 5988)

Used by GitHub and other APIs, this approach includes pagination links in the response headers:

```
Link: <https://api.example.com/users?page=2>; rel="next", <https://api.example.com/users?page=5>; rel="last"
```

Configure with:
```json
{
  "pagination": {
    "mechanism": "link",
    "max_pages": 5
  }
}
```

### Cursor-Based Pagination

Uses a cursor or token to fetch the next page:

```json
{
  "items": [...],
  "next_cursor": "dXNlcjpYLWJhc2U2NHVybG9mZnNldA=="
}
```

Configure with:
```json
{
  "pagination": {
    "mechanism": "cursor",
    "cursor_param": "cursor",
    "cursor_response_field": "next_cursor",
    "max_pages": 5
  }
}
```

### Offset/Limit Pagination

Uses offset and limit parameters to control pagination:

```
GET /users?offset=50&limit=25
```

Configure with:
```json
{
  "pagination": {
    "mechanism": "offset",
    "offset_param": "offset",
    "limit_param": "limit",
    "max_pages": 5
  }
}
```

### Page-Based Pagination

Uses page numbers and page size:

```
GET /users?page=3&per_page=25
```

Configure with:
```json
{
  "pagination": {
    "mechanism": "page",
    "page_param": "page",
    "page_size_param": "per_page",
    "max_pages": 5
  }
}
```

### Auto-Detection

When `mechanism` is set to `auto`, AutoMCP will automatically detect the pagination mechanism based on:

1. Presence of Link headers
2. Response structure with cursor fields
3. Support for offset/limit parameters
4. Support for page/per_page parameters

This is the default and works for most APIs.

## How Pagination Works in AutoMCP

When a tool is executed that returns paginated results:

1. AutoMCP makes the initial request
2. It detects if more pages are available
3. If more pages exist and `max_pages` isn't reached, AutoMCP fetches the next page
4. Results from all pages are combined
5. The combined results are returned as a single response

## Limiting Result Size

To limit the total number of pages fetched, set the `max_pages` parameter:

```json
{
  "pagination": {
    "enabled": true,
    "max_pages": 3
  }
}
```

This will fetch at most 3 pages for any paginated endpoint.

## Disabling Pagination

Pagination can be disabled by setting `enabled` to `false`:

```json
{
  "pagination": {
    "enabled": false
  }
}
```

## Best Practices

1. **Set Reasonable Limits**: Use `max_pages` to prevent excessively large responses
2. **Use Auto When Possible**: The `auto` mechanism works for most APIs
3. **Specify Fields**: If your API uses non-standard field names, specify them in the configuration
4. **Test Pagination**: Verify pagination works correctly for your specific API 