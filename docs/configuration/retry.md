# Retry Handling

AutoMCP includes built-in retry functionality to handle transient errors and temporary API failures automatically.

## Retry Configuration

Configure retry behavior in your API configuration file:

```json
{
  "retry": {
    "max_retries": 3,
    "backoff_factor": 0.5,
    "retry_on_status_codes": [429, 500, 502, 503, 504],
    "enabled": true
  }
}
```

## Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_retries` | number | Maximum number of retry attempts | `3` |
| `backoff_factor` | number | Exponential backoff multiplier | `0.5` |
| `retry_on_status_codes` | array | HTTP status codes to trigger retries | `[429, 500, 502, 503, 504]` |
| `enabled` | boolean | Whether retry functionality is enabled | `true` |

## How Retry Works

When a request fails with a status code in `retry_on_status_codes`:

1. AutoMCP waits for a delay period
2. The request is retried
3. If the request fails again, the delay increases exponentially
4. This continues until either:
   - The request succeeds
   - The maximum number of retries is reached
   - A non-retryable error occurs

## Exponential Backoff

The delay between retries follows an exponential backoff pattern:

```
delay = backoff_factor * (2 ^ (retry_number - 1))
```

For example, with a `backoff_factor` of 0.5:
- First retry: 0.5 seconds
- Second retry: 1.0 seconds
- Third retry: 2.0 seconds

This strategy helps prevent overwhelming the API server during outages or rate limit issues.

## Retry Status Codes

By default, AutoMCP retries on these status codes:

- `429`: Too Many Requests (rate limiting)
- `500`: Internal Server Error
- `502`: Bad Gateway
- `503`: Service Unavailable
- `504`: Gateway Timeout

You can customize this list to match the specific behavior of your API.

## Retry Headers

AutoMCP also respects standard retry headers sent by the server:

- `Retry-After`: If present, AutoMCP will wait the specified number of seconds
- `X-RateLimit-Reset`: Used by some APIs to indicate when rate limits will reset

## Disabling Retry

Retry functionality can be disabled by setting `enabled` to `false`:

```json
{
  "retry": {
    "max_retries": 3,
    "enabled": false
  }
}
```

You can also omit the `retry` section entirely to use default retry behavior.

## Best Practices

1. **Start Conservative**: Begin with lower `max_retries` and increase if needed
2. **Tune for Your API**: Adjust `backoff_factor` based on the API's rate limits and recovery patterns
3. **Add Specific Status Codes**: Include any additional status codes that your API returns for retryable errors
4. **Avoid Retrying Client Errors**: Generally, don't retry 4xx errors (except 429) as they typically indicate client-side problems 