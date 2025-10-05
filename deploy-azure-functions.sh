#!/bin/bash

# 🚀 Azure Functions Deployment Script for FlashStudio
# This script automates the deployment of Azure Functions

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (update these values)
RESOURCE_GROUP="${RESOURCE_GROUP:-flashstudio-rg}"
LOCATION="${LOCATION:-Southeast Asia}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-flashstudiostorage$(date +%s | tail -c 5)}"
FUNCTION_APP="${FUNCTION_APP:-flashstudio-functions}"
SUBSCRIPTION="${SUBSCRIPTION:-}"

echo -e "${BLUE}🚀 FlashStudio Azure Functions Deployment${NC}"
echo "=============================================="

# Check prerequisites
echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Functions Core Tools is installed
if ! command -v func &> /dev/null; then
    echo -e "${RED}❌ Azure Functions Core Tools is not installed.${NC}"
    echo "Install with: npm install -g azure-functions-core-tools@4 --unsafe-perm true"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}🔑 Not logged in to Azure. Please log in:${NC}"
    az login
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION" ]; then
    echo -e "${BLUE}🎯 Setting subscription to: $SUBSCRIPTION${NC}"
    az account set --subscription "$SUBSCRIPTION"
fi

echo -e "${GREEN}✅ Prerequisites check completed${NC}"

