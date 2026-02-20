# Deployment Guide

This guide covers deploying EVE Gatekeeper in various environments.

## Docker Deployment (Recommended)

### Prerequisites
- Docker 20.10+
- Docker Compose v2+

### Quick Start

```bash
# Clone and enter directory
git clone https://github.com/Arete-Consortium/EVE_Gatekeeper.git
cd EVE_Gatekeeper

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start services
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8000/health
```

### Production Configuration

Edit `.env` for production:

```env
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
SECRET_KEY=your-secure-random-key
POSTGRES_URL=postgresql://user:pass@postgres:5432/eve_gatekeeper
REDIS_URL=redis://redis:6379
RATE_LIMIT_ENABLED=true
```

### Scaling

```bash
# Scale API containers
docker-compose up -d --scale eve-gatekeeper=3
```

Note: When scaling, use an external load balancer (nginx, traefik) and shared Redis for WebSocket state.

## Manual Deployment

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (optional but recommended)
- Redis 7+ (optional)

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./eve_gatekeeper.db
export LOG_LEVEL=INFO
```

### Running with Gunicorn

```bash
pip install gunicorn

gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Systemd Service

Create `/etc/systemd/system/eve-gatekeeper.service`:

```ini
[Unit]
Description=EVE Gatekeeper API
After=network.target

[Service]
User=gatekeeper
WorkingDirectory=/opt/eve-gatekeeper
Environment=PATH=/opt/eve-gatekeeper/venv/bin
EnvironmentFile=/opt/eve-gatekeeper/.env
ExecStart=/opt/eve-gatekeeper/venv/bin/gunicorn \
  backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable eve-gatekeeper
sudo systemctl start eve-gatekeeper
```

## Cloud Deployment

### Railway

1. Connect your GitHub repository
2. Add environment variables in Railway dashboard
3. Railway auto-detects Dockerfile

### Fly.io

Create `fly.toml`:

```toml
app = "eve-gatekeeper"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true

[[services.ports]]
  handlers = ["http"]
  port = 80

[[services.ports]]
  handlers = ["tls", "http"]
  port = 443

[env]
  LOG_LEVEL = "INFO"
  LOG_FORMAT = "json"
```

```bash
flyctl launch
flyctl secrets set SECRET_KEY=your-secret
flyctl deploy
```

### AWS ECS

Use the provided Dockerfile with:
- Application Load Balancer
- ECS Fargate or EC2
- RDS PostgreSQL
- ElastiCache Redis

## Reverse Proxy Configuration

### Nginx

```nginx
upstream gatekeeper {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name gatekeeper.example.com;

    ssl_certificate /etc/ssl/certs/gatekeeper.crt;
    ssl_certificate_key /etc/ssl/private/gatekeeper.key;

    location / {
        proxy_pass http://gatekeeper;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/ws/ {
        proxy_pass http://gatekeeper;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

## Health Checks

The `/health` endpoint returns:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-01T00:00:00Z",
  "checks": {
    "database": "ok",
    "cache": "memory",
    "esi": "unknown"
  }
}
```

Use this for:
- Container orchestration (Docker, Kubernetes)
- Load balancer health checks
- Monitoring systems

## Monitoring

### Prometheus

Scrape `/metrics` endpoint:

```yaml
scrape_configs:
  - job_name: 'eve-gatekeeper'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana

Import dashboard or create panels for:
- `http_requests_total` - Request rate
- `http_request_duration_seconds` - Latency
- `cache_hits_total` / `cache_misses_total` - Cache efficiency
- `websocket_connections_active` - Active connections

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs eve-gatekeeper

# Common issues:
# - Missing .env file
# - Database connection failure
# - Port already in use
```

### WebSocket connections dropping

- Check proxy timeout settings
- Ensure WebSocket upgrade headers are passed
- Monitor `websocket_connections_active` metric

### High memory usage

- Reduce cache TTL values
- Check for memory leaks in logs
- Consider using Redis instead of in-memory cache
