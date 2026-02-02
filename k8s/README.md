# EVE Gatekeeper Kubernetes Deployment

This directory contains Kubernetes manifests for deploying EVE Gatekeeper.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Ingress Controller (nginx-ingress recommended)
- Storage provisioner for PersistentVolumes

## Quick Start

```bash
# 1. Create the namespace and base resources
kubectl apply -k .

# 2. Update secrets with real values
kubectl create secret generic eve-gatekeeper-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -base64 32) \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 16) \
  -n eve-gatekeeper \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Build and push the Docker image
docker build -t your-registry/eve-gatekeeper:latest ..
docker push your-registry/eve-gatekeeper:latest

# 4. Update the image in kustomization.yaml or use:
kubectl set image deployment/eve-gatekeeper \
  eve-gatekeeper=your-registry/eve-gatekeeper:latest \
  -n eve-gatekeeper

# 5. Check deployment status
kubectl get pods -n eve-gatekeeper
kubectl get svc -n eve-gatekeeper
```

## Components

| Component | Type | Description |
|-----------|------|-------------|
| eve-gatekeeper | Deployment | API server (2+ replicas) |
| postgres | StatefulSet | PostgreSQL database |
| redis | Deployment | Redis cache/pub-sub |

## Configuration

### ConfigMap (configmap.yaml)

Non-sensitive configuration values. Edit directly or override with kustomize.

### Secrets (secret.yaml)

Sensitive values. **Never commit real secrets!**

Required secrets:
- `SECRET_KEY`: Application secret key (min 32 chars)
- `POSTGRES_PASSWORD`: PostgreSQL password

Optional secrets:
- `ESI_CLIENT_ID`: EVE SSO client ID
- `ESI_SECRET_KEY`: EVE SSO secret
- `DISCORD_WEBHOOK_URL`: Discord webhook for alerts
- `SENTRY_DSN`: Sentry error tracking

### Ingress (ingress.yaml)

Update the host to match your domain:
```yaml
spec:
  rules:
    - host: api.your-domain.com
```

For TLS, uncomment the tls section and ensure cert-manager is configured.

## Scaling

The HPA automatically scales between 2-10 replicas based on CPU/memory.

Manual scaling:
```bash
kubectl scale deployment/eve-gatekeeper --replicas=5 -n eve-gatekeeper
```

## Monitoring

Prometheus metrics available at `/metrics` on each pod.

Annotations enable automatic scraping:
```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

## Health Checks

- Liveness: `/health` - restarts unhealthy pods
- Readiness: `/health` - removes from load balancer if failing

## Troubleshooting

```bash
# View pod logs
kubectl logs -f deployment/eve-gatekeeper -n eve-gatekeeper

# Check pod status
kubectl describe pod -l app.kubernetes.io/name=eve-gatekeeper -n eve-gatekeeper

# Access pod shell
kubectl exec -it deployment/eve-gatekeeper -n eve-gatekeeper -- /bin/bash

# Check database connectivity
kubectl exec -it postgres-0 -n eve-gatekeeper -- psql -U gatekeeper -d eve_gatekeeper -c '\dt'

# Check Redis
kubectl exec -it deployment/redis -n eve-gatekeeper -- redis-cli ping
```

## Production Checklist

- [ ] Update `secret.yaml` with real credentials (or use external secrets)
- [ ] Configure TLS in `ingress.yaml`
- [ ] Update `ingress.yaml` host to your domain
- [ ] Set resource limits appropriate for your workload
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up monitoring and alerting
- [ ] Review and adjust HPA settings
