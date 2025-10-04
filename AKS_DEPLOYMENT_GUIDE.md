# FlashStudio AKS Deployment Guide

## 🚀 **Complete Guide: Deploying FlashStudio to Azure Kubernetes Service**

This guide will walk you through deploying your FlashStudio application to Azure Kubernetes Service (AKS) step by step.

---

## 📋 **Prerequisites**

✅ **Azure Account** with active subscription  
✅ **Azure CLI** installed and configured  
✅ **Docker** installed and working  
✅ **kubectl** (will be installed via Azure CLI)  
✅ **FlashStudio application** ready to deploy  

---

## 🎯 **Deployment Options**

### **Option 1: Automated Deployment (Recommended)**
Use the provided script for one-click deployment:
```bash
./deploy-to-aks.sh
```

### **Option 2: Manual Step-by-Step**
Follow the manual steps below for learning purposes.

---

## 🛠️ **Manual Deployment Steps**

### **Step 1: Login to Azure**

```bash
# Login to Azure (opens browser)
az login

# Verify your subscription
az account show
az account list --output table

# Set subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

### **Step 2: Create Resource Group**

```bash
# Set variables
export RESOURCE_GROUP="flashstudio-rg"
export LOCATION="eastus"
export AKS_CLUSTER_NAME="flashstudio-aks"
export ACR_NAME="flashstudioregistry"  # Must be globally unique

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### **Step 3: Create Azure Container Registry (ACR)**

```bash
# Create ACR
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Get ACR login server
export ACR_LOGIN_SERVER=$(az acr show \
    --name $ACR_NAME \
    --resource-group $RESOURCE_GROUP \
    --query loginServer \
    --output tsv)

echo "ACR Login Server: $ACR_LOGIN_SERVER"
```

### **Step 4: Create AKS Cluster**

```bash
# Create AKS cluster (takes 10-15 minutes)
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_CLUSTER_NAME \
    --node-count 2 \
    --node-vm-size Standard_B2s \
    --attach-acr $ACR_NAME \
    --generate-ssh-keys \
    --enable-managed-identity \
    --network-plugin azure

# Get AKS credentials for kubectl
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_CLUSTER_NAME \
    --overwrite-existing

# Verify kubectl connection
kubectl get nodes
```

### **Step 5: Build and Push Docker Image**

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build and tag image
export IMAGE_TAG="$ACR_LOGIN_SERVER/flashstudio:latest"
docker build -t $IMAGE_TAG .

# Push to ACR
docker push $IMAGE_TAG

# Verify image in ACR
az acr repository list --name $ACR_NAME --output table
```

### **Step 6: Create Kubernetes Secrets**

```bash
# Create secrets for environment variables
kubectl create secret generic flashstudio-secrets \
    --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
    --from-literal=ADMIN_USERNAME="admin" \
    --from-literal=ADMIN_PASSWORD="secure_admin_password_$(openssl rand -hex 4)" \
    --from-literal=STRIPE_PUBLISHABLE_KEY="pk_test_your_key_here" \
    --from-literal=STRIPE_SECRET_KEY="sk_test_your_key_here"

# Verify secrets
kubectl get secrets
```

### **Step 7: Update Kubernetes Manifests**

```bash
# Update deployment with your ACR image
sed "s|flashstudiomain\.azurecr\.io/flashstudio/monolith:v1|$IMAGE_TAG|g" \
    k8-deploy/deployment-simple.yaml > deployment-updated.yaml
```

### **Step 8: Deploy Application**

```bash
# Deploy to AKS
kubectl apply -f deployment-updated.yaml
kubectl apply -f k8-deploy/service-simple.yaml

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services
```

### **Step 9: Wait for External IP**

```bash
# Monitor service for external IP (may take a few minutes)
kubectl get service flashstudio-service -w

