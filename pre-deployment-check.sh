#!/bin/bash

# ====================================================
# Pre-Deployment Verification Script
# ====================================================

echo "🔍 FlashStudio AKS Pre-Deployment Check"
echo "========================================"

# Check Azure CLI
echo "1. Checking Azure CLI..."
if command -v az &> /dev/null; then
    echo "✅ Azure CLI installed: $(az --version | head -n1)"
else
    echo "❌ Azure CLI not found. Please install it."
    exit 1
fi

# Check Docker
echo "2. Checking Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker installed: $(docker --version)"
    
    # Check if Docker is running
    if docker ps &> /dev/null; then
        echo "✅ Docker daemon is running"
    else
        echo "❌ Docker daemon not running. Please start Docker."
        exit 1
    fi
else
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

# Check kubectl
echo "3. Checking kubectl..."
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl installed: $(kubectl version --client --short 2>/dev/null)"
else
    echo "⚠️  kubectl not found. Will be configured via Azure CLI."
fi

# Check Dockerfile
echo "4. Checking application files..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile found"
else
    echo "❌ Dockerfile not found in current directory"
    exit 1
fi

if [ -f "k8-deploy/deployment-simple.yaml" ]; then
    echo "✅ Kubernetes deployment manifest found"
else
    echo "❌ Kubernetes manifests not found"
    exit 1
fi

# Test Docker build
echo "5. Testing Docker build..."
if docker build -t flashstudio-test . > /tmp/docker-build.log 2>&1; then
    echo "✅ Docker build successful"
    docker rmi flashstudio-test > /dev/null 2>&1
else
    echo "❌ Docker build failed. Check /tmp/docker-build.log for details"
    echo "Last few lines of build log:"
    tail -n 5 /tmp/docker-build.log
    exit 1
fi

# Check Azure login status
echo "6. Checking Azure authentication..."
if az account show &> /dev/null; then
    ACCOUNT=$(az account show --query "name" -o tsv)
    SUBSCRIPTION=$(az account show --query "id" -o tsv)
    echo "✅ Logged into Azure"
    echo "   Account: $ACCOUNT"
    echo "   Subscription: $SUBSCRIPTION"
else
    echo "⚠️  Not logged into Azure. Run 'az login' before deployment."
fi

echo ""
echo "🎯 Pre-deployment check complete!"
echo ""
echo "Next steps:"
if ! az account show &> /dev/null; then
    echo "1. Login to Azure: az login"
    echo "2. Run deployment: ./deploy-to-aks.sh"
else
    echo "1. Run deployment: ./deploy-to-aks.sh"
fi
echo "3. Monitor progress and wait for external IP"
echo "4. Test application at http://EXTERNAL-IP"

echo ""
echo "📚 For detailed instructions, see: AKS_DEPLOYMENT_GUIDE.md"