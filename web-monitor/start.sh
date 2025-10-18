#!/bin/bash

# Big Dipper Web Monitor - Quick Start Script

echo "🎯 Big Dipper Web Monitor Setup"
echo "================================"

# Check if .env exists
if [ ! -f ../.env ]; then
    echo "⚠️  Warning: ../.env file not found"
    echo "Please ensure your Alpaca credentials are in Big Dipper's .env file"
    exit 1
fi

# Copy .env from parent directory
echo "📋 Copying environment variables..."
cp ../.env .env

# Create data directory if it doesn't exist
echo "📁 Creating data directory..."
mkdir -p data

# Build and start the backend
echo "🏗️  Building Docker container..."
docker-compose build

echo "🚀 Starting the monitor backend..."
docker-compose up -d

echo ""
echo "✅ Backend is starting up!"
echo ""
echo "Check status with:"
echo "  docker-compose ps"
echo ""
echo "View logs with:"
echo "  docker-compose logs -f monitor-backend"
echo ""
echo "Test the API:"
echo "  curl http://localhost:5000/api/health"
echo "  curl http://localhost:5000/api/dashboard"
echo ""
echo "Stop with:"
echo "  docker-compose down"
echo ""
echo "📊 The backend API is available at http://localhost:5000"
echo ""
echo "Next steps:"
echo "1. Test the API endpoints"
echo "2. Set up the React frontend in the 'frontend' directory"
echo "3. Add beautiful visualizations!"