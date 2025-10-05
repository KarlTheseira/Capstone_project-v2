# 🏗️ FlashStudio AKS Deployment Architecture

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AZURE SUBSCRIPTION                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                        RESOURCE GROUP: flashstudio-rg                      │ │
│  │                                                                             │ │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────────────────┐ │ │
│  │  │ Azure Container     │    │           Azure Kubernetes Service          │ │ │
│  │  │ Registry (ACR)      │    │              flashstudio-aks               │ │ │
│  │  │                     │    │                                             │ │ │
│  │  │ flashstudiomain     │───►│  ┌─────────────────────────────────────────┐ │ │ │
│  │  │ .azurecr.io         │    │  │          Namespace: flash               │ │ │ │
│  │  │                     │    │  │                                         │ │ │ │
│  │  │ • Docker Images     │    │  │  ┌──────────────────────────────────────┐ │ │ │ │
│  │  │ • Version Control   │    │  │  │        Deployment                    │ │ │ │ │
│  │  │ • CI/CD Integration │    │  │  │   flashstudio-monolith              │ │ │ │ │
│  │  └─────────────────────┘    │  │  │                                      │ │ │ │ │
│  │                             │  │  │  ┌─────────────┐ ┌─────────────────┐ │ │ │ │ │
│  │                             │  │  │  │   Pod 1     │ │      Pod 2      │ │ │ │ │ │
│  │                             │  │  │  │             │ │                 │ │ │ │ │ │
│  │                             │  │  │  │ FlashStudio │ │   FlashStudio   │ │ │ │ │ │
│  │                             │  │  │  │ Monolith    │ │   Monolith      │ │ │ │ │ │
│  │                             │  │  │  │             │ │                 │ │ │ │ │ │
│  │                             │  │  │  │ Port: 8000  │ │   Port: 8000    │ │ │ │ │ │
│  │                             │  │  │  └─────────────┘ └─────────────────┘ │ │ │ │ │
│  │                             │  │  └──────────────────────────────────────┘ │ │ │ │
│  │                             │  │                     │                     │ │ │ │
│  │                             │  │  ┌──────────────────▼──────────────────┐ │ │ │ │
│  │                             │  │  │            Service                  │ │ │ │ │
│  │                             │  │  │        flashstudio-lb              │ │ │ │ │
│  │                             │  │  │                                     │ │ │ │ │
│  │                             │  │  │     Type: LoadBalancer              │ │ │ │ │
│  │                             │  │  │     Port: 80 → 8000                │ │ │ │ │
│  │                             │  │  └─────────────────────────────────────┘ │ │ │ │
│  │                             │  └─────────────────────────────────────────┐ │ │ │
│  │                             │                                             │ │ │ │
│  │                             │  ┌─────────────────────────────────────────┐ │ │ │ │
│  │                             │  │               Secrets                   │ │ │ │ │
│  │                             │  │                                         │ │ │ │ │
│  │                             │  │ • flashstudio-secrets (DB, App)        │ │ │ │ │
│  │                             │  │ • stripe-secrets (Payments)            │ │ │ │ │
│  │                             │  │ • google-drive-secrets (Storage)       │ │ │ │ │
│  │                             │  └─────────────────────────────────────────┘ │ │ │ │
│  │                             └─────────────────────────────────────────────┘ │ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │ │
└─────────────────────────────────────────────────────────────────────────────────┘ │
                                         │                                           │
                                         ▼                                           │
┌─────────────────────────────────────────────────────────────────────────────────┐ │
│                             PUBLIC INTERNET                                     │ │
│                                                                                 │ │
│                    http://[EXTERNAL-IP] ◄── Load Balancer                      │ │
│                                                                                 │ │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │ │
│  │      Users      │───►│   FlashStudio   │───►│        Features            │ │ │
│  │                 │    │    Website      │    │                            │ │ │
│  │ • Browse Videos │    │                 │    │ • Video Management         │ │ │
│  │ • Make Orders   │    │ Load Balanced   │    │ • Payment Processing       │ │ │
│  │ • Admin Access  │    │ Across 2 Pods   │    │ • File Storage             │ │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────┘ │ │
└─────────────────────────────────────────────────────────────────────────────────┘ │
                                                                                   │
┌─────────────────────────────────────────────────────────────────────────────────┐ │
│                              CI/CD PIPELINE                                     │ │
│                                                                                 │ │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │ │
│  │  VS Code    │───►│   GitHub    │───►│GitHub Actions│───►│  Auto Deploy   │ │ │
│  │             │    │             │    │             │    │                 │ │ │
│  │ • Edit Code │    │ • git push  │    │ • Build     │    │ • Update Pods   │ │ │
│  │ • Test      │    │ • Triggers  │    │ • Test      │    │ • Zero Downtime │ │ │
│  │ • Commit    │    │   CI/CD     │    │ • Deploy    │    │ • Health Checks │ │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────────┘ │ │
└─────────────────────────────────────────────────────────────────────────────────┘ │
```

## 📊 Component Details

### **Azure Resources**
- **Resource Group**: `flashstudio-rg` - Contains all resources
- **AKS Cluster**: `flashstudio-aks` - Managed Kubernetes service
- **ACR**: `flashstudiomain.azurecr.io` - Container image registry
- **Load Balancer**: Public IP for external access

### **Kubernetes Components**
- **Namespace**: `flash` - Isolated environment for FlashStudio
- **Deployment**: `flashstudio-monolith` - Manages 2 pod replicas
- **Service**: `flashstudio-lb` - LoadBalancer exposing port 80→8000
- **Secrets**: Configuration for database, Stripe, Google Drive

### **Application Architecture**
- **Monolithic Design**: Single container with all features
- **High Availability**: 2 pods for redundancy
- **Auto-scaling**: Can scale up/down based on traffic
- **Health Checks**: Kubernetes monitors pod health

### **Deployment Flow**
1. **Code Change**: Developer pushes to GitHub
2. **CI/CD Trigger**: GitHub Actions workflow starts
3. **Build**: Docker image created with new code
4. **Push**: Image pushed to Azure Container Registry
5. **Deploy**: Kubernetes pulls new image and updates pods
6. **Rolling Update**: Zero-downtime deployment

### **Security Features**
- **Secrets Management**: Encrypted storage of sensitive data
- **Network Isolation**: Kubernetes networking
- **RBAC**: Role-based access control
- **Health Monitoring**: Continuous health checks

## 🎯 **Benefits of This Architecture**

✅ **Scalability**: Easy to add more pods or nodes
✅ **Reliability**: Multiple pods provide redundancy  
✅ **Automation**: CI/CD pipeline handles deployments
✅ **Monitoring**: Built-in Azure monitoring and logging
✅ **Cost-Effective**: Pay for actual resource usage
✅ **Production-Ready**: Enterprise-grade infrastructure