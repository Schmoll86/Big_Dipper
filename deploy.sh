#!/bin/bash
# Quick deploy script - push changes and restart Docker on Mac Mini

echo "🚀 Little Dipper Deploy"
echo "======================="

# Configuration
MAC_MINI="mac-mini.local"  # or use IP address like "192.168.1.100"
REMOTE_USER="schmoll"
REMOTE_PATH="~/Desktop/Little_Dipper"

echo ""
echo "📝 Step 1: Pushing changes to GitHub..."
git add -A
git commit -m "Deploy changes from MacBook Air"
git push

if [ $? -ne 0 ]; then
    echo "❌ Git push failed. Check your changes and try again."
    exit 1
fi

echo ""
echo "✅ Changes pushed to GitHub"
echo ""
echo "📥 Step 2: Pulling changes on Mac Mini and restarting..."

ssh ${REMOTE_USER}@${MAC_MINI} << 'EOF'
cd ~/Desktop/Little_Dipper
git pull
docker-compose restart
echo ""
echo "✅ Container restarted with new code"
sleep 3
echo ""
echo "📊 Container status:"
docker ps | grep dipper
echo ""
echo "📝 Recent logs:"
docker logs --tail 10 little-dipper
EOF

echo ""
echo "✅ Deploy complete!"
echo ""
echo "📊 To monitor logs: ssh ${REMOTE_USER}@${MAC_MINI} 'docker logs -f little-dipper'"
