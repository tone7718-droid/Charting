# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 설정: pyinstaller TherapyChart.spec
# - 단일 EXE (--onefile 동등)
# - 콘솔창 숨김 (console=False)

a = Analysis(
    ['therapy_chart_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TherapyChart',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 실행 시 콘솔창이 나타나지 않음
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
