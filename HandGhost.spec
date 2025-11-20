# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# --- Function to get package path ---
def get_package_path(package_name):
    try:
        import importlib
        return Path(importlib.util.find_spec(package_name).origin).parent
    except Exception as e:
        print(f"Error getting path for {package_name}: {e}")
        return None

# --- Find package paths ---
mediapipe_path = get_package_path("mediapipe")
customtkinter_path = get_package_path("customtkinter")

# --- Prepare data files ---
datas_to_include = []
if mediapipe_path:
    datas_to_include.extend([
        (str(mediapipe_path / 'modules/hand_landmark'), 'mediapipe/modules/hand_landmark'),
        (str(mediapipe_path / 'modules/palm_detection'), 'mediapipe/modules/palm_detection')
    ])
if customtkinter_path:
    datas_to_include.append(
        (str(customtkinter_path / 'assets'), 'customtkinter/assets')
    )

# --- PyInstaller Analysis ---
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas_to_include,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# --- EXE for one-file build ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HandGhost',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
