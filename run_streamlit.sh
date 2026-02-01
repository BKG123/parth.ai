#!/bin/bash

# Script to run Streamlit app with virtual environment

echo "🪶 Starting Parth AI Streamlit Interface..."

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating it..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    uv sync
fi

# Check if database is running
if ! docker-compose ps | grep -q "Up"; then
    echo "🐳 Starting database..."
    docker-compose up -d
    sleep 3
fi

# Run streamlit
echo "🚀 Launching Streamlit app..."
streamlit run app_streamlit.py
