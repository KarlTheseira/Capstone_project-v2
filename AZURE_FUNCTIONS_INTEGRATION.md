# Azure Functions Integration Guide for FlashStudio

## Overview

This guide explains how to integrate and deploy Azure Functions with your FlashStudio Flask application to add serverless capabilities for payment processing, image optimization, email notifications, and analytics.

## 🚀 Azure Functions Implemented

### 1. PaymentWebhook Function
- **Trigger**: HTTP (POST)
- **Purpose**: Process Stripe payment webhooks
- **Features**: 
  - Signature verification
  - Payment success/failure handling
  - Order status updates
  - Error handling and logging

### 2. ImageProcessor Function
- **Trigger**: Blob Storage
- **Purpose**: Automatic image optimization
- **Features**:
  - Multiple size generation (thumbnail, medium, large)
  - Format optimization (JPEG, WebP)
  - Automatic processing on upload

### 3. EmailNotifications Function
- **Trigger**: HTTP (POST)
- **Purpose**: Send various email types
- **Features**:
  - Order confirmations
  - Quote responses
  - Welcome emails
  - Password resets
  - Custom notifications

### 4. DailyAnalytics Function
- **Trigger**: Timer (Daily at 9 AM)
- **Purpose**: Generate daily business reports
- **Features**:
  - Sales summaries
  - Customer metrics
  - Popular products analysis
  - Automated email reports

## 📋 Prerequisites

Before deploying Azure Functions, ensure you have:

```bash
# Azure CLI installed and logged in
az login
az account set --subscription "your-subscription-id"

# Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Python 3.9+ installed
python --version
```

## 🔧 Environment Setup

### 1. Create Required Azure Resources

First, create the necessary Azure resources:

```bash
# Set variables
RESOURCE_GROUP="flashstudio-rg"
LOCATION="Southeast Asia"
STORAGE_ACCOUNT="flashstudiostorage"
FUNCTION_APP="flashstudio-functions"
APP_SERVICE_PLAN="flashstudio-plan"

# Create resource group (if not exists)
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Create storage account for Functions
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

# Create Function App
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux
```

### 2. Configure Environment Variables

Set up the required environment variables for your Function App:

```bash
# SendGrid for emails
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "EMAIL_API_KEY=your-sendgrid-api-key"

az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "EMAIL_FROM=noreply@flashstudio.com"

# Stripe for payments
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret"

# Flask App integration
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "FLASK_APP_URL=https://flashstudio-app.azurewebsites.net"

az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "ANALYTICS_API_KEY=your-analytics-api-key"

# Admin notifications
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "ADMIN_EMAIL=admin@flashstudio.com"

# Blob storage for image processing
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --query connectionString --output tsv)

az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings "AzureWebJobsStorage=$STORAGE_CONNECTION"
```

## 🚀 Deployment Steps

### Step 1: Navigate to Functions Directory

```bash
cd azure-functions
```

### Step 2: Initialize Functions Project (if needed)

```bash
# Initialize the project
func init --python

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Test Functions Locally

```bash
# Start local development server
func start

# Test PaymentWebhook (in another terminal)
curl -X POST "http://localhost:7071/api/PaymentWebhook" \
  -H "Content-Type: application/json" \
  -d '{"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test123"}}}'

# Test EmailNotifications
curl -X POST "http://localhost:7071/api/EmailNotifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "welcome",
    "to": "test@example.com",
    "name": "Test User"
  }'
```

### Step 4: Deploy to Azure

```bash
# Login to Azure (if not already logged in)
az login

# Deploy functions
func azure functionapp publish $FUNCTION_APP --python

# Verify deployment
az functionapp function list --resource-group $RESOURCE_GROUP --name $FUNCTION_APP
```

### Step 5: Configure Webhooks and Integrations

#### Stripe Webhook Configuration

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://flashstudio-functions.azurewebsites.net/api/PaymentWebhook`
3. Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Copy webhook secret and update the environment variable

