#!/bin/bash
# Quick API test script

echo "🧪 Testing Daily Sync API..."
echo ""

# Check if server is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is running"
    echo ""
    
    # Test root endpoint
    echo "📡 Testing root endpoint:"
    curl -s http://localhost:8000/ | python -m json.tool
    echo ""
    
    # Test health endpoint
    echo "📡 Testing health endpoint:"
    curl -s http://localhost:8000/health | python -m json.tool
    echo ""
    
    # Test text ingestion
    echo "📡 Testing text ingestion:"
    curl -s -X POST "http://localhost:8000/ingest/text" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "text=This is a test message for the Daily Sync system." | python -m json.tool
    echo ""
    
    echo "✅ All tests completed!"
else
    echo "❌ Server is not running. Start it with: python main.py"
    exit 1
fi
