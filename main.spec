# -*- mode: python ; coding: utf-8 -*-

import re

# Derive the exe file name from the VERSION defined in main.py, e.g.
# VERSION = "v1.4"  ->  "STXi EEPROM Installer V1.4.exe"
with open('main.py', encoding='utf-8') as _f:
    _version = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', _f.read()).group(1)
EXE_NAME = f'STXi EEPROM Installer V{_version.lstrip("vV")}'


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('stxi_ethercat_logo.png', '.'), ('STXI_logo_2021.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='stxi_ethercat_logo.ico',
)

# Remove the intermediate build/ folder once the exe has been produced.
import shutil
shutil.rmtree('build', ignore_errors=True)
