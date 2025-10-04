#!/bin/bash
# Kubernetes Deployment Script for FlashStudio
# This script deploys FlashStudio with Stripe payment integration to Kubernetes

set -e

echo "🚀 FlashStudio Kubernetes Deployment Script"
echo "==========================================="

# Configuration
NAMESPACE="flash"
IMAGE_TAG="v2"
ACR_NAME="flashstudiomain.azurecr.io"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    print_success "kubectl is available"
}

# Function to check if namespace exists
check_namespace() {
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        print_success "Namespace '$NAMESPACE' exists"
    else
        print_status "Creating namespace '$NAMESPACE'..."
        kubectl create namespace $NAMESPACE
        print_success "Namespace '$NAMESPACE' created"
    fi
}

# Function to create secrets
create_secrets() {
    print_status "Creating Kubernetes secrets..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found. Please create it with your configuration."
        exit 1
    fi
    
    # Source environment variables from .env file
    export $(cat .env | grep -v '^#' | xargs)
    
    # Validate required variables
    if [ -z "$STRIPE_PUBLISHABLE_KEY" ] || [ "$STRIPE_PUBLISHABLE_KEY" = "pk_test_your_publishable_key_here" ]; then
        print_error "STRIPE_PUBLISHABLE_KEY is not configured in .env file"
        exit 1
    fi
    
    if [ -z "$STRIPE_SECRET_KEY" ] || [ "$STRIPE_SECRET_KEY" = "sk_test_your_secret_key_here" ]; then
        print_error "STRIPE_SECRET_KEY is not configured in .env file"
        exit 1
    fi
    
    # Create or update Stripe secrets
    kubectl create secret generic stripe-secrets \
        --from-literal=STRIPE_PUBLISHABLE_KEY="$STRIPE_PUBLISHABLE_KEY" \
        --from-literal=STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" \
        --from-literal=STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "Stripe secrets created/updated"
    
    # Create application secrets
    kubectl create secret generic flashstudio-secrets \
        --from-literal=FLASK_SECRET_KEY="$FLASK_SECRET_KEY" \
        --from-literal=DATABASE_URL="sqlite:///filmcompany.db" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "Application secrets created/updated"
    
    # Create Azure storage secrets (if configured)
    if [ ! -z "$AZURE_STORAGE_CONNECTION_STRING" ] && [ "$AZURE_STORAGE_CONNECTION_STRING" != "DefaultEndpointsProtocol=https;AccountName=devtest;AccountKey=test;EndpointSuffix=core.windows.net" ]; then
        kubectl create secret generic blob-conn \
            --from-literal=AZURE_STORAGE_CONNECTION_STRING="$AZURE_STORAGE_CONNECTION_STRING" \
            --namespace=$NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        print_success "Azure storage secrets created/updated"
    else
        print_warning "Using development Azure storage configuration"
        kubectl create secret generic blob-conn \
            --from-literal=AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=devtest;AccountKey=test;EndpointSuffix=core.windows.net" \
            --namespace=$NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
}

# Function to deploy application
deploy_application() {
    print_status "Deploying FlashStudio application..."
    
    # Update image tag in deployment
    sed "s|flashstudiomain\.azurecr\.io/flashstudio/monolith:v1|$ACR_NAME/flashstudio/monolith:$IMAGE_TAG|g" k8-deploy/deployment.yaml > /tmp/deployment-updated.yaml
    
    # Apply deployment
    kubectl apply -f /tmp/deployment-updated.yaml
    print_success "Deployment applied"
    
    # Apply service
    kubectl apply -f k8-deploy/service.yaml
    print_success "Service applied"
    
    # Clean up temp file
    rm /tmp/deployment-updated.yaml
}

# Function to check deployment status
check_deployment() {
    print_status "Checking deployment status..."
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/flashstudio-monolith -n $NAMESPACE
    
    print_success "Deployment is ready!"
    
    # Show pod status
    print_status "Pod status:"
    kubectl get pods -n $NAMESPACE
    
    # Show service status
    print_status "Service status:"
    kubectl get services -n $NAMESPACE
}

# Function to show access information
show_access_info() {
    print_success "🎉 FlashStudio deployed successfully!"
    echo ""
    print_status "Access Information:"
    
    # Get service information
    SERVICE_IP=$(kubectl get service flashstudio-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    SERVICE_PORT=$(kubectl get service flashstudio-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')
    
    if [ "$SERVICE_IP" = "pending" ] || [ -z "$SERVICE_IP" ]; then
        print_warning "External IP is still pending. Use port-forward for testing:"
        echo "  kubectl port-forward service/flashstudio-service 8080:80 -n $NAMESPACE"
        echo "  Then access: http://localhost:8080"
    else
        echo "  External URL: http://$SERVICE_IP:$SERVICE_PORT"
    fi
    
    echo ""
    print_status "Useful commands:"
    echo "  View logs: kubectl logs -f deployment/flashstudio-monolith -n $NAMESPACE"
    echo "  Get pods: kubectl get pods -n $NAMESPACE"
    echo "  Describe deployment: kubectl describe deployment flashstudio-monolith -n $NAMESPACE"
    echo "  Delete deployment: kubectl delete -f k8-deploy/ -n $NAMESPACE"
}

# Main execution
main() {
    print_status "Starting deployment process..."
    
    check_kubectl
    check_namespace
    create_secrets
    deploy_application
    check_deployment
    show_access_info
    
    print_success "Deployment completed successfully! 🎉"
}

# Run main function
main "$@"