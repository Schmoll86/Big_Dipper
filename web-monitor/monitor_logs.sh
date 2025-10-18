#!/bin/bash

# Log Monitoring Script - Checks every 10 minutes
# Run with: ./monitor_logs.sh

BACKEND_LOG="/tmp/backend.log"
FRONTEND_LOG="/tmp/frontend.log"
MONITOR_INTERVAL=600  # 10 minutes in seconds

echo "🔍 Starting log monitor (checking every 10 minutes)"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Log Check: $TIMESTAMP"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check if processes are running
    if ! pgrep -f "app.py" > /dev/null; then
        echo "❌ Backend NOT running!"
    else
        echo "✅ Backend running (PID: $(pgrep -f 'app.py'))"
    fi

    if ! pgrep -f "react-scripts" > /dev/null; then
        echo "❌ Frontend NOT running!"
    else
        echo "✅ Frontend running (PID: $(pgrep -f 'react-scripts' | head -1))"
    fi

    echo ""

    # Check backend health
    HEALTH=$(curl -s http://localhost:5001/api/health 2>&1)
    if echo "$HEALTH" | grep -q "healthy"; then
        echo "✅ Backend health: OK"
    else
        echo "❌ Backend health: FAILED"
        echo "   Response: $HEALTH"
    fi

    echo ""
    echo "📝 Backend Log Analysis:"

    # Count errors in last 10 minutes
    BACKEND_ERRORS=$(tail -1000 "$BACKEND_LOG" 2>/dev/null | grep -i "ERROR" | wc -l | tr -d ' ')
    if [ "$BACKEND_ERRORS" -gt 0 ]; then
        echo "   ⚠️  $BACKEND_ERRORS errors found:"
        tail -1000 "$BACKEND_LOG" 2>/dev/null | grep -i "ERROR" | tail -5 | sed 's/^/      /'
    else
        echo "   ✅ No errors in recent logs"
    fi

    # Check for database issues
    DB_ERRORS=$(tail -1000 "$BACKEND_LOG" 2>/dev/null | grep -i "database\|sqlite" | grep -i "error" | wc -l | tr -d ' ')
    if [ "$DB_ERRORS" -gt 0 ]; then
        echo "   ⚠️  Database errors detected!"
    fi

    # Check API response times
    echo ""
    echo "   Recent API calls:"
    tail -100 "$BACKEND_LOG" 2>/dev/null | grep "GET /" | tail -3 | sed 's/^/      /'

    echo ""
    echo "📝 Frontend Log Analysis:"
    FRONTEND_ERRORS=$(tail -1000 "$FRONTEND_LOG" 2>/dev/null | grep -i "error\|failed" | wc -l | tr -d ' ')
    if [ "$FRONTEND_ERRORS" -gt 0 ]; then
        echo "   ⚠️  $FRONTEND_ERRORS errors/warnings found"
    else
        echo "   ✅ No errors in recent logs"
    fi

    # Test dashboard endpoint
    echo ""
    echo "🔌 Testing Dashboard API:"
    DASHBOARD_TEST=$(curl -s http://localhost:5001/api/dashboard 2>&1)
    if echo "$DASHBOARD_TEST" | grep -q "account"; then
        POSITIONS=$(echo "$DASHBOARD_TEST" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d['positions']))" 2>/dev/null || echo "?")
        EQUITY=$(echo "$DASHBOARD_TEST" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"\${d['account']['equity']:.2f}\")" 2>/dev/null || echo "?")
        echo "   ✅ Dashboard responding"
        echo "   📊 Positions: $POSITIONS"
        echo "   💰 Equity: $EQUITY"
    else
        echo "   ❌ Dashboard not responding correctly"
    fi

    echo ""
    echo "⏰ Next check in 10 minutes..."
    echo ""

    sleep $MONITOR_INTERVAL
done
