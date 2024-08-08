# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/config.ini','./'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/Assets/no-signal-icon-black.jpg','./Assets'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/UI/BroadCast.ui','./UI'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/UI/monit_widget.ui','./UI'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/UI/RTSP_Address.ui','./Dialog/UI'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/UI/Set_Channel.ui','./Dialog/UI'),
    ('C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/Assets/icon.ico','./'),
    ],
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
    [],
    exclude_binaries=True,
    name='OnePersonBroadcast',
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
    icon='C:/Users/kangchul/PycharmProjects/OnePersonBroadcase/Assets/icon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OnePersonBroadCast',
)
