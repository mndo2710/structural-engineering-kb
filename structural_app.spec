# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the Structural Engineering Calculation Desktop App."""

from pathlib import Path

block_cipher = None
REPO_ROOT = Path(SPECPATH)

datas = [
    (str(REPO_ROOT / "config"), "config"),
    (str(REPO_ROOT / "database"), "database"),
    (str(REPO_ROOT / "procedures"), "procedures"),
    (str(REPO_ROOT / "gui" / "assets"), "gui/assets"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "openpyxl",
    "reportlab",
    "reportlab.graphics.shapes",
    "reportlab.platypus",
    "pandas",
    "numpy",
    "scipy",
    "keyring",
    "googleapiclient",
    "google_auth_oauthlib",
    "google.oauth2",
    "cloud",
    "cloud.drive_sync_service",
    "cloud.credential_store",
    "cloud.local_cache_manager",
    "sqlite3",
]

a = Analysis(
    [str(REPO_ROOT / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
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
    name="StructuralCalculationApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StructuralCalculationApp",
)
