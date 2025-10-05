# 🚀 FlashStudio Monolith Deployment to Azure Kubernetes Service

## Step-by-Step Guide Using Azure Portal

This guide will walk you through deploying your FlashStudio monolithic application to Azure Kubernetes Service (AKS) using the Azure Portal interface.

---

## 📋 **Prerequisites Checklist**

Before starting, ensure you have:
- ✅ Azure account with active subscription
- ✅ Your FlashStudio code ready in GitHub
- ✅ Docker installed locally (optional, for testing)
- ✅ Basic understanding of Kubernetes concepts

---

## 🎯 **STEP 1: Create Resource Group**

### 1.1 Access Azure Portal
1. Go to **https://portal.azure.com**
2. Sign in with your Azure account
3. Click **"Resource groups"** in the left sidebar (or search for it)

### 1.2 Create New Resource Group
1. Click **"+ Create"** button
2. Fill in the details:
   ```
   Subscription: [Your subscription]
   Resource group name: flashstudio-rg
   Region: East US (or your preferred region)
   ```
3. Click **"Review + Create"**
4. Click **"Create"**

**✅ Expected Result:** Resource group `flashstudio-rg` created

---

## 🐳 **STEP 2: Create Azure Container Registry (ACR)**

### 2.1 Navigate to Container Registries
1. In Azure Portal, search for **"Container registries"**
2. Click **"Container registries"** service
3. Click **"+ Create"**

### 2.2 Configure ACR Settings
```
Subscription: [Your subscription]
Resource group: flashstudio-rg
Registry name: flashstudiomain
Location: East US
SKU: Basic ($5/month)
Admin user: Enable ✅
```

### 2.3 Create Registry
1. Click **"Review + Create"**
2. Click **"Create"**
3. Wait 2-3 minutes for deployment to complete

**✅ Expected Result:** ACR created at `flashstudiomain.azurecr.io`

---

## ☸️ **STEP 3: Create Azure Kubernetes Service (AKS)**

### 3.1 Navigate to Kubernetes Services
1. Search for **"Kubernetes services"** in Azure Portal
2. Click **"Kubernetes services"**
3. Click **"+ Create"** → **"Create Kubernetes cluster"**

### 3.2 Configure Basic Settings
```
Subscription: [Your subscription]
Resource group: flashstudio-rg
Cluster preset configuration: Dev/Test
Kubernetes cluster name: flashstudio-aks
Region: East US
Availability zones: None
AKS pricing tier: Free
Kubernetes version: Default (latest stable)
Automatic upgrade: Disabled
Node security channel type: None
```

### 3.3 Configure Node Pool
```
Scale method: Manual
Node count: 2
Node size: Standard_B2s (2 vcpus, 4 GiB memory) - $30/month each
```

### 3.4 Configure Integration
1. Click **"Integration"** tab
2. **Container registry:** Select `flashstudiomain`
3. **Enable container insights:** Yes ✅
4. **Azure Policy:** Disabled

### 3.5 Create AKS Cluster
1. Click **"Review + Create"**
2. **Review the estimated cost** (should be ~$60-80/month for 2 nodes)
3. Click **"Create"**
4. **Wait 10-15 minutes** for cluster creation (grab a coffee! ☕)

**✅ Expected Result:** AKS cluster `flashstudio-aks` created and running

---

## 🔧 **STEP 4: Setup Local Tools (One-time setup)**

### 4.1 Install Azure CLI (if not installed)

**Windows:**
```powershell
# Download and run: https://aka.ms/installazurecliwindows
```

**macOS:**
```bash
brew install azure-cli
```

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### 4.2 Install kubectl (if not installed)
```bash
# Install via Azure CLI
az aks install-cli
```

### 4.3 Login to Azure
```bash
az login
```
This opens your browser for authentication.

**✅ Expected Result:** Local tools installed and authenticated

---

## 🔑 **STEP 5: Configure GitHub Secrets**

### 5.1 Get Azure Service Principal
In your terminal, run:
```bash
# Create service principal for GitHub Actions
az ad sp create-for-rbac \
  --name "flashstudio-github-actions" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/flashstudio-rg \
  --sdk-auth
```

**Copy the entire JSON output!**

### 5.2 Get ACR Login Server
```bash
az acr show --name flashstudiomain --resource-group flashstudio-rg --query loginServer --output tsv
```

### 5.3 Add GitHub Secrets
1. Go to your GitHub repository: **https://github.com/KarlTheseira/Capstone_project-v2**
2. Click **"Settings"** tab
3. Click **"Secrets and variables"** → **"Actions"**
4. Click **"New repository secret"** and add each:

```
Name: AZURE_CREDENTIALS
Value: [Paste the entire JSON from step 5.1]

Name: ACR_LOGIN_SERVER
Value: flashstudiomain.azurecr.io

Name: RESOURCE_GROUP
Value: flashstudio-rg

Name: AKS_CLUSTER_NAME
Value: flashstudio-aks

Name: NAMESPACE
Value: flash
```

**✅ Expected Result:** 5 secrets configured in GitHub repository

---

## 📦 **STEP 6: Connect to Your AKS Cluster**

### 6.1 Get AKS Credentials
```bash
az aks get-credentials \
  --resource-group flashstudio-rg \
  --name flashstudio-aks \
  --overwrite-existing
```

