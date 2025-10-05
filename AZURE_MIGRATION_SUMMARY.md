# FlashStudio: Azure App Service → AKS Migration

## ✅ Changes Made

### 1. **Removed Azure App Service Deployment**
- **Deleted workflow**: `.github/workflows/main_flashstudio-karl.yml.disabled`
- **Removed App Service files**: 
  - `startup.txt` (Gunicorn startup config for App Service)
  - `wsgi.py` (WSGI entry point for App Service)
  - `fix-deployment.sh` (App Service troubleshooting script)
  - `AZURE_APP_SERVICE_GUIDE.md` (App Service deployment guide)
  - `DEPLOYMENT_FIX_GUIDE.md` (App Service troubleshooting guide)

### 2. **Updated AKS Configuration**
- **Fixed image reference** in `k8-deploy/deployment.yaml`: 
  - Changed from hardcoded `v2` tag to `latest` tag
  - Matches CI/CD pipeline dynamic tagging
- **Updated deployment script** (`deploy-to-aks.sh`):
  - Fixed ACR name: `flashstudioregistry` → `flashstudiomain` 
  - Added proper namespace handling: `flash`
  - Fixed service names: `flashstudio-service` → `flashstudio-lb`
  - Added Google Drive secrets creation

### 3. **Current Deployment Options**

#### Option A: **Automated CI/CD (Recommended)**
```bash
# Push to main branch triggers automatic deployment
git add .
git commit -m "Switch from App Service to AKS deployment" 
git push origin main
```

**Requirements for GitHub Actions:**
- `AZURE_CREDENTIALS` - Service principal for Azure access
- `ACR_LOGIN_SERVER` - `flashstudiomain.azurecr.io`
- `RESOURCE_GROUP` - Resource group name
- `AKS_CLUSTER_NAME` - AKS cluster name  
- `NAMESPACE` - `flash`

#### Option B: **Manual Deployment**
```bash
# Run the deployment script
./deploy-to-aks.sh
```

**What the script does:**
1. Creates Azure Resource Group
2. Creates Azure Container Registry (ACR)  
3. Creates AKS cluster
4. Builds and pushes Docker image
5. Creates Kubernetes namespace and secrets
6. Deploys application to AKS

## 🏗️ **Current Architecture**

```
GitHub Repository (main branch)
        ↓
   GitHub Actions CI/CD
        ↓
   Azure Container Registry
        ↓
   Azure Kubernetes Service
        ↓
   Load Balancer (Public IP)
```

## 📊 **Deployment Status**

### **Active Deployment Method**: AKS via GitHub Actions
### **Removed Deployment Method**: Azure App Service (completely removed)

## 🔧 **Configuration Files**

### **Kubernetes Manifests**
- `k8-deploy/deployment.yaml` - Main application deployment
- `k8-deploy/service.yaml` - LoadBalancer service 
- `k8-deploy/stripe-secrets.yaml` - Stripe payment secrets template

### **CI/CD Pipeline**  
- `.github/workflows/ci-cd.yaml` - AKS deployment pipeline (ACTIVE)
- *Azure App Service pipeline removed*

### **Application Configuration**
- `Dockerfile` - Optimized for Kubernetes deployment
- `entrypoint.sh` - Gunicorn startup for port 8000
- `requirements.txt` - Python dependencies

## 🚀 **Next Steps**

1. **Test the deployment**:
   ```bash
   # Method 1: Push to GitHub (triggers CI/CD)
   git push origin main
   
   # Method 2: Manual deployment
   ./deploy-to-aks.sh
   ```

2. **Configure secrets** (if using manual deployment):
   ```bash
   # Update Stripe secrets with real values
   kubectl patch secret stripe-secrets -n flash -p='{"data":{"STRIPE_SECRET_KEY":"'$(echo -n "sk_live_your_real_key" | base64)'"}}' 
   
   # Update Google Drive secrets with real values  
   kubectl patch secret google-drive-secrets -n flash -p='{"data":{"GOOGLE_DRIVE_CREDENTIALS_JSON":"'$(echo -n '{"your":"real","credentials":"here"}' | base64)'"}}' 
   ```

3. **Monitor the deployment**:
   ```bash
   # Check pod status
   kubectl get pods -n flash
   
   # Check service status  
   kubectl get services -n flash
   
   # View logs
   kubectl logs -l app=flashstudio-monolith -n flash
   ```

4. **Get application URL**:
   ```bash
   kubectl get service flashstudio-lb -n flash
   # Look for EXTERNAL-IP value
   ```

## 📱 **Access Your Application**

Once deployed, your FlashStudio application will be available at the LoadBalancer's external IP address on port 80.

## 🔄 **Rollback Option**

If you need to switch back to Azure App Service:
1. Restore files from Git history: `git checkout HEAD~1 -- .github/workflows/main_flashstudio-karl.yml AZURE_APP_SERVICE_GUIDE.md`
2. Recreate `startup.txt` and `wsgi.py` files (see Git history for content)
3. Push changes to trigger App Service deployment

**Note**: All App Service files have been removed but are available in Git history.

## 🎯 **Benefits of AKS over App Service**

- ✅ **Better scaling**: Horizontal pod autoscaling
- ✅ **Cost control**: Pay for actual resource usage  
- ✅ **Flexibility**: Full Kubernetes feature set
- ✅ **Multi-service ready**: Easy to add microservices later
- ✅ **Rolling updates**: Zero-downtime deployments
- ✅ **Load balancing**: Built-in traffic distribution