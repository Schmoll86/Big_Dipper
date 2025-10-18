#!/bin/bash
# Little Dipper - Quick Setup Script

set -e

echo "🌙 Little Dipper Setup"
echo "====================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo
    echo "⚠️  No .env file found"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo
    echo "🔑 IMPORTANT: Edit .env with your Alpaca credentials:"
    echo "   ALPACA_KEY=your_api_key"
    echo "   ALPACA_SECRET=your_secret_key"
    echo
else
    echo "✓ .env file exists"
fi

# Run tests
echo
echo "Running tests..."
python test_dip_logic.py
echo

echo "====================="
echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "  1. Edit .env with your Alpaca credentials"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python main.py"
echo
echo "Or use Docker:"
echo "  docker-compose up -d"
echo