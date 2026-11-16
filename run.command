#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d "venv" ]]; then
  echo "First-time setup: creating Python virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

PORT=5055
echo "========================================================"
echo " Product Image Helper - 600x600 Formatter"
echo " Opening http://127.0.0.1:${PORT} in your browser..."
echo "========================================================"

(sleep 1 && open "http://127.0.0.1:${PORT}") &
python app.py "${PORT}"
