# Rate Limiting

AutoMCP includes built-in rate limiting to prevent API throttling and ensure your applications stay within API provider limits.

## Rate Limiting Configuration

Rate limiting can be configured in your API configuration file:

```json
{
  "rate_limits": {
    "per_second": 5,
    "per_minute": 60,
    "per_hour": 1000,
    "enabled": true
  }
}
```

## Available Rate Limit Types

AutoMCP supports multiple rate limit windows:

| Option | Type | Description |
|--------|------|-------------|
| `per_second` | number | Maximum requests per second |
| `per_minute` | number | Maximum requests per minute |
| `per_hour` | number | Maximum requests per hour |
| `per_day` | number | Maximum requests per day |
| `enabled` | boolean | Whether rate limiting is enabled |

You can specify one or more rate limit windows. AutoMCP will enforce all configured limits.

## How Rate Limiting Works

AutoMCP uses a token bucket algorithm for rate limiting:

1. Each rate limit window has a bucket of tokens
2. Tokens are added to the bucket at the configured rate
3. Each API request consumes one token
4. If no tokens are available, the request is delayed until a token becomes available
5. The maximum number of tokens in a bucket equals the rate limit

This approach ensures smooth API usage while preventing bursts that might trigger API provider limits.

## Rate Limit Behavior

When a request would exceed the rate limit:

1. The request is not dropped but queued
2. AutoMCP will wait until the request can be made within the rate limits
3. If multiple rate limits are configured, the request will wait for all limits to be satisfied

## Configuring Multiple Rate Limits

For APIs with complex rate limiting requirements, you can specify multiple limits:

```json
{
  "rate_limits": {
    "per_second": 5,
    "per_minute": 100,
    "per_hour": 1000,
    "enabled": true
  }
}
```

This configuration enforces:
- No more than 5 requests per second
- No more than 100 requests per minute
- No more than 1000 requests per hour

## Disabling Rate Limiting

Rate limiting can be disabled by setting `enabled` to `false`:

```json
{
  "rate_limits": {
    "per_minute": 60,
    "enabled": false
  }
}
```

You can also omit the `rate_limits` section entirely to disable rate limiting.

## Best Practices

1. **Check API Documentation**: Review the API provider's rate limits and configure accordingly
2. **Add Buffer Space**: Set slightly lower limits than the API allows to account for other applications using the same API key
3. **Start Conservative**: Begin with conservative limits and increase as needed
4. **Monitor Usage**: Keep track of rate limit responses from the API to adjust your configuration 