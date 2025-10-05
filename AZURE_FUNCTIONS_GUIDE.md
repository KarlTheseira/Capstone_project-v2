# Azure Functions Guide for Beginners

## 🎯 **What are Azure Functions?**

Think of Azure Functions as **small pieces of code that run in the cloud** when something happens. They're like having **mini-programs** that:

- ✅ **Run automatically** when triggered (like when a file is uploaded)
- ✅ **Scale instantly** - Handle 1 request or 1000 requests
- ✅ **Cost nothing when not used** - Pay only when they run
- ✅ **No server management** - Microsoft handles everything

### **Real-World Analogy**
Imagine Azure Functions like **smart light switches**:
- A regular app is like **keeping lights on all the time** (always running, always costing money)
- Azure Functions are like **motion sensors** (only turn on when needed, save energy/money)

---

## 🏗️ **How Azure Functions Help Your FlashStudio App**

### **Current FlashStudio Architecture**
```
User → Flask App → Does Everything
                ├── Handle payments
                ├── Process images
                ├── Send emails
                └── Generate reports
```

### **With Azure Functions Architecture**
```
User → Flask App → Handles main website
         ↓
    Azure Functions → Specialized tasks
    ├── Payment Processing Function
    ├── Image Resizing Function
    ├── Email Notification Function
    └── Report Generation Function
```

**Benefits:**
- **Better Performance** - Main app stays fast
- **Better Scaling** - Heavy tasks scale independently
- **Lower Costs** - Pay only when functions run
- **Better Reliability** - If one function fails, others keep working

---

## 🚀 **Azure Functions We'll Add to FlashStudio**

### **Function 1: Image Processing**
**Purpose**: Automatically resize and optimize uploaded images
**Trigger**: When image uploaded to blob storage
**What it does**: Creates thumbnails, optimizes file size

### **Function 2: Payment Processing**
**Purpose**: Handle payment webhooks from Stripe
**Trigger**: HTTP request from Stripe
**What it does**: Updates order status, sends confirmation emails

### **Function 3: Email Notifications**
**Purpose**: Send automated emails (welcome, receipts, quotes)
**Trigger**: Message in queue
**What it does**: Formats and sends professional emails

### **Function 4: Analytics Processing**
**Purpose**: Generate daily/weekly business reports
**Trigger**: Timer (runs daily at midnight)
**What it does**: Calculates metrics, creates reports

---

## 📋 **Step-by-Step: Creating Your First Azure Function**

### **Step 1: Install Azure Functions Tools**

#### **1.1 Install Azure Functions Core Tools**
```bash
# On Ubuntu/Linux
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

#### **1.2 Install Python Dependencies**
```bash
pip install azure-functions azure-storage-blob requests
```

### **Step 2: Create Function App Project**

#### **2.1 Create Project Directory**
```bash
# Create a new directory for functions
mkdir flashstudio-functions
cd flashstudio-functions

