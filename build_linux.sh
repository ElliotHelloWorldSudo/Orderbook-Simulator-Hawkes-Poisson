#!/usr/bin/env bash
# Build a standalone Linux binary (onedir) with PyInstaller.
# Run this ON LINUX from the project root:
#   ./build_linux.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Creating virtual environment (.venv)"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Cleaning previous build artifacts"
rm -rf build dist

echo "==> Running PyInstaller"
pyinstaller packaging/app.spec --noconfirm

echo
echo "==> Build complete."
echo "    Standalone app folder: dist/OrderBookSimulator/"
echo "    Launch it with:        dist/OrderBookSimulator/OrderBookSimulator"
echo
echo "==> To produce an installable .deb package, run:"
echo "    ./packaging/linux/build_deb.sh"
