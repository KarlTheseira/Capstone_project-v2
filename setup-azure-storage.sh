#!/bin/bash
# Azure Blob Storage Setup Script for FlashStudio

set -e

echo "🌟 Azure Blob Storage Setup for FlashStudio"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed"
        echo "Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    print_success "Azure CLI is available"
}

# Login to Azure
azure_login() {
    print_status "Checking Azure login status..."
    
    if ! az account show &> /dev/null; then
        print_status "Please login to Azure..."
        az login
    fi
    
    SUBSCRIPTION=$(az account show --query name --output tsv)
    print_success "Logged in to Azure subscription: $SUBSCRIPTION"
}

# Create resource group
create_resource_group() {
    RESOURCE_GROUP=${1:-"flashstudio-rg"}
    LOCATION=${2:-"Southeast Asia"}
    
    print_status "Creating resource group: $RESOURCE_GROUP in $LOCATION"
    
    if az group show --name $RESOURCE_GROUP &> /dev/null; then
        print_success "Resource group $RESOURCE_GROUP already exists"
    else
        az group create --name $RESOURCE_GROUP --location "$LOCATION"
        print_success "Resource group $RESOURCE_GROUP created"
    fi
}

# Create storage account
create_storage_account() {
    RESOURCE_GROUP=${1:-"flashstudio-rg"}
    STORAGE_ACCOUNT=${2:-"flashstudioblob$(date +%s)"}
    
    print_status "Creating storage account: $STORAGE_ACCOUNT"
    
    if az storage account show --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP &> /dev/null; then
        print_success "Storage account $STORAGE_ACCOUNT already exists"
    else
        az storage account create \
            --name $STORAGE_ACCOUNT \
            --resource-group $RESOURCE_GROUP \
            --location "Southeast Asia" \
            --sku Standard_LRS \
            --kind StorageV2 \
            --access-tier Hot \
            --allow-blob-public-access true
        
        print_success "Storage account $STORAGE_ACCOUNT created"
    fi
}

# Create blob containers
create_containers() {
    STORAGE_ACCOUNT=$1
    
    print_status "Creating blob containers..."
    
    # Get storage account key
    STORAGE_KEY=$(az storage account keys list --account-name $STORAGE_ACCOUNT --query '[0].value' --output tsv)
    
    # Create containers
    containers=("uploads" "media" "backups")
    
    for container in "${containers[@]}"; do
        if az storage container show --name $container --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY &> /dev/null; then
            print_success "Container '$container' already exists"
        else
            az storage container create \
                --name $container \
                --account-name $STORAGE_ACCOUNT \
                --account-key $STORAGE_KEY \
                --public-access blob
            
            print_success "Container '$container' created"
        fi
    done
}

# Configure CORS
configure_cors() {
    STORAGE_ACCOUNT=$1
    
    print_status "Configuring CORS for storage account..."
    
    STORAGE_KEY=$(az storage account keys list --account-name $STORAGE_ACCOUNT --query '[0].value' --output tsv)
    
    az storage cors add \
        --services b \
        --methods GET POST PUT \
        --origins "*" \
        --allowed-headers "*" \
        --exposed-headers "*" \
        --max-age 3600 \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY
    
    print_success "CORS configured"
}

# Get connection string
get_connection_string() {
    STORAGE_ACCOUNT=$1
    RESOURCE_GROUP=$2
    
    print_status "Getting connection string..."
    
    CONNECTION_STRING=$(az storage account show-connection-string \
        --name $STORAGE_ACCOUNT \
        --resource-group $RESOURCE_GROUP \
        --query connectionString \
        --output tsv)
    
    echo ""
    print_success "🎉 Azure Blob Storage setup complete!"
    echo ""
    print_status "Configuration Details:"
    echo "Storage Account: $STORAGE_ACCOUNT"
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Containers: uploads, media, backups"
    echo ""
    print_status "Add this to your .env file:"
    echo "AZURE_STORAGE_CONNECTION_STRING=\"$CONNECTION_STRING\""
    echo "AZURE_STORAGE_ACCOUNT=\"$STORAGE_ACCOUNT\""
    echo "AZURE_STORAGE_CONTAINER=\"uploads\""
    echo ""
    print_status "Or update Kubernetes secrets:"
    echo "kubectl create secret generic blob-conn \\"
    echo "  --from-literal=AZURE_STORAGE_CONNECTION_STRING=\"$CONNECTION_STRING\" \\"
    echo "  --namespace=flash \\"
    echo "  --dry-run=client -o yaml | kubectl apply -f -"
}

# Main setup function
main() {
    RESOURCE_GROUP=${1:-"flashstudio-rg"}
    STORAGE_ACCOUNT=${2:-"flashstudioblob$(date +%s)"}
    
    print_status "Starting Azure Blob Storage setup..."
    print_status "Resource Group: $RESOURCE_GROUP"
    print_status "Storage Account: $STORAGE_ACCOUNT"
    echo ""
    
    check_azure_cli
    azure_login
    create_resource_group "$RESOURCE_GROUP"
    create_storage_account "$RESOURCE_GROUP" "$STORAGE_ACCOUNT"
    create_containers "$STORAGE_ACCOUNT"
    configure_cors "$STORAGE_ACCOUNT"
    get_connection_string "$STORAGE_ACCOUNT" "$RESOURCE_GROUP"
    
    print_success "✨ Setup completed successfully!"
}

# Show help
show_help() {
    echo "Azure Blob Storage Setup Script for FlashStudio"
    echo ""
    echo "Usage:"
    echo "  $0                                    # Use default names"
    echo "  $0 my-resource-group my-storage       # Custom names"
    echo "  $0 --help                            # Show this help"
    echo ""
    echo "This script will:"
    echo "  1. Create an Azure resource group"
    echo "  2. Create a storage account"
    echo "  3. Create blob containers (uploads, media, backups)"
    echo "  4. Configure CORS settings"
    echo "  5. Provide connection strings for your app"
}

# Check arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Run main setup
main "$1" "$2"