#!/bin/bash

# Big Dipper Web Monitor - Complete Startup Script
# This script stops any running instances and starts both backend and frontend

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Big Dipper Web Monitor Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}✗${NC} .env file not found!"
    exit 1
fi

# Step 1: Stop any running instances
echo ""
echo -e "${YELLOW}Step 1: Stopping existing processes...${NC}"

# Stop backend
if pgrep -f "python.*app.py" > /dev/null; then
    pkill -f "app.py"
    echo -e "  ${GREEN}✓${NC} Stopped backend (Flask)"
else
    echo -e "  ${BLUE}ℹ${NC} Backend not running"
fi

# Stop frontend
if pgrep -f "react-scripts start" > /dev/null; then
    pkill -f "react-scripts"
    echo -e "  ${GREEN}✓${NC} Stopped frontend (React)"
else
    echo -e "  ${BLUE}ℹ${NC} Frontend not running"
fi

# Wait for processes to fully stop
sleep 2

# Step 2: Start Backend
echo ""
echo -e "${YELLOW}Step 2: Starting backend...${NC}"

cd "$SCRIPT_DIR/backend"

# Verify Python dependencies
if ! python3 -c "import flask; import flask_cors; import alpaca" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} Python dependencies missing!"
    echo -e "  Run: ${YELLOW}pip install -r requirements.txt${NC}"
    exit 1
fi

# Start backend in background
python3 app.py > /tmp/big_dipper_backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo -ne "  Waiting for backend to start"
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
        echo -e "\n  ${GREEN}✓${NC} Backend running on http://localhost:5001"
        echo -e "  ${BLUE}ℹ${NC} Backend PID: $BACKEND_PID"
        echo -e "  ${BLUE}ℹ${NC} Logs: tail -f /tmp/big_dipper_backend.log"
        break
    fi
    echo -n "."
    if [ $i -eq 10 ]; then
        echo -e "\n  ${RED}✗${NC} Backend failed to start!"
        echo -e "  Check logs: cat /tmp/big_dipper_backend.log"
        exit 1
    fi
done

# Step 3: Start Frontend
echo ""
echo -e "${YELLOW}Step 3: Starting frontend...${NC}"

cd "$SCRIPT_DIR/frontend"

# Verify node_modules
if [ ! -d "node_modules" ]; then
    echo -e "  ${RED}✗${NC} node_modules not found!"
    echo -e "  Run: ${YELLOW}npm install${NC}"
    exit 1
fi

# Start frontend in background
PORT=3000 npm start > /tmp/big_dipper_frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to compile
echo -ne "  Waiting for frontend to compile"
for i in {1..30}; do
    sleep 1
    if grep -q "Compiled successfully" /tmp/big_dipper_frontend.log 2>/dev/null; then
        echo -e "\n  ${GREEN}✓${NC} Frontend running on http://localhost:3000"
        echo -e "  ${BLUE}ℹ${NC} Frontend PID: $FRONTEND_PID"
        echo -e "  ${BLUE}ℹ${NC} Logs: tail -f /tmp/big_dipper_frontend.log"
        break
    fi

    # Check for errors
    if grep -q "Failed to compile" /tmp/big_dipper_frontend.log 2>/dev/null; then
        echo -e "\n  ${RED}✗${NC} Frontend failed to compile!"
        echo -e "  Check logs: cat /tmp/big_dipper_frontend.log"
        exit 1
    fi

    echo -n "."
    if [ $i -eq 30 ]; then
        echo -e "\n  ${YELLOW}⚠${NC} Frontend taking longer than expected..."
        echo -e "  Check logs: tail -f /tmp/big_dipper_frontend.log"
        break
    fi
done

# Step 4: Final Status
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Web Monitor Started Successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "📊 Dashboard:  ${GREEN}http://localhost:3000${NC}"
echo -e "🔌 API:        ${GREEN}http://localhost:5001/api${NC}"
echo ""
echo -e "📝 Logs:"
echo -e "   Backend:  tail -f /tmp/big_dipper_backend.log"
echo -e "   Frontend: tail -f /tmp/big_dipper_frontend.log"
echo ""
echo -e "🛑 Stop:"
echo -e "   pkill -f 'app.py'"
echo -e "   pkill -f 'react-scripts'"
echo ""
echo -e "${YELLOW}Opening browser in 3 seconds...${NC}"
sleep 3

# Open browser (macOS)
if command -v open &> /dev/null; then
    open http://localhost:3000
fi

echo ""
echo -e "${GREEN}Done! Check your browser.${NC}"
echo ""
