#!/bin/bash
# Script to start the server with ngrok

echo "🚀 Starting Daily Sync with ngrok..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed!"
    echo ""
    echo "Install it with:"
    echo "  brew install ngrok"
    echo ""
    echo "Or download from: https://ngrok.com/download"
    exit 1
fi

# Check if server is already running
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stopping existing server..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# Start the server in background
echo "📡 Starting FastAPI server..."
cd "$(dirname "$0")"
source venv/bin/activate
nohup python main.py > /tmp/daily_sync.log 2>&1 &
SERVER_PID=$!
echo "✅ Server started (PID: $SERVER_PID)"

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
sleep 3

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server failed to start. Check /tmp/daily_sync.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Server is ready!"
echo ""

# Start ngrok
echo "🌐 Starting ngrok tunnel..."
echo ""
echo "=========================================="
echo "  Your app will be available at:"
echo "  https://XXXXX.ngrok-free.app"
echo "  (Check the ngrok output below)"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop both server and ngrok"
echo ""

# Start ngrok (this will block)
ngrok http 8000

# Cleanup on exit
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID 2>/dev/null
echo "✅ Done!"
