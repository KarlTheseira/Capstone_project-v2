# 🚀 FlashStudio Kubernetes Deployment Guide

## Prerequisites Checklist

Before deploying to Kubernetes, ensure you have:

### ✅ **Infrastructure Requirements**
- [ ] Kubernetes cluster running (AKS, GKE, EKS, or local)
- [ ] `kubectl` installed and configured
- [ ] Docker image registry access (Azure Container Registry)
- [ ] Cluster has internet access for pulling images

### ✅ **Application Requirements**
- [ ] Stripe account with API keys (test or live)
- [ ] Database configured (PostgreSQL recommended for production)
- [ ] Azure Blob Storage account (for file uploads)
- [ ] SSL/TLS certificates (for production HTTPS)

### ✅ **Configuration Files**
- [ ] `.env` file with all required environment variables
- [ ] `k8-deploy/deployment.yaml` updated
- [ ] `k8-deploy/service.yaml` configured
- [ ] Docker image built and pushed to registry

## 🔧 **Deployment Methods**

### **Method 1: Automated Deployment (Recommended)**

Use the provided deployment script:

```bash
# 1. Ensure all prerequisites are met
# 2. Update .env file with production values
# 3. Run automated deployment
./deploy.sh
```

### **Method 2: Manual Deployment**

If you prefer manual control:

```bash
# 1. Create namespace
kubectl create namespace flash

# 2. Create secrets
kubectl create secret generic stripe-secrets \
  --from-literal=STRIPE_PUBLISHABLE_KEY="pk_live_your_key" \
  --from-literal=STRIPE_SECRET_KEY="sk_live_your_key" \
  --from-literal=STRIPE_WEBHOOK_SECRET="whsec_your_secret" \
  --namespace=flash

kubectl create secret generic flashstudio-secrets \
  --from-literal=FLASK_SECRET_KEY="your-production-secret" \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db" \
  --namespace=flash

kubectl create secret generic blob-conn \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING="your-azure-connection" \
  --namespace=flash

# 3. Deploy application
kubectl apply -f k8-deploy/deployment.yaml
kubectl apply -f k8-deploy/service.yaml
```

## 🌍 **Environment Configurations**

### **Development Environment**
```bash
# Use test Stripe keys
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Use SQLite database
DATABASE_URL=sqlite:///filmcompany.db

# Use development Azure storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
```

### **Production Environment**
```bash
# Use live Stripe keys
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...

# Use PostgreSQL database
DATABASE_URL=postgresql://user:pass@azure-postgres:5432/flashstudio

# Use production Azure storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=prod;...
```

## 🔒 **Security Considerations**

### **Secrets Management**
- ✅ Store all sensitive data in Kubernetes secrets
- ✅ Use different secrets for different environments
- ✅ Rotate secrets regularly
- ❌ Never commit secrets to version control

### **Network Security**
- ✅ Use HTTPS in production (TLS termination)
- ✅ Configure network policies if needed
- ✅ Whitelist webhook endpoints
- ✅ Use private container registries

### **Application Security**
- ✅ Set strong Flask SECRET_KEY
- ✅ Use production-grade database
- ✅ Enable authentication for admin routes
- ✅ Configure CORS properly

## 📊 **Monitoring & Troubleshooting**

### **Health Checks**
The application includes health check endpoints:
- `/healthz` - Application health status
- Kubernetes probes monitor pod health

### **Common Issues & Solutions**

#### 1. **Pod CrashLoopBackOff**
```bash
# Check logs
kubectl logs -f deployment/flashstudio-monolith -n flash

# Common causes:
# - Missing environment variables
# - Database connection issues
# - Invalid Stripe keys
```

#### 2. **Service Not Accessible**
```bash
# Check service status
kubectl get services -n flash

# Port forward for testing
kubectl port-forward service/flashstudio-service 8080:80 -n flash
```

#### 3. **Payment Issues**
```bash
# Check Stripe webhook delivery in dashboard
# Verify webhook URL is accessible
# Check application logs for Stripe errors
```

### **Useful Commands**

```bash
# View all resources
kubectl get all -n flash

# Check pod logs
kubectl logs -f deployment/flashstudio-monolith -n flash

# Describe deployment
kubectl describe deployment flashstudio-monolith -n flash

# Get events
kubectl get events -n flash --sort-by=.metadata.creationTimestamp

# Scale deployment
kubectl scale deployment flashstudio-monolith --replicas=3 -n flash

# Update deployment (after pushing new image)
kubectl rollout restart deployment/flashstudio-monolith -n flash
```

## 🔄 **CI/CD Integration**

### **GitHub Actions Example**

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Build and push Docker image
      run: |
        docker build -t flashstudiomain.azurecr.io/flashstudio/monolith:${{ github.sha }} .
        docker push flashstudiomain.azurecr.io/flashstudio/monolith:${{ github.sha }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/flashstudio-monolith web=flashstudiomain.azurecr.io/flashstudio/monolith:${{ github.sha }} -n flash
```

## 🎯 **Production Checklist**

Before going live:

### **Application**
- [ ] Database migration completed
- [ ] Static files properly served
- [ ] Error pages configured
- [ ] Logging configured
- [ ] Backup strategy in place

### **Stripe Configuration**
- [ ] Live API keys configured
- [ ] Webhook endpoint accessible
- [ ] Payment flow tested
- [ ] Tax configuration (if needed)
- [ ] Dispute handling process

### **Infrastructure**
- [ ] Load balancer configured
- [ ] SSL certificates installed
- [ ] Domain name configured
- [ ] Monitoring alerts set up
- [ ] Backup procedures tested

### **Security**
- [ ] Security scan completed
- [ ] Penetration test (if required)
- [ ] Access controls reviewed
- [ ] Secrets audit completed

## 📞 **Support & Resources**

- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Stripe Documentation**: https://stripe.com/docs
- **Azure AKS Documentation**: https://docs.microsoft.com/en-us/azure/aks/
- **Flask Production Guide**: https://flask.palletsprojects.com/en/2.0.x/deploying/