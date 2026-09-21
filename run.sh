#!/usr/bin/env bash
# LAND AI - quick start (macOS/Linux)
set -e
cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
echo ""
echo "Starting LAND AI at http://127.0.0.1:5000"
python app.py