# Initialize Azure Functions project
func init . --python
```

#### **2.2 Create Your First Function**
```bash
# Create an HTTP-triggered function
func new --name PaymentWebhook --template "HTTP trigger"
```

This creates:
```
flashstudio-functions/
├── PaymentWebhook/
│   ├── __init__.py          # Your function code
│   └── function.json        # Function configuration
├── host.json                # App-wide settings
├── local.settings.json      # Local environment variables
└── requirements.txt         # Python dependencies
```

---

## 💻 **Example: Payment Webhook Function**

Let's create a real function that handles Stripe payment webhooks:

### **Step 3.1: Edit PaymentWebhook/__init__.py**

```python
import azure.functions as func
import logging
import json
import stripe
import os
from datetime import datetime

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Payment webhook triggered')
    
    try:
        # Get the request body
        payload = req.get_body()
        sig_header = req.headers.get('stripe-signature')
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        # Verify webhook signature (security)
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            logging.error("Invalid payload")
            return func.HttpResponse("Invalid payload", status_code=400)
        except stripe.error.SignatureVerificationError:
            logging.error("Invalid signature")
            return func.HttpResponse("Invalid signature", status_code=400)
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            logging.info(f"Payment succeeded: {payment_intent['id']}")
            
            # Here you would:
            # 1. Update order status in database
            # 2. Send confirmation email
            # 3. Trigger fulfillment process
            
            return func.HttpResponse(
                json.dumps({"status": "success", "message": "Payment processed"}),
                status_code=200,
                mimetype="application/json"
            )
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            logging.info(f"Payment failed: {payment_intent['id']}")
            
            # Handle failed payment
            # 1. Update order status
            # 2. Send failure notification
            # 3. Trigger retry logic
            
            return func.HttpResponse(
                json.dumps({"status": "handled", "message": "Payment failure processed"}),
                status_code=200,
                mimetype="application/json"
            )
        
        else:
            logging.info(f"Unhandled event type: {event['type']}")
            return func.HttpResponse("Event received", status_code=200)
            
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return func.HttpResponse(
            "Internal server error",
            status_code=500
        )
```

### **Step 3.2: Configure Function Settings**

Edit `PaymentWebhook/function.json`:
```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": [
        "post"
      ]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

---

## 🔄 **Example: Image Processing Function**

### **Step 4.1: Create Image Resizer Function**
```bash
func new --name ImageProcessor --template "Blob trigger"
```

### **Step 4.2: Edit ImageProcessor/__init__.py**

```python
import azure.functions as func
import logging
from PIL import Image
import io
from azure.storage.blob import BlobServiceClient

def main(myblob: func.InputStream) -> None:
    logging.info(f"Processing blob: {myblob.name}")
    
    try:
        # Read the uploaded image
        image_data = myblob.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Create thumbnail (300x300)
        thumbnail = image.copy()
        thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # Save thumbnail to bytes
        thumbnail_io = io.BytesIO()
        # Preserve original format or default to JPEG
        format = image.format if image.format else 'JPEG'
        thumbnail.save(thumbnail_io, format=format, quality=85, optimize=True)
        thumbnail_io.seek(0)
        
        # Upload thumbnail to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(
            os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        )
        
        # Generate thumbnail filename
        original_name = myblob.name.split('/')[-1]  # Get filename from path
        name_parts = original_name.rsplit('.', 1)
        thumbnail_name = f"{name_parts[0]}_thumb.{name_parts[1]}" if len(name_parts) > 1 else f"{original_name}_thumb"
        
        # Upload thumbnail
        blob_client = blob_service_client.get_blob_client(
            container="thumbnails",
            blob=thumbnail_name
        )
        
        blob_client.upload_blob(thumbnail_io.getvalue(), overwrite=True)
        
        logging.info(f"Thumbnail created: {thumbnail_name}")
        
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
```

---

## ⏰ **Example: Scheduled Analytics Function**

### **Step 5.1: Create Timer Function**
```bash
func new --name DailyAnalytics --template "Timer trigger"
```

### **Step 5.2: Edit DailyAnalytics/__init__.py**

```python
import azure.functions as func
import logging
from datetime import datetime, timedelta
import requests
import os

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Daily analytics function started at %s', utc_timestamp)
    
    try:
        # Calculate yesterday's metrics
        yesterday = datetime.now() - timedelta(days=1)
        
        # Call your main app's analytics API
        app_url = os.environ.get('MAIN_APP_URL')
        analytics_data = {
            'date': yesterday.strftime('%Y-%m-%d'),
            'metrics': []
        }
        
        # You would fetch data from your database here
        # For demo, we'll simulate
        analytics_data['metrics'] = {
            'daily_revenue': 1250.00,
            'new_orders': 15,
            'website_visitors': 320,
            'conversion_rate': 4.7
        }
        
        # Send report (could be email, database update, etc.)
        logging.info(f"Analytics calculated: {analytics_data}")
        
        # Example: Send to main app
        if app_url:
            response = requests.post(
                f"{app_url}/api/analytics/daily",
                json=analytics_data,
                headers={'Content-Type': 'application/json'}
            )
            logging.info(f"Analytics sent to main app: {response.status_code}")
            
    except Exception as e:
        logging.error(f"Error in daily analytics: {str(e)}")
```

