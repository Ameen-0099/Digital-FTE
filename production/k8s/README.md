# NexusFlow Customer Success Digital FTE - Production Deployment

Complete production deployment configuration for the NexusFlow Digital FTE on Kubernetes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                    │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   API Pods (3)  │  │  Worker Pods(2) │  │    Ingress      │                 │
│  │   FastAPI       │  │  Kafka Consumer │  │    NGINX        │                 │
│  │   :8000         │  │  AI Agent       │  │    TLS          │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                           │
│           └────────────────────┼────────────────────┘                           │
│                                │                                                │
│           ┌────────────────────┼────────────────────┐                           │
│           │                    │                    │                           │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐                 │
│  │   PostgreSQL    │  │     Kafka       │  │   ConfigMap     │                 │
│  │   pgvector      │  │   Zookeeper     │  │   Secrets       │                 │
│  │   :5432         │  │   :9092         │  │   Env Vars      │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Local Development (Docker Compose)

```bash
# Set environment variables
export OPENAI_API_KEY=sk-...

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Access API docs
open http://localhost:8000/docs

# Access Kafka UI
open http://localhost:8080
```

### Kubernetes Deployment

```bash
# 1. Build Docker image
docker build -t nexusflow-digital-fte:1.0.0 .

# 2. Create namespace and deploy
kubectl apply -f production/k8s/namespace.yaml
kubectl apply -f production/k8s/configmap.yaml

# 3. Create secrets (update with real values)
kubectl create secret generic digital-fte-secrets \
  --from-literal=DATABASE_PASSWORD='your-password' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=TWILIO_ACCOUNT_SID='AC...' \
  --from-literal=TWILIO_AUTH_TOKEN='...' \
  -n digital-fte

# 4. Deploy infrastructure
kubectl apply -f production/k8s/postgres.yaml
kubectl apply -f production/k8s/kafka.yaml

# 5. Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=postgres -n digital-fte --timeout=120s
kubectl wait --for=condition=ready pod -l app=kafka -n digital-fte --timeout=120s

# 6. Deploy application
kubectl apply -f production/k8s/deployment.yaml
kubectl apply -f production/k8s/worker.yaml
kubectl apply -f production/k8s/ingress.yaml

# 7. Verify deployment
kubectl get pods -n digital-fte
kubectl get services -n digital-fte

# 8. Access API
kubectl port-forward svc/digital-fte-api-service 8000:80 -n digital-fte
open http://localhost:8000/docs
```

## Files Overview

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for production container |
| `docker-compose.yml` | Local development environment |
| `requirements.txt` | Python dependencies |
| `deploy.sh` | Automated deployment script |
| `production/k8s/namespace.yaml` | Kubernetes namespace with quotas |
| `production/k8s/configmap.yaml` | Environment configuration |
| `production/k8s/postgres.yaml` | PostgreSQL with pgvector |
| `production/k8s/kafka.yaml` | Kafka + Zookeeper |
| `production/k8s/deployment.yaml` | FastAPI API deployment |
| `production/k8s/worker.yaml` | Agent Worker deployment |
| `production/k8s/ingress.yaml` | External access with TLS |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `kafka-service:9092` |
| `KAFKA_TOPIC` | Kafka topic for messages | `customer-support-tickets` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4-turbo-preview` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

### Resource Allocation

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| API Pod | 250m | 1000m | 512Mi | 2Gi |
| Worker Pod | 500m | 2000m | 1Gi | 4Gi |
| PostgreSQL | 500m | 2000m | 1Gi | 4Gi |
| Kafka | 500m | 2000m | 1Gi | 4Gi |

### Auto-Scaling

| Component | Min Replicas | Max Replicas | CPU Target | Memory Target |
|-----------|--------------|--------------|------------|---------------|
| API | 2 | 10 | 70% | 80% |
| Worker | 1 | 8 | 70% | 80% |

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Logs

```bash
# API logs
kubectl logs -f -l app=digital-fte-api -n digital-fte

# Worker logs
kubectl logs -f -l app=digital-fte-worker -n digital-fte

# PostgreSQL logs
kubectl logs -l app=postgres -n digital-fte

# Kafka logs
kubectl logs -l app=kafka -n digital-fte
```

## Troubleshooting

### Pod not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n digital-fte

# Check logs
kubectl logs <pod-name> -n digital-fte
```

### Database connection issues

```bash
# Test database connection
kubectl exec -it <api-pod> -n digital-fte -- python -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://...'))"
```

### Kafka issues

```bash
# Check Kafka topics
kubectl exec -it <kafka-pod> -n digital-fte -- kafka-topics --bootstrap-server localhost:9092 --list
```

## Security Considerations

1. **Secrets**: Never commit secrets to git. Use Kubernetes secrets or external secret management.
2. **Network Policies**: Consider adding NetworkPolicy resources to restrict pod-to-pod communication.
3. **TLS**: Always use TLS for external access. The ingress.yaml includes cert-manager configuration.
4. **Resource Limits**: All pods have resource limits to prevent resource exhaustion.
5. **Non-root User**: The Dockerfile runs as a non-root user for security.

## Cost Optimization

1. **Auto-scaling**: HPA automatically scales based on CPU/memory usage.
2. **Spot Instances**: Consider using spot instances for worker pods.
3. **Resource Requests**: Right-size resource requests based on actual usage.
4. **Log Retention**: Configure log retention policies to reduce storage costs.