# Function to prompt for confirmation
confirm() {
    read -p "$(echo -e ${YELLOW}$1 ${NC}[y/N]: )" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Display configuration
echo -e "\n${BLUE}📝 Deployment Configuration:${NC}"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Location: $LOCATION"
echo "   Storage Account: $STORAGE_ACCOUNT"
echo "   Function App: $FUNCTION_APP"

if ! confirm "Do you want to continue with this configuration?"; then
    echo -e "${YELLOW}❌ Deployment cancelled${NC}"
    exit 0
fi

# Step 1: Create Resource Group
echo -e "\n${BLUE}📦 Creating resource group...${NC}"
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${GREEN}✅ Resource group '$RESOURCE_GROUP' already exists${NC}"
else
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    echo -e "${GREEN}✅ Created resource group '$RESOURCE_GROUP'${NC}"
fi

# Step 2: Create Storage Account
echo -e "\n${BLUE}💾 Creating storage account...${NC}"
if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${GREEN}✅ Storage account '$STORAGE_ACCOUNT' already exists${NC}"
else
    az storage account create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$STORAGE_ACCOUNT" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2
    echo -e "${GREEN}✅ Created storage account '$STORAGE_ACCOUNT'${NC}"
fi

# Step 3: Create Function App
echo -e "\n${BLUE}⚡ Creating Function App...${NC}"
if az functionapp show --name "$FUNCTION_APP" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${GREEN}✅ Function App '$FUNCTION_APP' already exists${NC}"
else
    az functionapp create \
        --resource-group "$RESOURCE_GROUP" \
        --consumption-plan-location "$LOCATION" \
        --runtime python \
        --runtime-version 3.9 \
        --functions-version 4 \
        --name "$FUNCTION_APP" \
        --storage-account "$STORAGE_ACCOUNT" \
        --os-type Linux
    echo -e "${GREEN}✅ Created Function App '$FUNCTION_APP'${NC}"
fi

# Step 4: Configure Environment Variables
echo -e "\n${BLUE}🔧 Setting up environment variables...${NC}"

# Required environment variables
echo -e "${YELLOW}Please provide the following configuration values:${NC}"

# SendGrid API Key
read -p "SendGrid API Key (for emails): " -s SENDGRID_KEY
echo
if [ -n "$SENDGRID_KEY" ]; then
    az functionapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$FUNCTION_APP" \
        --settings "EMAIL_API_KEY=$SENDGRID_KEY" \
        --output none
fi

# Stripe Webhook Secret
read -p "Stripe Webhook Secret (for payments): " -s STRIPE_SECRET
echo
if [ -n "$STRIPE_SECRET" ]; then
    az functionapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$FUNCTION_APP" \
        --settings "STRIPE_WEBHOOK_SECRET=$STRIPE_SECRET" \
        --output none
fi

# Admin Email
read -p "Admin Email (for notifications): " ADMIN_EMAIL
if [ -n "$ADMIN_EMAIL" ]; then
    az functionapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$FUNCTION_APP" \
        --settings "ADMIN_EMAIL=$ADMIN_EMAIL" \
        --output none
fi

# Flask App URL
read -p "Flask App URL (e.g., https://flashstudio-app.azurewebsites.net): " FLASK_URL
if [ -n "$FLASK_URL" ]; then
    az functionapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$FUNCTION_APP" \
        --settings "FLASK_APP_URL=$FLASK_URL" \
        --output none
fi

# Set default email from address
az functionapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --settings "EMAIL_FROM=noreply@flashstudio.com" \
    --output none

echo -e "${GREEN}✅ Environment variables configured${NC}"

# Step 5: Create Blob Storage Container for Images
echo -e "\n${BLUE}📁 Creating blob storage container...${NC}"
STORAGE_CONNECTION=$(az storage account show-connection-string \
    --resource-group "$RESOURCE_GROUP" \
    --name "$STORAGE_ACCOUNT" \
    --query connectionString --output tsv)

az storage container create \
    --name "images" \
    --connection-string "$STORAGE_CONNECTION" \
    --output none

echo -e "${GREEN}✅ Created blob storage container 'images'${NC}"

# Step 6: Deploy Functions
echo -e "\n${BLUE}🚀 Deploying Azure Functions...${NC}"

# Check if we're in the right directory
if [ ! -f "host.json" ]; then
    if [ -d "azure-functions" ]; then
        cd azure-functions
        echo -e "${YELLOW}📁 Switched to azure-functions directory${NC}"
    else
        echo -e "${RED}❌ Cannot find azure-functions directory or host.json file${NC}"
        echo "Please run this script from the FlashStudio root directory"
        exit 1
    fi
fi

# Deploy the functions
func azure functionapp publish "$FUNCTION_APP" --python

echo -e "${GREEN}✅ Functions deployed successfully!${NC}"

# Step 7: Verify Deployment
echo -e "\n${BLUE}🔍 Verifying deployment...${NC}"

# List deployed functions
FUNCTIONS=$(az functionapp function list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --query "[].name" --output tsv)

if [ -n "$FUNCTIONS" ]; then
    echo -e "${GREEN}✅ Deployed functions:${NC}"
    for func_name in $FUNCTIONS; do
        echo "   • $func_name"
    done
else
    echo -e "${RED}❌ No functions found. Deployment may have failed.${NC}"
fi

# Get function app URL
FUNCTION_URL="https://${FUNCTION_APP}.azurewebsites.net"

echo -e "\n${GREEN}🎉 Deployment completed successfully!${NC}"
echo "=============================================="
echo -e "${BLUE}📋 Summary:${NC}"
echo "   • Resource Group: $RESOURCE_GROUP"
echo "   • Function App: $FUNCTION_APP"
echo "   • Function URL: $FUNCTION_URL"
echo "   • Storage Account: $STORAGE_ACCOUNT"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "   1. Configure Stripe webhook URL: $FUNCTION_URL/api/PaymentWebhook"
echo "   2. Test email function: $FUNCTION_URL/api/EmailNotifications"
echo "   3. Monitor functions in Azure Portal"
echo "   4. Update your Flask app integration"
echo ""
echo -e "${BLUE}📚 Documentation: AZURE_FUNCTIONS_INTEGRATION.md${NC}"

# Optional: Open Azure Portal
if confirm "Do you want to open the Function App in Azure Portal?"; then
    az functionapp browse --resource-group "$RESOURCE_GROUP" --name "$FUNCTION_APP"
fi

echo -e "\n${GREEN}✨ Azure Functions deployment complete! ✨${NC}"