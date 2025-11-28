#!/bin/bash

# ============================================
# adb-turbo - Cleanup Script
# Frees port 8765 and stops any running servers
# ============================================

PORT=8765

echo "🧹 Cleaning up adb-turbo..."

# Kill any running Flask servers
if pkill -f "python.*app.py" 2>/dev/null; then
    echo "✓ Stopped running server"
else
    echo "ℹ No running server found"
fi

# Check if port is in use and kill the process
PID=$(lsof -ti:${PORT} 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "✓ Killing process $PID using port ${PORT}"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# Verify port is free
if lsof -ti:${PORT} 2>/dev/null; then
    echo "⚠ Port ${PORT} is still in use"
    exit 1
else
    echo "✓ Port ${PORT} is now free"
fi

echo "✨ Cleanup complete!"

