#!/bin/bash
# Discord Transcript Bot - Setup & Launcher (Unix)

set -e

echo "🔧 Setting up Discord Transcript Bot..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Setup .env if not exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your DISCORD_TOKEN and SERVER_ID before running."
    echo "   You can edit now with: nano .env"
    read -p "   Press Enter to continue after editing, or Ctrl+C to abort..."
fi

# Create assets directory for local badge icons
mkdir -p assets

# Create transcripts directory
mkdir -p transcripts

# Run the bot
echo "🚀 Starting bot..."
python3 main.py