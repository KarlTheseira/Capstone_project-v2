# 🚨 GitHub Actions Deployment Fix Guide

## Problem: Process completed with exit code 1

Your GitHub Actions deployment is failing because of several issues. Here's how to fix them:

## 🔧 **Immediate Fixes Required**

### **Step 1: Get Your Azure Publish Profile**

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to your App Service** (flashstudio-app)
3. **Click "Get publish profile"** in the top menu
4. **Download the .PublishSettings file**
5. **Open the file in notepad** and copy ALL the content

### **Step 2: Add GitHub Secret**

1. **Go to your GitHub repository**: https://github.com/KarlTheseira/Capstone_project-v2
2. **Click "Settings" tab**
3. **Click "Secrets and variables" → "Actions"**
4. **Click "New repository secret"**
5. **Name**: `AZURE_WEBAPP_PUBLISH_PROFILE`
6. **Value**: Paste the entire publish profile content
7. **Click "Add secret"**

### **Step 3: Update Azure Workflow Name**

The workflow needs the correct app name. In the Azure workflow file, change:

```yaml
env:
  AZURE_WEBAPP_NAME: your-actual-app-name-here    # Change this!
```

To find your app name:
- Go to Azure Portal → App Service
- Copy the exact name (e.g., "flashstudio-app-karl" or whatever you named it)

### **Step 4: Disable Conflicting Workflow**

Your current `ci-cd.yml` workflow conflicts with Azure deployment. Either:

**Option A: Rename it**
```bash
mv .github/workflows/ci-cd.yml .github/workflows/ci-cd.yml.disabled
```

**Option B: Add condition to skip on main branch**
```yaml
# Add this at the top of ci-cd.yml
on:
  push:
    branches: [ develop ]  # Remove 'main' from here
```

## 🚀 **Quick Terminal Commands**

Run these in your terminal to fix the issues:

```bash
# 1. Disable the conflicting workflow
mv .github/workflows/ci-cd.yml .github/workflows/ci-cd.yml.backup

# 2. Commit the new Azure workflow
git add .
git commit -m "Fix Azure deployment workflow"
git push origin main
```

## 🔍 **Common Exit Code 1 Causes**

### **Missing Dependencies**
- **Issue**: Some packages don't install on Azure Linux
- **Fix**: Updated requirements.txt with compatible versions

### **Python Version Mismatch**
- **Issue**: Local Python 3.12 vs Azure Python 3.11
- **Fix**: Updated workflow to use Python 3.11

### **Startup Command Issues**
- **Issue**: Wrong WSGI configuration
- **Fix**: Ensure `startup.txt` contains: `gunicorn --bind=0.0.0.0 --timeout 600 app:app`

### **Environment Variables Missing**
- **Issue**: Flask app can't start without required env vars
- **Fix**: Set these in Azure Portal → Configuration:

```
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DATABASE_URL=sqlite:///flashstudio.db
GOOGLE_DRIVE_CREDENTIALS_JSON={"type":"service_account"...}
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
```

## 🎯 **Testing the Fix**

1. **Push your changes**:
```bash
git add .
git commit -m "Fix deployment configuration"
git push origin main
```

2. **Monitor the deployment**:
- Go to GitHub → Actions tab
- Watch the "Deploy FlashStudio to Azure App Service" workflow
- Should see green checkmarks instead of red X's

3. **Check Azure Portal**:
- Go to App Service → Deployment Center
- Should show successful deployment from GitHub

## ⚠️ **If Still Failing**

### **Check Azure Logs**
1. Azure Portal → App Service → Log stream
2. Look for specific error messages

### **Manual Deploy Option**
If GitHub Actions keeps failing, you can deploy manually:

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login and deploy
az login
az webapp up --resource-group flashstudio-rg --name your-app-name --runtime "PYTHON:3.11"
```

## ✅ **Success Indicators**

- ✅ GitHub Actions shows green checkmark
- ✅ Azure Portal shows "Deployment successful"  
- ✅ Your app URL loads without errors
- ✅ No "Application Error" page in browser

---

**Need help?** The most common issue is the missing publish profile secret. Make sure you:
1. Downloaded the .PublishSettings file from Azure
2. Added it as `AZURE_WEBAPP_PUBLISH_PROFILE` in GitHub secrets
3. Used the exact app name in the workflow

Try these fixes and let me know which step resolves the exit code 1 error!