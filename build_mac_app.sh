#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must be run on macOS to build a .app bundle."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: python3 not found. Install Python 3.11+ (e.g., brew install python@3.11)."
  exit 1
fi

echo "==> Creating build virtual environment (.venv_mac)..."
"$PYTHON_BIN" -m venv .venv_mac
source .venv_mac/bin/activate

echo "==> Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt pywebview pyinstaller

echo "==> Building dist/ProductImageHelper.app..."
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name "ProductImageHelper" \
  --add-data "static:static" \
  --collect-all rembg \
  --collect-all pymatting \
  --collect-all onnxruntime \
  desktop_app.py

echo ""
echo "Build complete!"
echo "App bundle created at: $(pwd)/dist/ProductImageHelper.app"
echo "You can drag ProductImageHelper.app into your /Applications folder."
echo "Note: On first launch, the AI model (~973MB for BiRefNet) will download to:"
echo "  ~/Library/Application Support/ProductImageHelper/models/"
