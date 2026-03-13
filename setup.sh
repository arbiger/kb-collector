#!/bin/bash
# KB Collector Setup Script

echo "=== KB Collector Setup ==="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it first."
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install it first."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check for system dependencies
echo "Checking system dependencies..."

if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ ffmpeg is not installed. This is required for YouTube audio extraction."
    echo "Install it with: brew install ffmpeg"
fi

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️ Please edit .env and add your API keys and vault path."
fi

echo "=== Setup Complete! ==="
