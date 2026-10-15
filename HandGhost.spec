# -*- mode: python ; coding: utf-8 -*-
# Build on each target OS; PyInstaller cannot cross-compile Windows/Linux bundles.
from PyInstaller.utils.hooks import collect_data_files
from pathlib import Path
import sys

# Standalone Python builds may keep Tcl/Tk outside the system loader paths.
tk_libraries = [(str(path), ".") for path in (Path(sys.base_prefix) / "lib").glob("libtcl*.so*")]

a = Analysis(
    ['main.py'], pathex=[], binaries=tk_libraries,
    datas=([(str(Path('src/eye/model_assets.json')), 'src/eye')] + collect_data_files('mediapipe', includes=['modules/**/*'])
           + collect_data_files('customtkinter')),
    hiddenimports=['PIL._tkinter_finder', 'torch.utils.model_zoo'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['IPython', 'pytest', 'tkinter.test'], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='HandGhost',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
)

# Folder bundle: avoid extracting the optional CPU frameworks at every launch.
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='HandGhost')