### 6.2 Verify Connection
```bash
# Test connection
kubectl get nodes

# Should show something like:
# NAME                                STATUS   ROLES   AGE   VERSION
# aks-nodepool1-12345678-vmss000000   Ready    agent   5m    v1.27.x
# aks-nodepool1-12345678-vmss000001   Ready    agent   5m    v1.27.x
```

**✅ Expected Result:** kubectl connected to your AKS cluster

---

## 🔐 **STEP 7: Create Kubernetes Secrets**

### 7.1 Create Namespace
```bash
kubectl create namespace flash
```

### 7.2 Create Application Secrets
```bash
# Database and basic app secrets
kubectl create secret generic flashstudio-secrets \
  --from-literal=DATABASE_URL="sqlite:///filmcompany.db" \
  --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
  --namespace=flash

# Stripe payment secrets (use your actual keys)
kubectl create secret generic stripe-secrets \
  --from-literal=STRIPE_PUBLISHABLE_KEY="pk_test_your_key_here" \
  --from-literal=STRIPE_SECRET_KEY="sk_test_your_key_here" \
  --from-literal=STRIPE_WEBHOOK_SECRET="whsec_your_secret_here" \
  --namespace=flash

# Google Drive secrets (use your actual credentials)
kubectl create secret generic google-drive-secrets \
  --from-literal=GOOGLE_DRIVE_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project"}' \
  --from-literal=GOOGLE_DRIVE_FOLDER_ID="your_folder_id" \
  --namespace=flash
```

### 7.3 Verify Secrets
```bash
kubectl get secrets -n flash
```

**✅ Expected Result:** Three secrets created in the `flash` namespace

---

## 🚀 **STEP 8: Deploy Application (Automated via GitHub)**

### 8.1 Trigger Deployment
```bash
# Navigate to your project directory
cd /path/to/FlashStudio-main

# Commit any changes and push
git add .
git commit -m "Deploy to AKS - Initial deployment"
git push origin main
```

### 8.2 Monitor GitHub Actions
1. Go to your GitHub repository
2. Click **"Actions"** tab
3. Watch the **"CI/CD - Flash Studio to AKS"** workflow
4. The workflow should:
   - ✅ Validate secrets
   - ✅ Build Docker image
   - ✅ Push to ACR
   - ✅ Deploy to AKS

**✅ Expected Result:** GitHub Actions successfully deploys your app

---

## 📊 **STEP 9: Monitor Deployment**

### 9.1 Check Pod Status
```bash
# Watch pods starting up
kubectl get pods -n flash -w

# Should show:
# NAME                                  READY   STATUS    RESTARTS   AGE
# flashstudio-monolith-xxxxxxxxx-xxxxx   1/1     Running   0          2m
# flashstudio-monolith-xxxxxxxxx-xxxxx   1/1     Running   0          2m
```

### 9.2 Check Service Status
```bash
# Get service information
kubectl get services -n flash

# Should show LoadBalancer with EXTERNAL-IP
```

### 9.3 Get Application URL
```bash
# Get external IP (may take 3-5 minutes)
kubectl get service flashstudio-lb -n flash
```

**✅ Expected Result:** Your app is running with a public IP address

---

## 🌐 **STEP 10: Access Your Application**

### 10.1 Get Public URL
Once the LoadBalancer has an EXTERNAL-IP:
```bash
# Example output:
# NAME              TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)        AGE
# flashstudio-lb    LoadBalancer   10.0.xxx.xxx   20.xxx.xxx.xxx   80:30xxx/TCP   5m
```

### 10.2 Test Your Application
1. Open browser to: **http://[EXTERNAL-IP]**
2. You should see your FlashStudio homepage
3. Test key functionality:
   - ✅ Homepage loads
   - ✅ Admin login works
   - ✅ Video management accessible
   - ✅ Payment flow functional

**✅ Expected Result:** FlashStudio monolith running successfully on AKS!

---

## 🔍 **STEP 11: Troubleshooting Commands**

If something goes wrong, use these commands:

### Check Pod Logs
```bash
# View application logs
kubectl logs -l app=flashstudio-monolith -n flash --tail=50

# Follow live logs
kubectl logs -l app=flashstudio-monolith -n flash -f
```

### Check Pod Status
```bash
# Detailed pod information
kubectl describe pods -n flash

# Check events
kubectl get events -n flash --sort-by=.metadata.creationTimestamp
```

### Restart Deployment
```bash
# Force restart all pods
kubectl rollout restart deployment/flashstudio-monolith -n flash
```

---

## 💰 **Cost Estimation**

**Monthly costs (East US region):**
- AKS Control Plane: **$0** (Free tier)
- 2x Standard_B2s nodes: **$60** ($30 each)
- Azure Container Registry (Basic): **$5**
- LoadBalancer: **$5**
- **Total: ~$70/month**

---

## 🎯 **Success Criteria**

Your deployment is successful when:
- ✅ AKS cluster is running (2 nodes)
- ✅ ACR contains your Docker image
- ✅ Pods are running (2 replicas)
- ✅ LoadBalancer has external IP
- ✅ Application accessible via browser
- ✅ All features working (admin, payments, videos)

---

## 📞 **Support Resources**

- **Azure Portal**: Monitor resources and costs
- **GitHub Actions**: Check deployment logs
- **kubectl**: Manage Kubernetes resources
- **Azure CLI**: Manage Azure resources

**🎉 Congratulations! Your FlashStudio monolith is now running on Azure Kubernetes Service!**