# Once you have an external IP, test the application
# (Replace with actual external IP)
curl http://EXTERNAL-IP/healthz
```

---

## 🔍 **Troubleshooting Commands**

### **Check Pod Status**
```bash
# View all pods
kubectl get pods

# Describe a specific pod
kubectl describe pod POD-NAME

# View pod logs
kubectl logs POD-NAME

# Follow pod logs
kubectl logs -f POD-NAME
```

### **Check Services**
```bash
# View all services
kubectl get services

# Describe service
kubectl describe service flashstudio-service
```

### **Debug Container Issues**
```bash
# Execute into running container
kubectl exec -it POD-NAME -- bash

# Port forward for local testing
kubectl port-forward service/flashstudio-service 8080:80
# Then access: http://localhost:8080
```

### **Check Events**
```bash
# View cluster events
kubectl get events --sort-by=.metadata.creationTimestamp

# View events for specific namespace
kubectl get events --field-selector involvedObject.name=flashstudio
```

---

## 🎯 **Post-Deployment Verification**

### **1. Check Application Health**
```bash
# Get external IP
EXTERNAL_IP=$(kubectl get service flashstudio-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$EXTERNAL_IP/healthz

# Should return: {"ok":true}
```

### **2. Access Admin Panel**
- URL: `http://EXTERNAL-IP/admin/login`
- Get admin password: `kubectl get secret flashstudio-secrets -o jsonpath='{.data.ADMIN_PASSWORD}' | base64 -d`

### **3. Test Core Functionality**
- Homepage: `http://EXTERNAL-IP`
- Services: `http://EXTERNAL-IP/services`
- Portfolio: `http://EXTERNAL-IP/portfolio`

---

## ⚙️ **Production Configurations**

### **1. Enable HTTPS with Cert-Manager**
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configure ingress with SSL (separate guide needed)
```

### **2. Set Up Monitoring**
```bash
# Install Azure Monitor for containers
az aks enable-addons -a monitoring -n $AKS_CLUSTER_NAME -g $RESOURCE_GROUP
```

### **3. Configure Autoscaling**
```bash
# Enable cluster autoscaler
az aks update \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_CLUSTER_NAME \
    --enable-cluster-autoscaler \
    --min-count 1 \
    --max-count 5
```

---

## 🔄 **Update Deployment**

### **When You Make Code Changes:**
```bash
# Build and push new image
docker build -t $ACR_LOGIN_SERVER/flashstudio:v2 .
docker push $ACR_LOGIN_SERVER/flashstudio:v2

# Update deployment
kubectl set image deployment/flashstudio flashstudio=$ACR_LOGIN_SERVER/flashstudio:v2

# Check rollout status
kubectl rollout status deployment/flashstudio
```

---

## 🧹 **Cleanup Resources**

### **Delete AKS Resources**
```bash
# Delete the entire resource group (removes everything)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

### **Or Delete Individual Components**
```bash
# Delete AKS cluster
az aks delete --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP --yes

# Delete ACR
az acr delete --name $ACR_NAME --resource-group $RESOURCE_GROUP --yes
```

---

## 📊 **Cost Optimization**

### **Development Setup (Lower Cost)**
- Node VM Size: `Standard_B2s` (2 vCPUs, 4 GB RAM)
- Node Count: 1-2 nodes
- ACR: Basic tier

### **Production Setup**
- Node VM Size: `Standard_D2s_v3` or higher
- Node Count: 3+ nodes with autoscaling
- ACR: Standard tier with geo-replication

---

## 🎉 **Success Indicators**

✅ **AKS cluster created and running**  
✅ **Docker image built and pushed to ACR**  
✅ **Application pods running without restarts**  
✅ **Service has external IP assigned**  
✅ **Health check endpoint responds correctly**  
✅ **Admin panel accessible with credentials**  

---

**Your FlashStudio application is now running on Azure Kubernetes Service!** 🚀

For production use, consider implementing additional security, monitoring, and backup strategies.