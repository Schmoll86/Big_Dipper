#!/bin/bash

# Big Dipper Web Monitor - Stop Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Big Dipper Web Monitor...${NC}"
echo ""

# Stop backend
if pgrep -f "python.*app.py" > /dev/null; then
    pkill -f "app.py"
    echo -e "${GREEN}✓${NC} Stopped backend (Flask)"
else
    echo -e "${YELLOW}ℹ${NC} Backend not running"
fi

# Stop frontend
if pgrep -f "react-scripts start" > /dev/null; then
    pkill -f "react-scripts"
    echo -e "${GREEN}✓${NC} Stopped frontend (React)"
else
    echo -e "${YELLOW}ℹ${NC} Frontend not running"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
