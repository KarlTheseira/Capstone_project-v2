#!/bin/bash

# ====================================================
# FlashStudio AKS Deployment Script
# ====================================================

set -e  # Exit on any error

# Configuration Variables  
RESOURCE_GROUP="flashstudio-rg"
LOCATION="eastus"
AKS_CLUSTER_NAME="flashstudio-aks"
ACR_NAME="flashstudiomain"
APP_NAME="flashstudio"
NAMESPACE="flash"
NODE_COUNT=2

echo "🚀 Starting FlashStudio AKS Deployment..."
echo "================================================"

# Step 1: Login to Azure (if not already logged in)
echo "📋 Step 1: Azure Login"
if ! az account show >/dev/null 2>&1; then
    echo "Please log in to Azure:"
    az login
else
    echo "✅ Already logged in to Azure"
fi

# Show current subscription
echo "Current subscription:"
az account show --query "[name, id]" -o table

# Step 2: Create Resource Group
echo ""
echo "📋 Step 2: Creating Resource Group"
if az group show --name $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✅ Resource group '$RESOURCE_GROUP' already exists"
else
    echo "Creating resource group '$RESOURCE_GROUP'..."
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo "✅ Resource group created"
fi

# Step 3: Create Azure Container Registry
echo ""
echo "📋 Step 3: Creating Azure Container Registry"
if az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✅ ACR '$ACR_NAME' already exists"
else
    echo "Creating Azure Container Registry '$ACR_NAME'..."
    az acr create --resource-group $RESOURCE_GROUP \
                  --name $ACR_NAME \
                  --sku Basic \
                  --admin-enabled true
    echo "✅ ACR created"
fi

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Step 4: Create AKS Cluster
echo ""
echo "📋 Step 4: Creating AKS Cluster"
if az aks show --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✅ AKS cluster '$AKS_CLUSTER_NAME' already exists"
else
    echo "Creating AKS cluster '$AKS_CLUSTER_NAME'... (this may take 10-15 minutes)"
    az aks create \
        --resource-group $RESOURCE_GROUP \
        --name $AKS_CLUSTER_NAME \
        --node-count $NODE_COUNT \
        --node-vm-size Standard_B2s \
        --attach-acr $ACR_NAME \
        --generate-ssh-keys \
        --enable-managed-identity \
        --network-plugin azure
    echo "✅ AKS cluster created"
fi

# Step 5: Get AKS credentials
echo ""
echo "📋 Step 5: Configuring kubectl"
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME --overwrite-existing
echo "✅ kubectl configured for AKS cluster"

# Step 6: Build and Push Docker Image to ACR
echo ""
echo "📋 Step 6: Building and Pushing Docker Image"
echo "Logging into ACR..."
az acr login --name $ACR_NAME

# Tag and push the image
IMAGE_TAG="$ACR_LOGIN_SERVER/$APP_NAME:latest"
echo "Building Docker image with tag: $IMAGE_TAG"
docker build -t $IMAGE_TAG .

echo "Pushing image to ACR..."
docker push $IMAGE_TAG
echo "✅ Docker image pushed to ACR"

# Step 7: Create namespace and update Kubernetes manifests  
echo ""
echo "📋 Step 7: Creating namespace and updating manifests"

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create temporary deployment file with correct image
sed "s|flashstudiomain\.azurecr\.io/flashstudio/monolith:latest|$IMAGE_TAG|g" k8-deploy/deployment.yaml > /tmp/deployment-updated.yaml

echo "✅ Namespace created and Kubernetes manifests updated"

# Step 8: Create Kubernetes Secrets
echo ""
echo "📋 Step 8: Creating Kubernetes Secrets"

# Check if secrets already exist in the correct namespace
if kubectl get secret flashstudio-secrets -n $NAMESPACE >/dev/null 2>&1; then
    echo "✅ FlashStudio secrets already exist"
else
    echo "Creating flashstudio-secrets..."
    kubectl create secret generic flashstudio-secrets \
        --from-literal=DATABASE_URL="sqlite:///filmcompany.db" \
        --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
        --namespace=$NAMESPACE
    echo "✅ FlashStudio secrets created"
fi

if kubectl get secret stripe-secrets -n $NAMESPACE >/dev/null 2>&1; then
    echo "✅ Stripe secrets already exist"
else
    echo "⚠️  Creating placeholder Stripe secrets (you need to update these with real values)"
    kubectl create secret generic stripe-secrets \
        --from-literal=STRIPE_PUBLISHABLE_KEY="pk_test_replace_with_your_key" \
        --from-literal=STRIPE_SECRET_KEY="sk_test_replace_with_your_key" \
        --from-literal=STRIPE_WEBHOOK_SECRET="whsec_replace_with_your_secret" \
        --namespace=$NAMESPACE
    echo "✅ Placeholder Stripe secrets created"
fi

if kubectl get secret google-drive-secrets -n $NAMESPACE >/dev/null 2>&1; then
    echo "✅ Google Drive secrets already exist"
else
    echo "⚠️  Creating placeholder Google Drive secrets (you need to update these)"
    kubectl create secret generic google-drive-secrets \
        --from-literal=GOOGLE_DRIVE_CREDENTIALS_JSON='{"type":"service_account","project_id":"replace-me"}' \
        --from-literal=GOOGLE_DRIVE_FOLDER_ID="replace_with_folder_id" \
        --namespace=$NAMESPACE
    echo "✅ Placeholder Google Drive secrets created"
fi

# Step 9: Deploy to AKS
echo ""
echo "📋 Step 9: Deploying to AKS"
echo "Applying Kubernetes manifests..."

kubectl apply -f /tmp/deployment-updated.yaml
kubectl apply -f k8-deploy/service.yaml

echo "✅ Application deployed to AKS"

# Step 10: Wait for deployment and get status
echo ""
echo "📋 Step 10: Checking Deployment Status"
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=flashstudio-monolith -n $NAMESPACE --timeout=300s

# Get service information
echo ""
echo "🎉 Deployment Complete!"
echo "================================================"
echo "Cluster Information:"
kubectl get nodes -o wide

echo ""
echo "Application Status:"
kubectl get pods -l app=flashstudio-monolith -n $NAMESPACE
kubectl get services -n $NAMESPACE

# Get external IP (if LoadBalancer)
EXTERNAL_IP=$(kubectl get service flashstudio-lb -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
if [ "$EXTERNAL_IP" != "Pending" ] && [ "$EXTERNAL_IP" != "" ]; then
    echo ""
    echo "🌐 Your application will be available at: http://$EXTERNAL_IP"
else
    echo ""
    echo "🌐 External IP is pending. Check status with:"
    echo "   kubectl get service flashstudio-lb -n $NAMESPACE -w"
fi

echo ""
echo "📋 Useful Commands:"
echo "   View pods: kubectl get pods -n $NAMESPACE"
echo "   View services: kubectl get services -n $NAMESPACE"
echo "   View logs: kubectl logs -l app=flashstudio-monolith -n $NAMESPACE"
echo "   Port forward (for testing): kubectl port-forward svc/flashstudio-lb 8080:80 -n $NAMESPACE"

# Cleanup temporary file
rm -f /tmp/deployment-updated.yaml

echo ""
echo "✅ FlashStudio successfully deployed to AKS!"