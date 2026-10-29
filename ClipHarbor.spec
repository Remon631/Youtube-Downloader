# PyInstaller spec for Apple Silicon macOS. Build on the target Mac.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path.cwd()
ffmpeg = project / "bin" / "ffmpeg"
qjs = project / "bin" / "qjs"
icon_file = project / "logo" / "RYD.icns"
binaries = []
datas = []
if ffmpeg.exists():
    binaries.append((str(ffmpeg), "bin"))
    datas.append((str(ffmpeg), "bin"))
if qjs.exists():
    binaries.append((str(qjs), "bin"))
    datas.append((str(qjs), "bin"))
logo_dir = project / "logo"
if logo_dir.exists():
    datas.append((str(logo_dir), "logo"))

yt_datas, yt_binaries, yt_hidden = collect_all("yt_dlp")
datas += yt_datas
binaries += yt_binaries

# Qt/PySide6 plugin collection is handled by PyInstaller's hooks.
a = Analysis(
    ["clipharbor.py"],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["yt_dlp", "yt_dlp.cookies", "yt_dlp.postprocessor", "PySide6.QtSvg", "PySide6.QtNetwork"] + yt_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Remon YT Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Remon YT Downloader",
)
app = BUNDLE(
    coll,
    name="Remon YT Downloader.app",
    icon=str(icon_file) if icon_file.exists() else None,
    bundle_identifier="com.remon.ytdownloader",
    version="3.0.1",
    info_plist={
        "CFBundleName": "Remon YT Downloader",
        "CFBundleDisplayName": "Remon YT Downloader",
        "CFBundleIdentifier": "com.remon.ytdownloader",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        "CFBundleExecutable": "Remon YT Downloader",
        "CFBundleIconFile": "RYD.icns",
        "CFBundleShortVersionString": "3.0.1",
        "CFBundleVersion": "3.0.1",
        "CFBundleSupportedPlatforms": ["MacOSX"],
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.video",
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticGraphicsSwitching": True,
    },
)
