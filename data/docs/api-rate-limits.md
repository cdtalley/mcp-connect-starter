# API Rate Limits

_Last updated: 2023-12-18_

Sample knowledge-base article bundled with the MCP Connect starter.

## Default limits

| Plan       | Requests / minute | Burst |
|------------|-------------------|-------|
| Starter    | 60                | 120   |
| Growth     | 300               | 600   |
| Enterprise | 1,200             | 2,400 |

## Requesting an increase

Enterprise customers with a sustained need above their tier's default limit
can request an increase through their account team. Increases are applied
per-API-key and reviewed quarterly.

## Handling 429 responses

Clients should respect the `Retry-After` header and use exponential
backoff with jitter. Repeated bursts that ignore `Retry-After` may result
in a temporary IP-level throttle independent of the per-key limit.
