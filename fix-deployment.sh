#!/bin/bash

# 🚀 Azure Deployment Quick Fix Script

echo "🔧 FlashStudio Azure Deployment Fix"
echo "=================================="

# Step 1: Check current files
echo "📁 Checking deployment files..."
if [ -f "startup.txt" ]; then
    echo "✅ startup.txt exists"
    cat startup.txt
else
    echo "❌ startup.txt missing - creating..."
    echo "gunicorn --bind=0.0.0.0 --timeout 600 app:app" > startup.txt
fi

if [ -f "wsgi.py" ]; then
    echo "✅ wsgi.py exists"
else
    echo "❌ wsgi.py missing - creating..."
    cat > wsgi.py << EOF
from app import app

if __name__ == "__main__":
    app.run()
EOF
fi

# Step 2: Test basic imports
echo ""
echo "🧪 Testing Flask app..."
export SECRET_KEY="test-secret-key"
export STRIPE_PUBLISHABLE_KEY="pk_test_example" 
export STRIPE_SECRET_KEY="sk_test_example"
export DATABASE_URL="sqlite:///test.db"

python -c "
try:
    from app import app
    print('✅ Flask app imports successfully')
    print('✅ App name:', app.name)
except Exception as e:
    print('❌ Flask import failed:', e)
"

# Step 3: Check requirements
echo ""
echo "📦 Checking requirements.txt..."
if pip install -r requirements.txt --dry-run > /dev/null 2>&1; then
    echo "✅ Requirements look good"
else
    echo "⚠️  Some requirements might have issues"
fi

# Step 4: Commit changes
echo ""
echo "📝 Ready to commit deployment fixes..."
echo ""
echo "Next steps:"
echo "1. Go to Azure Portal and get your app's publish profile"
echo "2. Add it as AZURE_WEBAPP_PUBLISH_PROFILE secret in GitHub"  
echo "3. Update the app name in .github/workflows/azure-deploy.yml"
echo "4. Run: git add . && git commit -m 'Fix deployment' && git push"
echo ""
echo "🎯 Your app URL will be: https://[your-app-name].azurewebsites.net"