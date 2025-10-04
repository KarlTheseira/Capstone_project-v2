#!/bin/bash
# Setup script for Kubernetes deployment tools

echo "🔧 Installing Kubernetes deployment tools..."

# Install kubectl
echo "📦 Installing kubectl..."
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

echo "✅ kubectl installed"

# Verify installation
echo "🔍 Verifying installations..."
kubectl version --client
echo ""

echo "🎯 Next steps:"
echo "1. Configure kubectl to connect to your Kubernetes cluster:"
echo "   - For Azure AKS: az aks get-credentials --resource-group myResourceGroup --name myAKSCluster"
echo "   - For Google GKE: gcloud container clusters get-credentials cluster-name --zone zone-name"
echo "   - For AWS EKS: aws eks update-kubeconfig --region region-code --name cluster-name"
echo "   - For local cluster: Use your cluster's specific configuration"
echo ""
echo "2. Push your Docker image to a container registry:"
echo "   docker push flashstudiomain.azurecr.io/flashstudio/monolith:v2"
echo ""
echo "3. Run the deployment script:"
echo "   ./deploy.sh"
echo ""
echo "✨ Setup complete!"