### **Step 5.3: Configure Timer Schedule**

Edit `DailyAnalytics/function.json`:
```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 2 * * *"
    }
  ]
}
```

**Schedule Format Explanation:**
- `0 0 2 * * *` = Every day at 2:00 AM UTC
- Format: `{second} {minute} {hour} {day} {month} {day-of-week}`

---

## 🚀 **Deploying Azure Functions**

### **Step 6: Deploy to Azure**

#### **6.1 Create Function App in Azure Portal**
1. Go to **Azure Portal** → **Create Resource**
2. Search for **"Function App"**
3. Fill details:
   - **Resource Group**: `flashstudio-rg`
   - **Function App name**: `flashstudio-functions`
   - **Runtime**: `Python 3.12`
   - **Region**: Same as your web app
   - **Hosting Plan**: `Consumption (Serverless)`

#### **6.2 Deploy from Command Line**
```bash
# Login to Azure
az login

# Deploy your functions
func azure functionapp publish flashstudio-functions
```

#### **6.3 Set Environment Variables**
In Azure Portal, go to your Function App:
1. **Settings** → **Environment variables**
2. Add all required variables:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `AZURE_STORAGE_CONNECTION_STRING`
   - `MAIN_APP_URL`

---

## 🔗 **Integrating Functions with Your Flask App**

### **Step 7: Update Your Flask App**

#### **7.1 Add Function URLs to Config**
In your `config.py`:
```python
class Config:
    # ... existing config ...
    
    # Azure Functions URLs
    PAYMENT_WEBHOOK_URL = os.getenv("PAYMENT_WEBHOOK_URL", "")
    IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "")
```

#### **7.2 Trigger Functions from Flask**
In your Flask routes:
```python
import requests

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    # ... existing upload logic ...
    
    # After file upload, trigger image processing
    if file_uploaded_successfully:
        try:
            # Trigger Azure Function (if using HTTP trigger)
            function_url = current_app.config['IMAGE_PROCESSOR_URL']
            if function_url:
                requests.post(function_url, json={
                    'blob_name': filename,
                    'container': 'uploads'
                })
        except Exception as e:
            logger.error(f"Failed to trigger image processing: {e}")
    
    return jsonify({"status": "success"})
```

---

## 💰 **Azure Functions Cost (Very Cheap!)**

### **Consumption Plan Pricing**
- **First 1 million executions**: FREE every month
- **After that**: $0.20 per million executions
- **Execution time**: $0.000016 per GB-second

### **Example Monthly Costs**
- **Small app** (10,000 function calls): $0
- **Medium app** (100,000 calls): $0
- **Large app** (5 million calls): ~$1
- **Very large app** (20 million calls): ~$4

**Most small to medium applications will cost $0-2/month for Azure Functions!**

---

## 🎯 **Next Steps for Your FlashStudio App**

### **Immediate Functions to Add**
1. **Payment Webhook Handler** - Process Stripe events
2. **Image Optimizer** - Resize uploaded images
3. **Email Sender** - Send confirmation emails

### **Advanced Functions (Later)**
1. **PDF Generator** - Create invoices/quotes
2. **Data Backup** - Daily database backups
3. **Security Scanner** - Check for malicious uploads

### **Testing Your Functions**
```bash
# Test locally
func start

# Test specific function
curl -X POST http://localhost:7071/api/PaymentWebhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

**Ready to add serverless superpowers to your FlashStudio app!** ⚡

Next, I'll show you exactly how to implement these functions in your project.