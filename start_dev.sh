#!/bin/bash
# Development startup script for FlashStudio
# This script activates the virtual environment and loads environment variables

echo "🚀 Starting FlashStudio Development Server..."

# Activate virtual environment
source venv/bin/activate

# Load environment variables from .env file
if [ -f .env ]; then
    echo "📁 Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found. Using default environment variables..."
    export FLASK_SECRET_KEY="dev-secret-key"
    export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=devtest;AccountKey=test;EndpointSuffix=core.windows.net"
fi

# Check if Stripe keys are configured
if [ -z "$STRIPE_SECRET_KEY" ] || [ "$STRIPE_SECRET_KEY" = "sk_test_your_secret_key_here" ]; then
    echo "⚠️  Stripe keys not configured. Payment features will not work."
    echo "📝 Please update your .env file with actual Stripe test keys from https://stripe.com"
else
    echo "✅ Stripe keys configured"
fi

# Start the Flask development server
echo "🌟 Starting Flask app at http://127.0.0.1:5001"
echo "Press Ctrl+C to stop the server"
python app.py