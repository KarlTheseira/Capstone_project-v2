# Azure App Service Deployment Guide for Beginners

## 🎯 **What is Azure App Service?**

Azure App Service is like having a **web hosting service on steroids**. Think of it as:
- A server that Microsoft manages for you
- Automatically scales when you get more visitors
- Connects directly to your GitHub repository
- Handles security updates and maintenance

## 🚀 **Step-by-Step Deployment to Azure App Service**

### **Step 1: Prepare Your Application**

First, let's make sure your Flask app is ready for Azure App Service.

#### **1.1 Create requirements.txt (if not exists)**
```bash
# Your requirements.txt should include:
Flask==3.1.2
gunicorn>=20.0.0
# ... all other dependencies
```

#### **1.2 Create startup command file**
Create `startup.sh`:
```bash
#!/bin/bash
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

#### **1.3 Set environment variables**
Your app needs these environment variables in Azure:
- `SECRET_KEY`
- `ADMIN_USERNAME` 
- `ADMIN_PASSWORD`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_SECRET_KEY`

---

### **Step 2: Create Azure Resources**

#### **2.1 Login to Azure Portal**
1. Go to [portal.azure.com](https://portal.azure.com)
2. Sign in with your Microsoft account
3. If you don't have an Azure account, create one (free tier available)

#### **2.2 Create a Resource Group**
Think of a resource group as a **folder** that holds all your Azure resources.

1. Click **"Create a resource"**
2. Search for **"Resource group"**
3. Click **"Create"**
4. Fill in details:
   - **Subscription**: Your subscription
   - **Resource group name**: `flashstudio-rg`
   - **Region**: `East US` (or closest to you)
5. Click **"Review + Create"** → **"Create"**

#### **2.3 Create App Service Plan**
This determines the **power and cost** of your web server.

1. Search for **"App Service Plan"**
2. Click **"Create"**
3. Fill in details:
   - **Resource Group**: `flashstudio-rg`
   - **Name**: `flashstudio-plan`
   - **Operating System**: `Linux`
   - **Region**: `East US`
   - **Pricing Tier**: `Basic B1` (about $13/month) or `Free F1` for testing
4. Click **"Review + Create"** → **"Create"**

---

### **Step 3: Create Web App**

#### **3.1 Create the Web App**
1. Search for **"Web App"**
2. Click **"Create"**
3. Fill in details:
   - **Resource Group**: `flashstudio-rg`
   - **Name**: `flashstudio-app` (must be globally unique)
   - **Publish**: `Code`
   - **Runtime stack**: `Python 3.12`
   - **Operating System**: `Linux`
   - **Region**: `East US`
   - **App Service Plan**: Select `flashstudio-plan`
4. Click **"Review + Create"** → **"Create"**

#### **3.2 Configure Deployment**
1. Go to your new Web App resource
2. In the left menu, click **"Deployment Center"**
3. Choose **"GitHub"** as source
4. Sign in to GitHub and authorize Azure
5. Select:
   - **Organization**: Your GitHub username
   - **Repository**: `Capstone_project-v2`
   - **Branch**: `main`
6. Click **"Save"**

Azure will now automatically deploy your app when you push to GitHub!

---

### **Step 4: Configure Environment Variables**

#### **4.1 Set Application Settings**
1. In your Web App, go to **"Settings"** → **"Environment variables"**
2. Click **"+ Add"** for each environment variable:

```
Name: SECRET_KEY
Value: your-super-secret-key-here

Name: ADMIN_USERNAME  
Value: admin

Name: ADMIN_PASSWORD
Value: your-secure-password

Name: STRIPE_PUBLISHABLE_KEY
Value: pk_test_your_stripe_key

Name: STRIPE_SECRET_KEY
Value: sk_test_your_stripe_key

Name: SCM_DO_BUILD_DURING_DEPLOYMENT
Value: true
```

3. Click **"Apply"** to save

#### **4.2 Configure Startup Command**
1. Go to **"Settings"** → **"Configuration"**
2. In **"Startup Command"**, enter:
   ```
   gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
   ```
3. Click **"Save"**

---

### **Step 5: Monitor Deployment**

#### **5.1 Watch the Build**
1. Go to **"Deployment Center"**
2. You'll see the deployment status
3. Click on a deployment to see logs
4. Wait for **"Success"** status (usually 5-10 minutes)

#### **5.2 Test Your Application**
1. Go to **"Overview"** 
2. Click on your **"Default domain"** (like `https://flashstudio-app.azurewebsites.net`)
3. Your Flask application should load!

---

## 💰 **Cost Breakdown**

### **Free Tier (Good for Learning)**
- **App Service Plan (F1)**: $0/month
- **Limitations**: 60 minutes/day, custom domains not supported

### **Basic Tier (Good for Small Projects)**
- **App Service Plan (B1)**: ~$13/month
- **Includes**: Custom domains, SSL certificates, 1.75 GB RAM

### **Production Tier (S1)**
- **App Service Plan (S1)**: ~$56/month
- **Includes**: Auto-scaling, staging slots, daily backups

---

## 🔧 **Troubleshooting Common Issues**

### **Issue 1: App Won't Start**
**Problem**: "Application Error" page shows
**Solution**: 
1. Check logs in **"Monitoring"** → **"Log stream"**
2. Verify startup command is correct
3. Check that all required environment variables are set

### **Issue 2: Dependencies Not Installing**
**Problem**: Import errors in logs
**Solution**:
1. Ensure `requirements.txt` is in root directory
2. Add `SCM_DO_BUILD_DURING_DEPLOYMENT=true` environment variable
3. Redeploy from GitHub

### **Issue 3: Static Files Not Loading**
**Problem**: CSS/images don't load
**Solution**:
1. Configure static files in your Flask app
2. Use Azure Blob Storage for static files (advanced)

---

## 📋 **Quick Deployment Checklist**

- [ ] ✅ Azure account created
- [ ] ✅ Resource group created
- [ ] ✅ App Service Plan created  
- [ ] ✅ Web App created
- [ ] ✅ GitHub deployment configured
- [ ] ✅ Environment variables set
- [ ] ✅ Startup command configured
- [ ] ✅ Application accessible via URL
- [ ] ✅ Admin panel working
- [ ] ✅ Database operations working

---

**Next: We'll add Azure Functions to extend your application!** 🚀