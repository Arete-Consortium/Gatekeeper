# EVE Map Visualization - Technical Architecture

This document describes the technical architecture, data flow, and design decisions for the EVE Map Visualization project.

## Table of Contents
- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [API Data Acquisition Pipeline](#api-data-acquisition-pipeline)
- [Caching Systems](#caching-systems)
- [FastAPI Backend Architecture](#fastapi-backend-architecture)
- [Visualization Rendering Pipeline](#visualization-rendering-pipeline)
- [Data Models](#data-models)
- [Performance Considerations](#performance-considerations)

## System Overview

The EVE Map Visualization project consists of two main components:

1. **Frontend Visualization Layer**: Python-based 2D map rendering using matplotlib and NetworkX
2. **Backend API Layer**: FastAPI REST API providing system data, risk analysis, and route calculation

Both layers integrate with EVE Online's ESI (External Services Interface) API for real-time game data.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │  Python Script   │              │   Web Browser    │        │
│  │  (matplotlib)    │              │  (Swagger UI)    │        │
│  └────────┬─────────┘              └────────┬─────────┘        │
│           │                                  │                  │
└───────────┼──────────────────────────────────┼──────────────────┘
            │                                  │
            │                                  │ HTTP/REST
            │ Direct                           │
            │ Import                           │
            │                                  │
┌───────────▼──────────────────────────────────▼──────────────────┐
│                      Application Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────┐      ┌────────────────────────┐   │
│  │  Frontend Package      │      │   Backend API          │   │
│  │  (src/evemap)          │      │   (FastAPI)            │   │
│  │                        │      │                        │   │
│  │  ├─ ESIClient          │      │  ├─ /systems/*         │   │
│  │  ├─ NedenMap           │      │  ├─ /map/*             │   │
│  │  ├─ Models             │      │  └─ /health            │   │
│  │  └─ Utils              │      │                        │   │
│  └───────┬────────────────┘      └────────┬───────────────┘   │
│          │                                 │                   │
│          │                                 │                   │
└──────────┼─────────────────────────────────┼───────────────────┘
           │                                 │
           │                                 │
┌──────────▼─────────────────────────────────▼───────────────────┐
│                      Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │ Data Loader  │  │ Risk Engine  │  │ Routing Service│       │
│  │ (LRU Cache)  │  │              │  │  (Dijkstra)    │       │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘       │
│         │                 │                    │               │
│         └─────────────────┴────────────────────┘               │
│                           │                                    │
└───────────────────────────┼────────────────────────────────────┘
                            │
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                       Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ universe.json   │  │ risk_config.json │  │  ESI API     │  │
│  │ (Systems/Gates) │  │ (Risk Weights)   │  │  (CCP Games) │  │
│  └─────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## API Data Acquisition Pipeline

### ESI API Integration

The EVE Online ESI (External Services Interface) API provides real-time data about the game universe.

#### Data Flow

```
1. Client Request
   └─> ESIClient._make_request()
       └─> HTTP GET to https://esi.eveonline.com/latest/{endpoint}
           ├─> Retry Logic (exponential backoff)
           ├─> Rate Limiting (0.05-0.1s delays)
           └─> Response Parsing

2. Data Aggregation
   └─> get_region_data()
       ├─> Fetch Region Info
       │   └─> /universe/regions/{region_id}
       ├─> Fetch Constellations
       │   └─> /universe/constellations/{const_id} (batch)
       ├─> Fetch Systems
       │   └─> /universe/systems/{system_id} (batch)
       └─> Build Jump Connections
           └─> /universe/stargates/{gate_id} (batch)

3. Model Construction
   └─> System, Region, Constellation, JumpConnection objects
```

#### Key Endpoints Used

| Endpoint | Purpose | Rate Limit Handling |
|----------|---------|---------------------|
| `/universe/regions/{id}` | Get region metadata | 3 retries with exponential backoff |
| `/universe/constellations/{id}` | Get constellation data | 0.05s delay between requests |
| `/universe/systems/{id}` | Get system details | 0.1s delay between requests |
| `/universe/stargates/{id}` | Get gate connections | 0.05s delay between requests |

#### Error Handling

```python
def _make_request(self, endpoint: str, retries: int = 3):
    for attempt in range(retries):
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                return None  # All retries failed
```

### Backend Data Loading

The backend uses a simpler, file-based approach for faster responses:

```
1. JSON File Storage
   └─> backend/app/data/
       ├─> universe.json (systems and gates)
       └─> risk_config.json (risk parameters)

2. Data Loader Service
   └─> @lru_cache decorator for in-memory caching
       ├─> load_universe() → Universe model
       └─> load_risk_config() → RiskConfig model

3. API Endpoints
   └─> Access cached data instantly
       └─> No external API calls during request handling
```

## Caching Systems

### LRU Cache (Backend)

The backend uses Python's `functools.lru_cache` for efficient data loading:

```python
@lru_cache(maxsize=1)
def load_universe() -> Universe:
    """Load universe data from JSON file."""
    universe_file = DATA_DIR / "universe.json"
    with open(universe_file, "r") as f:
        data = json.load(f)
    return Universe(**data)
```

**Benefits:**
- First call: Reads from disk and caches in memory
- Subsequent calls: Returns cached object instantly
- Memory efficient: Only 1 copy in memory (maxsize=1)
- Thread-safe: Built-in locking mechanism

**Cache Invalidation:**
- Automatic: When process restarts
- Manual: Not implemented (static data)
- Future: Could add file modification time checking

### Session Caching (Frontend ESIClient)

The ESI client uses `requests.Session` for connection pooling:

```python
def __init__(self, timeout: int = 10):
    self.session = requests.Session()
    self.session.headers.update({"User-Agent": self.USER_AGENT})
```

**Benefits:**
- Connection reuse: Faster subsequent requests
- Header persistence: User-Agent sent automatically
- Cookie handling: Session management if needed

## FastAPI Backend Architecture

### Application Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   └── config.py        # Configuration settings
│   ├── api/
│   │   ├── routes_systems.py   # /systems/* endpoints
│   │   └── routes_map.py       # /map/* endpoints
│   ├── models/
│   │   ├── system.py        # System, Gate, Universe models
│   │   ├── risk.py          # RiskConfig, RiskReport models
│   │   └── route.py         # RouteResponse, RouteHop models
│   ├── services/
│   │   ├── data_loader.py   # JSON data loading with cache
│   │   ├── risk_engine.py   # Risk calculation logic
│   │   ├── routing.py       # Dijkstra pathfinding
│   │   └── zkill_client.py  # zKillboard integration (stub)
│   └── data/
│       ├── universe.json    # System and gate data
│       └── risk_config.json # Risk weights and profiles
```

### Request Flow

```
1. HTTP Request
   └─> FastAPI Router
       └─> Route Handler (@router.get)
           ├─> Parameter Validation (Pydantic)
           ├─> Service Layer Call
           │   ├─> Data Loader (cached)
           │   ├─> Risk Engine / Routing
           │   └─> Response Model Construction
           └─> JSON Response (Pydantic serialization)

Example: GET /map/route?from=Jita&to=Niarja&profile=safer

FastAPI
└─> routes_map.calculate_route(from="Jita", to="Niarja", profile="safer")
    ├─> routing.calculate_route_with_profile()
    │   ├─> load_universe() [CACHED]
    │   ├─> load_risk_config() [CACHED]
    │   ├─> _build_graph() [compute risk weights]
    │   └─> _dijkstra() [find optimal path]
    └─> RouteResponse(path=[...], total_risk=...)
        └─> JSON: {"path": [...], "total_risk": ...}
```

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Considerations:**
- Restrict `allow_origins` to specific domains
- Enable authentication for sensitive endpoints
- Rate limiting for public APIs

## Visualization Rendering Pipeline

### Graph Construction

```
1. System Data Input
   └─> Dictionary of System objects
       └─> {system_id: System(...)}

2. NetworkX Graph Building
   └─> NedenMap._build_graph()
       ├─> Add nodes (systems)
       │   └─> G.add_node(system_id, system=system)
       └─> Add edges (jump connections)
           └─> G.add_edge(source_id, target_id, distance=distance)

3. Layout Calculation
   └─> calculate_layout(method="spring")
       ├─> nx.spring_layout() [force-directed]
       │   └─> Iterative optimization (50-100 iterations)
       ├─> nx.kamada_kawai_layout() [physics-based]
       ├─> nx.circular_layout() [circular arrangement]
       └─> nx.shell_layout() [concentric shells]
       
4. Position Assignment
   └─> Update System.x and System.y
       └─> self.systems[system_id].x = x
           self.systems[system_id].y = y
```

### Rendering Pipeline

```
1. Figure Initialization
   └─> plt.subplots(figsize=(20, 16), dpi=100)

2. Draw Edges (Jump Connections)
   └─> For each connection:
       ├─> Get source and target positions
       └─> ax.plot([x0, x1], [y0, y1], color='gray', alpha=0.3)

3. Draw Nodes (Systems)
   └─> Group by security status or region/constellation
       └─> For each group:
           ├─> Extract positions
           ├─> Select color (security-based or group-based)
           └─> ax.scatter(x_pos, y_pos, c=color, s=100)

4. Draw Labels
   └─> For each system:
       └─> ax.text(x, y, name, bbox=dict(...))

5. Add Legend
   └─> Create legend elements
       └─> ax.legend(handles=[...])

6. Save/Display
   └─> fig.savefig(filename, dpi=150, bbox_inches='tight')
       OR
       plt.show()
```

### Color Schemes

```python
SECURITY_COLORS = {
    SecurityStatus.HIGH_SEC: '#3366FF',    # Blue
    SecurityStatus.LOW_SEC: '#FF9900',     # Orange
    SecurityStatus.NULL_SEC: '#FF0000',    # Red
    SecurityStatus.WORMHOLE: '#9933FF',    # Purple
}
```

## Data Models

### Pydantic Models (Backend)

Using Pydantic v1.x for data validation:

```python
# System Model
class System(BaseModel):
    name: str
    security_status: float
    region: str
    constellation: Optional[str] = None

# Universe Model
class Universe(BaseModel):
    systems: Dict[str, System]  # typing.Dict for Python <3.10
    gates: List[Gate]           # typing.List for Python <3.10

# Risk Report Model
class RiskReport(BaseModel):
    system: str
    risk_score: float
    classification: str
    factors: Dict[str, float]
```

**Type Annotation Strategy:**
- Use `typing.Dict` instead of `dict[...]` (PEP 585)
- Use `typing.List` instead of `list[...]` (PEP 585)
- Use `typing.Optional` instead of `... | None` (PEP 604)
- Ensures compatibility with Python 3.9+

### Dataclass Models (Frontend)

Using Python dataclasses for lightweight models:

```python
@dataclass
class System:
    system_id: int
    name: str
    region_id: int
    constellation_id: int
    security_status: float
    security_class: SecurityStatus
    x: float = 0.0
    y: float = 0.0
```

## Performance Considerations

### Backend Optimizations

1. **LRU Caching**
   - Eliminates repeated file I/O
   - Reduces JSON parsing overhead
   - Memory footprint: ~1MB for typical universe data

2. **Graph Pre-computation**
   - Risk-weighted graph built once per request
   - O(V + E) complexity for graph construction
   - V = number of systems, E = number of gates

3. **Dijkstra's Algorithm**
   - O((V + E) log V) with priority queue
   - Efficient for sparse graphs (EVE universe)
   - Typical route calculation: <10ms

### Frontend Optimizations

1. **Layout Calculation**
   - Spring layout: O(iterations × E)
   - Kamada-Kawai: O(V²)
   - Cached after first calculation

2. **Rendering**
   - Vectorized operations with NumPy
   - Batch scatter plots by group
   - Lazy evaluation with matplotlib

### Scalability Limits

| Component | Current Limit | Recommended Maximum |
|-----------|--------------|---------------------|
| Systems in universe | ~100 | ~1,000 |
| Connections per request | ~200 | ~2,000 |
| Layout iterations | 50-100 | 200 |
| Concurrent API requests | Unlimited | Add rate limiting |

### Implemented Optimizations

1. **Database Integration** ✅
   - PostgreSQL support with SQLite fallback
   - Configured via `POSTGRES_URL` environment variable
   - Docker Compose includes PostgreSQL service

2. **Redis Caching** ✅
   - `RedisCacheService` with async Redis support
   - Auto-detects via `REDIS_URL`, falls back to memory cache
   - TTL-based invalidation per endpoint type

3. **Async ESI Client** ✅
   - `httpx.AsyncClient` with semaphore-based concurrency control
   - Automatic retry with exponential backoff (tenacity)
   - ESI error limit header tracking

4. **WebSocket Support** ✅
   - Real-time kill feed via `/api/v1/ws/killfeed`
   - System/region subscription filters
   - Connection manager for broadcast

5. **Rate Limiting** ✅
   - `slowapi` middleware (100 req/min per IP by default)
   - API key support for higher limits
   - Proper 429 responses with Retry-After headers

### Future Enhancements

1. **Real-time map updates via WebSocket**
   - Live risk score changes
   - Collaborative routing sessions

2. **Pub/sub for cache invalidation**
   - Redis pub/sub for multi-instance deployments

## Security Considerations

### API Security

1. **Input Validation**
   - Pydantic models validate all inputs
   - Type checking prevents injection attacks
   - String sanitization for system names

2. **Rate Limiting**
   - Implemented via `slowapi` middleware
   - Default: 100 requests/minute per IP
   - API key support for differentiated limits
   - Configurable via `RATE_LIMIT_ENABLED` and `RATE_LIMIT_PER_MINUTE`

3. **CORS Configuration**
   - Current: Allow all origins (development)
   - Production: Restrict to specific domains
   - Credential handling: Disabled by default

### Data Privacy

1. **No User Data**
   - No authentication required
   - No personal information stored
   - Public game data only

2. **ESI API Key**
   - Not required for current endpoints
   - Future: OAuth2 for authenticated endpoints
   - Store securely in environment variables

## Monitoring and Logging

### Health Checks

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

**Future Enhancements:**
- Database connectivity check
- External API availability
- Cache hit/miss rates

### Logging

Current: Basic print statements
Recommended: Structured logging with `logging` module

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Route calculated", extra={
    "from": source,
    "to": destination,
    "distance": len(path),
    "risk": total_risk
})
```

## Deployment

### Development

```bash
uvicorn app.main:app --reload
```

### Production

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### Cloud Deployment

**Recommended Platforms:**
- **AWS Lambda** with Mangum adapter
- **Google Cloud Run** (containerized)
- **Heroku** with Procfile
- **DigitalOcean App Platform**

## Conclusion

This architecture provides:
- ✅ Separation of concerns (frontend/backend)
- ✅ Efficient caching for performance
- ✅ Extensible design for new features
- ✅ Type safety with Pydantic
- ✅ RESTful API design
- ✅ Real-time data integration

Future enhancements can build on this foundation while maintaining backward compatibility.

---

For questions or contributions, see [CONTRIBUTING.md](CONTRIBUTING.md).