#### Blob Storage for Image Processing

```bash
# Create container for images
az storage container create \
  --name "images" \
  --connection-string "$STORAGE_CONNECTION"

# Update Flask app to use blob storage for uploads
```

## 🔗 Integration with Flask App

### 1. Update Flask App for Function Integration

Add these endpoints to your Flask app (`routes/admin.py` or new `routes/functions.py`):

```python
from flask import request, jsonify
import requests
import os

# Email notification helper
def send_notification_email(email_type, recipient_email, **kwargs):
    """Send email via Azure Function"""
    
    function_url = "https://flashstudio-functions.azurewebsites.net/api/EmailNotifications"
    
    payload = {
        "type": email_type,
        "to": recipient_email,
        **kwargs
    }
    
    try:
        response = requests.post(function_url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Email function error: {e}")
        return {"success": False, "error": str(e)}

# Use in your routes
@app.route('/checkout/success')
def checkout_success():
    # ... existing code ...
    
    # Send confirmation email
    send_notification_email(
        email_type="order_confirmation",
        recipient_email=order.customer_email,
        name=order.customer_name,
        order_id=order.id,
        total_amount=str(order.total),
        currency="SGD",
        items=[{"name": item.name, "price": str(item.price)} for item in order.items]
    )
    
    return render_template('confirmation.html', order=order)
```

### 2. Analytics API Endpoint

Add an analytics endpoint to provide data for the DailyAnalytics function:

```python
@app.route('/api/analytics')
@require_api_key  # Create this decorator for API security
def get_analytics():
    date = request.args.get('date')
    
    # Generate analytics data from your database
    analytics = {
        'date': date,
        'sales': {
            'total_revenue': calculate_daily_revenue(date),
            'total_orders': count_daily_orders(date),
            'average_order_value': calculate_avg_order_value(date),
            'currency': 'SGD'
        },
        'customers': {
            'new_registrations': count_new_customers(date),
            'returning_customers': count_returning_customers(date),
            'total_active': count_active_customers()
        },
        # ... more data
    }
    
    return jsonify(analytics)
```

## 🔍 Monitoring and Troubleshooting

### View Function Logs

```bash
# Stream live logs
func azure functionapp logstream $FUNCTION_APP

# View logs in Azure portal
az functionapp browse --resource-group $RESOURCE_GROUP --name $FUNCTION_APP
```

### Monitor Function Performance

```bash
# Get function statistics
az monitor metrics list \
  --resource "/subscriptions/YOUR-SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP" \
  --metric "FunctionExecutionCount,FunctionExecutionUnits"
```

### Common Issues and Solutions

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Environment Variables**: Verify all required settings are configured
3. **Timeout Issues**: Increase function timeout in `host.json`
4. **Authentication**: Check API keys and webhook secrets
5. **Permissions**: Ensure Function App has access to storage and other resources

## 💡 Best Practices

1. **Error Handling**: Always include try-catch blocks in functions
2. **Logging**: Use structured logging for better monitoring
3. **Security**: Validate all inputs and use proper authentication
4. **Performance**: Optimize for cold starts and execution time
5. **Testing**: Test functions locally before deployment
6. **Monitoring**: Set up alerts for function failures

## 🔄 Next Steps

1. **Set up Application Insights** for better monitoring
2. **Configure auto-scaling** for high traffic periods  
3. **Add more functions** for additional business logic
4. **Implement CI/CD pipeline** for automated deployments
5. **Add integration tests** for function reliability

## 📚 Additional Resources

- [Azure Functions Python Developer Guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [SendGrid Python SDK](https://github.com/sendgrid/sendgrid-python)
- [Stripe Webhooks Documentation](https://stripe.com/docs/webhooks)
- [Azure Blob Storage Python SDK](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python)

---

Your Azure Functions are now ready to extend FlashStudio with powerful serverless capabilities! 🚀