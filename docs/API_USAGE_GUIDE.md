# EVE Gatekeeper API Usage Guide

This guide covers common patterns, best practices, and use cases for integrating with the EVE Gatekeeper API.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Common Endpoints](#common-endpoints)
- [Routing](#routing)
- [Risk Assessment](#risk-assessment)
- [Real-Time Kill Feed](#real-time-kill-feed)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Python Client Library](#python-client-library)

## Getting Started

### Base URL

```
Production: https://your-domain.com/api/v1
Local Development: http://localhost:8000/api/v1
```

### API Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

## Authentication

Currently, the API is open for read operations. Rate limiting is applied per IP address.

For future authenticated endpoints:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/...
```

## Common Endpoints

### List Systems

```bash
# Basic list with pagination
curl "http://localhost:8000/api/v1/systems/?page=1&page_size=20"

# Filter by security category
curl "http://localhost:8000/api/v1/systems/?category=lowsec"

# Search by name
curl "http://localhost:8000/api/v1/systems/?search=Jita"

# Filter by region
curl "http://localhost:8000/api/v1/systems/?region_name=The%20Forge"
```

Response:
```json
{
  "items": [
    {
      "name": "Jita",
      "security": 0.95,
      "category": "highsec",
      "region_id": 10000002,
      "region_name": "The Forge",
      "constellation_id": 20000020,
      "constellation_name": "Kimotoro"
    }
  ],
  "pagination": {
    "total": 7600,
    "page": 1,
    "page_size": 20,
    "total_pages": 380
  }
}
```

### Get System Details

```bash
curl "http://localhost:8000/api/v1/systems/Jita"
```

### Get Neighboring Systems

```bash
curl "http://localhost:8000/api/v1/systems/Jita/neighbors"
```

Response:
```json
["Perimeter", "New Caldari", "Maurasi", "Niyabainen"]
```

## Routing

### Calculate Route

```bash
# Basic route
curl "http://localhost:8000/api/v1/route/?from=Jita&to=Amarr"

# Safer route profile
curl "http://localhost:8000/api/v1/route/?from=Jita&to=Amarr&profile=safer"

# Avoid specific systems
curl "http://localhost:8000/api/v1/route/?from=Jita&to=Amarr&avoid=Niarja&avoid=Uedama"

# Use Thera wormholes
curl "http://localhost:8000/api/v1/route/?from=Jita&to=HED-GP&thera=true"

# Use Ansiblex jump bridges
curl "http://localhost:8000/api/v1/route/?from=Jita&to=Amarr&bridges=true"
```

#### Routing Profiles

| Profile | Description |
|---------|-------------|
| `shortest` | Minimum jumps, ignores risk |
| `safer` | Balanced approach, avoids high-risk |
| `paranoid` | Maximum safety, avoids all danger |

#### Response Structure

```json
{
  "from_system": "Jita",
  "to_system": "Amarr",
  "profile": "safer",
  "total_jumps": 15,
  "total_cost": 18.5,
  "max_risk": 12.3,
  "avg_risk": 4.2,
  "bridges_used": 0,
  "thera_used": 0,
  "pochven_used": 0,
  "path": [
    {
      "system_name": "Jita",
      "system_id": 30000142,
      "cumulative_jumps": 0,
      "cumulative_cost": 0,
      "risk_score": 5.0,
      "connection_type": "origin"
    },
    {
      "system_name": "Perimeter",
      "system_id": 30000144,
      "cumulative_jumps": 1,
      "cumulative_cost": 1.0,
      "risk_score": 3.5,
      "connection_type": "gate"
    }
  ]
}
```

### Compare Routes

Compare multiple routing profiles side-by-side:

```bash
curl -X POST "http://localhost:8000/api/v1/route/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "from_system": "Jita",
    "to_system": "HED-GP",
    "profiles": ["shortest", "safer", "paranoid"],
    "avoid": [],
    "use_bridges": false,
    "use_thera": false
  }'
```

### Route History

Get recently calculated routes:

```bash
curl "http://localhost:8000/api/v1/route/history?page=1&page_size=10"
```

## Risk Assessment

### Get System Risk

```bash
# With live zKillboard data
curl "http://localhost:8000/api/v1/systems/Rancer/risk?live=true"

# Without live data (cached/calculated)
curl "http://localhost:8000/api/v1/systems/Rancer/risk?live=false"

# With ship profile
curl "http://localhost:8000/api/v1/systems/Rancer/risk?ship_profile=hauler"
```

#### Ship Profiles

| Profile | Description |
|---------|-------------|
| `default` | Standard risk calculation |
| `hauler` | Higher risk in lowsec/nullsec |
| `frigate` | Lower risk overall |
| `cruiser` | Moderate risk adjustment |
| `battleship` | Higher risk in nullsec |
| `mining` | Very high risk everywhere |
| `capital` | Extreme risk in nullsec |
| `cloaky` | Lower risk everywhere |

#### Risk Response

```json
{
  "system_name": "Rancer",
  "score": 72.5,
  "danger_level": "high",
  "breakdown": {
    "security_component": 40.0,
    "kills_component": 22.5,
    "pods_component": 10.0
  },
  "zkill_stats": {
    "kills": 45,
    "pods": 12,
    "total_value": 5000000000
  },
  "ship_profile": null
}
```

#### Danger Levels

| Score Range | Level |
|-------------|-------|
| 0-20 | low |
| 20-50 | medium |
| 50-80 | high |
| 80-100 | extreme |

## Real-Time Kill Feed

Connect to the WebSocket endpoint for real-time kill notifications:

```
ws://localhost:8000/api/v1/ws/killfeed
```

### JavaScript Example

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/killfeed');

ws.onopen = () => {
  console.log('Connected to kill feed');

  // Subscribe to specific systems
  ws.send(JSON.stringify({
    action: 'subscribe',
    type: 'systems',
    ids: [30000142, 30003068]  // Jita, Rancer
  }));
};

ws.onmessage = (event) => {
  const kill = JSON.parse(event.data);
  console.log(`Kill in ${kill.solar_system_name}: ${kill.ship_type_id}`);
};

ws.onclose = () => {
  console.log('Disconnected from kill feed');
};
```

### Python Example

See `examples/websocket_client.py` for a complete Python client with:
- Automatic reconnection
- Exponential backoff
- Subscription management

## Rate Limiting

Default limits:
- **Per IP**: 60 requests/minute
- **Burst**: 20 requests

Rate limit headers in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
```

When rate limited (429):
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

### Best Practices

1. **Cache responses** - Route and risk data doesn't change frequently
2. **Batch requests** - Use `/route/compare` instead of multiple `/route/` calls
3. **Use `live=false`** - For risk checks, cached data is often sufficient
4. **Respect rate limits** - Implement exponential backoff on 429

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Server error |

### Error Response Format

```json
{
  "detail": "System 'NonExistent' not found"
}
```

### Common Errors

**Invalid system name:**
```json
{
  "detail": "System 'NotASystem' not found"
}
```

**Invalid routing profile:**
```json
{
  "detail": "Unknown routing profile: 'invalid'. Available: shortest, safer, paranoid"
}
```

**No route possible:**
```json
{
  "detail": "No route found between 'Jita' and 'J123456'"
}
```

## Python Client Library

A complete Python client is available in `examples/gatekeeper_client.py`:

### Synchronous Usage

```python
from gatekeeper_client import GatekeeperClient, SystemNotFoundError

with GatekeeperClient("http://localhost:8000") as client:
    # Calculate route
    route = client.get_route("Jita", "Amarr", profile="safer")
    print(f"Route takes {route.total_jumps} jumps")

    # Get risk
    try:
        risk = client.get_risk("Rancer", live=True)
        print(f"Risk score: {risk.score}")
    except SystemNotFoundError:
        print("System not found")
```

### Asynchronous Usage

```python
from gatekeeper_client import AsyncGatekeeperClient

async with AsyncGatekeeperClient("http://localhost:8000") as client:
    # Get multiple risks concurrently
    risks = await client.get_risks(["Jita", "Rancer", "HED-GP"])

    for risk in risks:
        print(f"{risk.system_name}: {risk.score}")
```

## Use Case Examples

### Trip Planning

```python
# Find safest route with rest stops
with GatekeeperClient(BASE_URL) as client:
    # Get main route
    route = client.get_route("Jita", "HED-GP", profile="safer")

    # Check risk at each system
    for hop in route.path:
        risk = client.get_risk(hop["system_name"], live=False)
        if risk.score > 50:
            print(f"Warning: {hop['system_name']} is dangerous!")
```

### Intel Integration

```python
# Monitor systems for increased activity
client = KillFeedClient("ws://localhost:8000/api/v1/ws/killfeed")

def on_kill(event):
    if event.system_id in watched_systems:
        send_discord_alert(f"Activity in {event.system_name}")

client.on_kill = on_kill
await client.connect()
```

### Fleet Routing

```python
# Route for different ship types in fleet
fleet_ships = ["frigate", "cruiser", "capital"]

with GatekeeperClient(BASE_URL) as client:
    comparison = client.compare_routes("Jita", "HED-GP")

    for route in comparison["routes"]:
        print(f"{route['profile']}: {route['total_jumps']} jumps, "
              f"max risk {route['max_risk']}")

    print(f"\nRecommendation: {comparison['recommendation']}")
```

## Support

- **API Documentation**: http://localhost:8000/docs
- **GitHub Issues**: https://github.com/Arete-Consortium/EVE_Gatekeeper/issues
- **Status Endpoint**: `GET /api/v1/status/`
