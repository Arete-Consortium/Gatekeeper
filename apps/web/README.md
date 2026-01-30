# EVE Gatekeeper Web Frontend

Next.js web application for EVE Gatekeeper - an EVE Online route planning and intel tool.

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run production build locally
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Configuration

Create a `.env.local` file based on `.env.example`:

```bash
cp .env.example .env.local
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Deployment

### Docker

Build and run using Docker:

```bash
# Build the image
docker build -t eve-gatekeeper-web .

# Run the container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://your-api-server:8000 \
  eve-gatekeeper-web
```

### Docker Compose

For easier deployment with environment configuration:

```bash
# Set your API URL
export NEXT_PUBLIC_API_URL=http://your-api-server:8000

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop
docker-compose down
```

### Health Check

The application exposes a health check endpoint at `/api/health` which returns:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T12:00:00.000Z"
}
```

### Production Notes

- The Docker image uses a multi-stage build to minimize image size
- The application runs as a non-root user for security
- Standalone output mode is enabled for optimal Docker deployment
- Health checks are configured with a 30s interval

## Project Structure

```
src/
  app/           # Next.js App Router pages
    api/         # API routes (health check)
    alerts/      # Alert subscriptions page
    fitting/     # Fitting analyzer page
    intel/       # Intel feed page
    settings/    # Settings page
  components/    # React components
    ui/          # Base UI components
    system/      # System-related components
    route/       # Route planning components
    fitting/     # Fitting analysis components
    alerts/      # Alert management components
    layout/      # Layout components
  hooks/         # Custom React hooks
  lib/           # Utilities and API client
  styles/        # Global styles
```
