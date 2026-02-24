#!/bin/bash
# Kill any existing processes
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 1

echo "=== Starting FastAPI Sentiment Analysis Server ==="
cd "$(dirname "$0")"

# Start FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8765 > server.log 2>&1 &
SERVER_PID=$!
echo "Server started (PID $SERVER_PID)"
sleep 3

# Check server is running
if ! curl -s http://localhost:8765/ > /dev/null 2>&1; then
    echo "❌ Server failed to start! Check server.log"
    cat server.log
    exit 1
fi
echo "✅ Server is running on http://localhost:8765"

# Start Cloudflare tunnel
cloudflared tunnel --url http://localhost:8765 > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "Tunnel started (PID $TUNNEL_PID). Waiting for URL..."
sleep 12

# Extract tunnel URL
TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Failed to get tunnel URL. Check tunnel.log:"
    cat tunnel.log
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "=================================================="
echo "🌐 Public URL: $TUNNEL_URL"
echo "📍 Endpoint : $TUNNEL_URL/comment"
echo ""
echo "Test it:"
echo "curl -X POST '$TUNNEL_URL/comment' -H 'Content-Type: application/json' -d '{\"comment\": \"This product is amazing!\"}'"
echo "=================================================="
echo ""
echo "⚠️  Keep this terminal open while grading!"
echo "Server PID: $SERVER_PID | Tunnel PID: $TUNNEL_PID"
