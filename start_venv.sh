#!/bin/bash

# FlashStudio Flask App Starter Script using Virtual Environment
# This script ensures we use the virtual environment Python

echo "🚀 Starting FlashStudio with Virtual Environment..."
echo "📍 Working Directory: $(pwd)"
echo "🐍 Using Python: /home/vboxuser/FlashStudio-main/venv/bin/python"

# Kill any existing Flask processes
echo "🔄 Stopping any existing Flask processes..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1

# Check if virtual environment exists
if [ ! -f "/home/vboxuser/FlashStudio-main/venv/bin/python" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Test Flask app import
echo "🔍 Testing Flask app import..."
/home/vboxuser/FlashStudio-main/venv/bin/python -c "from app import app; print('✅ Flask app imports successfully')" || {
    echo "❌ Flask app import failed!"
    exit 1
}

# Check database
if [ ! -f "instance/filmcompany.db" ]; then
    echo "⚠️  Database not found at instance/filmcompany.db"
    echo "🔄 Running migration..."
    /home/vboxuser/FlashStudio-main/venv/bin/python migrate_reviews.py
fi

# Start Flask app
echo "🌟 Starting Flask application..."
echo "📱 Access your app at: http://127.0.0.1:5001/"
echo "⚙️  Admin Reviews at: http://127.0.0.1:5001/admin/reviews"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================="

/home/vboxuser/FlashStudio-main/venv/bin/python app.py