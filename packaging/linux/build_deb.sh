#!/usr/bin/env bash
# Packages dist/OrderBookSimulator (produced by build_linux.sh) into a
# real installable Debian package using only dpkg-deb (no internet needed).
#
# Run from the project root:
#   ./packaging/linux/build_deb.sh
#
# Install the result with:
#   sudo dpkg -i packaging/linux/output/orderbooksimulator_1.0.0_amd64.deb
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="orderbooksimulator"
VERSION="1.0.0"
ARCH="amd64"
STAGE="packaging/linux/stage"
OUT_DIR="packaging/linux/output"

if [ ! -d "dist/OrderBookSimulator" ]; then
    echo "dist/OrderBookSimulator not found. Run ./build_linux.sh first." >&2
    exit 1
fi

rm -rf "$STAGE" "$OUT_DIR"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/opt/orderbooksimulator"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/pixmaps"
mkdir -p "$OUT_DIR"

cp -r dist/OrderBookSimulator/* "$STAGE/opt/orderbooksimulator/"
cp packaging/icon.png "$STAGE/opt/orderbooksimulator/icon.png"
cp packaging/icon.png "$STAGE/usr/share/pixmaps/orderbooksimulator.png"
cp packaging/linux/orderbooksimulator.desktop "$STAGE/usr/share/applications/orderbooksimulator.desktop"

# Symlink onto PATH so it can also be launched from a terminal
mkdir -p "$STAGE/usr/bin"
ln -sf /opt/orderbooksimulator/OrderBookSimulator "$STAGE/usr/bin/orderbooksimulator"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: finance
Priority: optional
Architecture: $ARCH
Maintainer: OrderBookSim <noreply@example.com>
Description: Order Book Simulator
 Live limit order book simulation with interactive charts and a
 strategy backtester, built on PySide6.
EOF

dpkg-deb --build --root-owner-group "$STAGE" "$OUT_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo
echo "==> Built $OUT_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "    Install with: sudo dpkg -i $OUT_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "    Uninstall with: sudo dpkg -r $APP_NAME"
