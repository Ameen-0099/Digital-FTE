# NexusFlow Customer Success Digital FTE - Kubernetes Deployment Guide
# ======================================================================

# Quick Deploy Script
#!/bin/bash

set -e

echo "=================================================="
echo "NexusFlow Digital FTE - Kubernetes Deployment"
echo "=================================================="

# Configuration
NAMESPACE="digital-fte"
IMAGE_NAME="nexusflow-digital-fte"
IMAGE_TAG="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Build and push Docker image
build_image() {
    log_info "Building Docker image..."
    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
    log_info "Docker image built: ${IMAGE_NAME}:${IMAGE_TAG}"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: ${NAMESPACE}..."
    kubectl apply -f production/k8s/namespace.yaml
}

# Deploy ConfigMap and Secrets
deploy_config() {
    log_info "Deploying ConfigMap and Secrets..."
    kubectl apply -f production/k8s/configmap.yaml
    
    # Create secrets (update with real values)
    log_warn "Remember to update secrets with real values!"
    kubectl create secret generic digital-fte-secrets \
        --from-literal=DATABASE_PASSWORD='changeme' \
        --from-literal=OPENAI_API_KEY='sk-placeholder' \
        --from-literal=TWILIO_ACCOUNT_SID='AC-placeholder' \
        --from-literal=TWILIO_AUTH_TOKEN='placeholder' \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure (PostgreSQL, Kafka)..."
    kubectl apply -f production/k8s/postgres.yaml
    kubectl apply -f production/k8s/kafka.yaml
    
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=120s
    
    log_info "Waiting for Kafka to be ready..."
    kubectl wait --for=condition=ready pod -l app=kafka -n ${NAMESPACE} --timeout=120s
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    kubectl apply -f production/k8s/deployment.yaml
    kubectl apply -f production/k8s/worker.yaml
    kubectl apply -f production/k8s/ingress.yaml
    
    log_info "Waiting for API to be ready..."
    kubectl wait --for=condition=ready pod -l app=digital-fte-api -n ${NAMESPACE} --timeout=120s
    
    log_info "Waiting for Worker to be ready..."
    kubectl wait --for=condition=ready pod -l app=digital-fte-worker -n ${NAMESPACE} --timeout=120s
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    echo ""
    echo "=== Pods ==="
    kubectl get pods -n ${NAMESPACE}
    
    echo ""
    echo "=== Services ==="
    kubectl get services -n ${NAMESPACE}
    
    echo ""
    echo "=== Deployments ==="
    kubectl get deployments -n ${NAMESPACE}
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    API_POD=$(kubectl get pods -l app=digital-fte-api -n ${NAMESPACE} -o jsonpath="{.items[0].metadata.name}")
    kubectl exec -n ${NAMESPACE} ${API_POD} -- curl -s http://localhost:8000/health | head -20
}

# Main deployment
main() {
    check_prerequisites
    build_image
    create_namespace
    deploy_config
    deploy_infrastructure
    deploy_application
    verify_deployment
    
    echo ""
    log_info "=================================================="
    log_info "Deployment Complete!"
    log_info "=================================================="
    echo ""
    echo "Access the API:"
    echo "  kubectl port-forward svc/digital-fte-api-service 8000:80 -n ${NAMESPACE}"
    echo "  http://localhost:8000/docs"
    echo ""
    echo "View logs:"
    echo "  kubectl logs -f -l app=digital-fte-api -n ${NAMESPACE}"
    echo "  kubectl logs -f -l app=digital-fte-worker -n ${NAMESPACE}"
    echo ""
}

# Run main function
main "$@"
