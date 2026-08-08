# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Order Book Simulator desktop app.
# Build from the project root with:
#   pyinstaller packaging/app.spec --noconfirm
import sys
from pathlib import Path

block_cipher = None

ROOT = Path(__file__).resolve().parent.parent
ICON_ICO = str(ROOT / "packaging" / "icon.ico")
ICON_PNG = str(ROOT / "packaging" / "icon.png")

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "packaging" / "icon.png"), "packaging"),
    ],
    hiddenimports=[
        "pyqtgraph",
        "pyqtgraph.graphicsItems",
        "numpy",
        "sortedcontainers",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OrderBookSimulator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_ICO if sys.platform.startswith("win") else ICON_PNG,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OrderBookSimulator",
)

# On macOS this also produces a proper .app bundle if ever built there.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="OrderBookSimulator.app",
        icon=ICON_ICO,
        bundle_identifier="com.ordersim.orderbooksimulator",
    )
