@echo off
setlocal enabledelayedexpansion

:: ── plotviz Windows package builder ──────────────────────────────────────────
:: Produces:
::   dist\plotviz\          — one-folder app (PyInstaller)
::   dist\plotviz-VERSION-setup.exe  — NSIS installer  (if makensis is on PATH)
::   dist\plotviz-VERSION-win.zip    — portable zip    (always)
::
:: Requirements:
::   uv      https://astral.sh/uv
::   NSIS    https://nsis.sourceforge.io  (optional — for .exe installer)
::
:: Usage (from repo root):
::   create_pkg_win.bat
:: ─────────────────────────────────────────────────────────────────────────────

:: Resolve repo root to the directory containing this script
set "ROOT_DIR=%~dp0"
set "ROOT_DIR=%ROOT_DIR:~0,-1%"
cd /d "%ROOT_DIR%"

echo.
echo ================================================
echo    plotviz Windows package builder
echo    Root : %ROOT_DIR%
echo ================================================

:: ── Check uv ─────────────────────────────────────────────────────────────────
where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found.
    echo         Install with:  winget install astral-sh.uv
    echo         or visit:      https://astral.sh/uv
    exit /b 1
)

for /f "tokens=*" %%v in ('uv --version') do set UV_VER=%%v
for /f "tokens=*" %%v in ('uv run python --version') do set PY_VER=%%v
echo    uv     : %UV_VER%
echo    Python : %PY_VER%

:: ── Read version ─────────────────────────────────────────────────────────────
for /f "tokens=*" %%v in ('uv run python -c "import sys, pathlib; sys.path.insert(0, str(pathlib.Path('src/plotviz'))); from config._version import __version__; print(__version__)"') do set VERSION=%%v
echo    Version: %VERSION%

:: ── Config ───────────────────────────────────────────────────────────────────
set "APP_NAME=plotviz"
set "SPEC_FILE=plotviz_win.spec"
set "DIST_DIR=dist"
set "ASSETS_DIR=assets"
set "ICON_ICO=%ASSETS_DIR%\plotviz.ico"
set "APP_DIR=%DIST_DIR%\%APP_NAME%"
set "EXE=%APP_DIR%\%APP_NAME%.exe"
set "ZIP_OUT=%DIST_DIR%\%APP_NAME%-%VERSION%-win.zip"
set "INSTALLER_OUT=%DIST_DIR%\%APP_NAME%-%VERSION%-setup.exe"
set "NSIS_SCRIPT=%DIST_DIR%\installer.nsi"

:: ── Sync dependencies ─────────────────────────────────────────────────────────
echo.
echo ^> Syncing dependencies...
uv sync
if errorlevel 1 ( echo [ERROR] uv sync failed & exit /b 1 )

for /f "tokens=*" %%v in ('uv run pyinstaller --version') do set PI_VER=%%v
echo.
echo ^> PyInstaller %PI_VER%

:: ── Convert .icns to .ico (Pillow) ───────────────────────────────────────────
echo.
echo ^> Converting app icon to .ico...
uv run python - << "PYEOF"
from PIL import Image
import io, struct, pathlib, sys

icns = pathlib.Path("assets/plotviz.icns")
ico  = pathlib.Path("assets/plotviz.ico")

if not icns.exists():
    print("  WARNING: plotviz.icns not found — skipping .ico conversion")
    sys.exit(0)

data = icns.read_bytes()
pos = 8
best, best_px = None, 0
while pos < len(data):
    size = struct.unpack(">I", data[pos+4:pos+8])[0]
    payload = data[pos+8:pos+size]
    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        img = Image.open(io.BytesIO(payload))
        if img.size[0] * img.size[1] > best_px:
            best, best_px = payload, img.size[0] * img.size[1]
    pos += size

if best is None:
    print("  WARNING: no PNG found in .icns — skipping .ico conversion")
    sys.exit(0)

src = Image.open(io.BytesIO(best)).convert("RGBA")
sizes = [16, 32, 48, 64, 128, 256]
imgs  = [src.resize((s, s), Image.LANCZOS) for s in sizes]
imgs[0].save(str(ico), format="ICO", sizes=[(s, s) for s in sizes],
             append_images=imgs[1:])
print(f"  plotviz.ico written ({len(sizes)} sizes)")
PYEOF

:: ── Generate Windows file-type icons (.ico) ──────────────────────────────────
echo.
echo ^> Generating file-type icons (.ico)...
uv run python - << "PYEOF"
from PIL import Image, ImageDraw, ImageFont
import io, struct, pathlib, sys

def extract_base(icns_path):
    data = icns_path.read_bytes()
    pos, best, best_px = 8, None, 0
    while pos < len(data):
        size = struct.unpack(">I", data[pos+4:pos+8])[0]
        payload = data[pos+8:pos+size]
        if payload[:8] == b"\x89PNG\r\n\x1a\n":
            img = Image.open(io.BytesIO(payload))
            if img.size[0]*img.size[1] > best_px:
                best, best_px = payload, img.size[0]*img.size[1]
        pos += size
    return Image.open(io.BytesIO(best)).convert("RGBA") if best else None

def make_doc_icon(base, banner_rgb, label):
    S = 256
    img  = Image.new("RGBA", (S, S), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    R, FOLD, BANNER_H = 16, 36, 40
    pl,pr,pt,pb = 8, S-8, 6, S-6
    draw.rounded_rectangle([pl,pt,pr,pb], radius=R,
                            fill=(255,255,255,255), outline=(200,200,210,255), width=2)
    fx, fy = pr-FOLD, pt+FOLD
    draw.polygon([(fx,pt),(pr,pt),(pr,fy)], fill=(0,0,0,0))
    draw.polygon([(fx,pt),(pr,fy),(fx,fy)], fill=(218,218,232,255))
    draw.line([(fx,pt),(fx,fy),(pr,fy)], fill=(175,175,200,255), width=2)
    draw.line([(fx,pt),(pr,fy)], fill=(200,200,215,255), width=2)
    art = base.copy(); art.thumbnail((fx-pl-12, pb-BANNER_H-pt-12), Image.LANCZOS)
    cx = pl+6+(fx-pl-12-art.width)//2; cy = pt+6+(pb-BANNER_H-pt-12-art.height)//2
    img.alpha_composite(art, (cx,cy))
    draw = ImageDraw.Draw(img)
    page_mask = Image.new("RGBA",(S,S),(0,0,0,0))
    ImageDraw.Draw(page_mask).rounded_rectangle([pl,pt,pr,pb],radius=R,fill=(255,255,255,255))
    banner = Image.new("RGBA",(S,S),(0,0,0,0))
    ImageDraw.Draw(banner).rectangle([pl,pb-BANNER_H,pr,pb],fill=(*banner_rgb,255))
    clipped = Image.new("RGBA",(S,S),(0,0,0,0))
    clipped.paste(banner, mask=page_mask.split()[3])
    img = Image.alpha_composite(img, clipped)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    except:
        font = ImageFont.load_default()
    bb = draw.textbbox((0,0), label, font=font)
    tw,th = bb[2]-bb[0], bb[3]-bb[1]
    tx = (pl+pr)//2 - tw//2
    ty = pb-BANNER_H + (BANNER_H-th)//2 - bb[1]
    draw.text((tx,ty), label, font=font, fill=(255,255,255,255))
    return img

icns = pathlib.Path("assets/plotviz.icns")
if not icns.exists():
    print("  WARNING: plotviz.icns not found — skipping file-type icons")
    sys.exit(0)

base = extract_base(icns)
if base is None:
    print("  WARNING: could not extract base art — skipping"); sys.exit(0)

TYPES = [
    ("pviz",  ( 52,120,220), ".pviz"),
    ("pvizt", (210,130, 20), ".pvizt"),
    ("pvizx", (140, 60,200), ".pvizx"),
]
ico_sizes = [16,32,48,64,128,256]
for stem, rgb, label in TYPES:
    icon256 = make_doc_icon(base, rgb, label)
    imgs = [icon256.resize((s,s), Image.LANCZOS) for s in ico_sizes]
    out = pathlib.Path(f"assets/{stem}.ico")
    imgs[0].save(str(out), format="ICO", sizes=[(s,s) for s in ico_sizes],
                 append_images=imgs[1:])
    print(f"  {out} written")
PYEOF

:: ── Generate Windows spec file ────────────────────────────────────────────────
echo.
echo ^> Writing %SPEC_FILE%...
uv run python - << "PYEOF"
import pathlib, textwrap

ROOT = pathlib.Path(".")
spec = textwrap.dedent(f"""
    # -*- mode: python ; coding: utf-8 -*-
    # plotviz_win.spec — PyInstaller spec for Windows
    # Auto-generated by create_pkg_win.bat — do not edit by hand.

    from pathlib import Path
    from PyInstaller.utils.hooks import collect_data_files, collect_submodules
    import importlib.util as _ilu

    _vspec = Path(SPECPATH) / 'src' / 'plotviz' / 'config' / '_version.py'
    _vmod  = _ilu.spec_from_file_location('_version', _vspec)
    _vm    = _ilu.module_from_spec(_vmod); _vmod.loader.exec_module(_vm)
    APP_VERSION = _vm.__version__

    ROOT_DIR = Path(SPECPATH)
    PKG_DIR  = ROOT_DIR / 'src' / 'plotviz'

    hidden_imports = [
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
        'PyQt6.QtPrintSupport', 'PyQt6.sip',
        'matplotlib', 'matplotlib.pyplot',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_agg',
        'matplotlib.backends.backend_svg',
        'matplotlib.backends.backend_pdf',
        'matplotlib.figure', 'matplotlib.ticker', 'matplotlib.colors',
        'matplotlib.cm', 'matplotlib.patches', 'matplotlib.lines',
        'matplotlib.collections', 'matplotlib.contour', 'matplotlib.image',
        'matplotlib.axes._axes', 'matplotlib.axes._base',
        'matplotlib.axes._secondary_axes',
        'mpl_toolkits', 'mpl_toolkits.mplot3d',
        'mpl_toolkits.mplot3d.axes3d', 'mpl_toolkits.mplot3d.art3d',
        'numpy', 'numpy.core._multiarray_umath', 'numpy.core.multiarray',
        'numpy.random', 'numpy.fft', 'numpy.linalg',
        'scipy', 'scipy.optimize', 'scipy.stats', 'scipy.interpolate',
        'scipy.special', 'scipy.linalg',
        'scipy._lib.messagestream', 'scipy._lib._util',
        'pandas',
        'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas', 'pandas._libs.tslibs.timestamps',
        'pandas._libs.tslibs.offsets', 'pandas._libs.tslibs.period',
        'pandas._libs.tslibs.timezones', 'pandas._libs.missing',
        'pandas.io.formats.style', 'pandas.io.excel._openpyxl',
        'openpyxl', 'openpyxl.cell._writer', 'openpyxl.styles',
        'openpyxl.reader.excel', 'openpyxl.writer.excel',
        'openpyxl.utils', 'openpyxl.utils.dataframe',
        'ui', 'ui.main_window', 'ui.tab_builders', 'ui.plot_engine',
        'ui.serialization', 'ui.canvas',
        'data', 'data.loader', 'data.scientific',
        'styling', 'styling.presets',
        'config', 'config.settings', 'config._version',
        'zipfile', 'json', 'tempfile', 'traceback',
        'multiprocessing', 'multiprocessing.pool',
        'winreg',
    ]

    hidden_imports += collect_submodules('matplotlib')
    hidden_imports += collect_submodules('mpl_toolkits')
    hidden_imports += collect_submodules('scipy')
    hidden_imports += collect_submodules('pandas')
    hidden_imports += collect_submodules('openpyxl')
    hidden_imports += collect_submodules('PyQt6')

    datas = []
    _assets = ROOT_DIR / 'assets'
    if _assets.exists():
        datas += [(str(_assets), 'assets')]
    datas += collect_data_files('matplotlib')
    datas += collect_data_files('mpl_toolkits')
    datas += collect_data_files('pandas')
    datas += collect_data_files('openpyxl')
    datas += collect_data_files('scipy')

    _ico = ROOT_DIR / 'assets' / 'plotviz.ico'
    _icon_arg = str(_ico) if _ico.exists() else None

    a = Analysis(
        [str(PKG_DIR / 'main.py')],
        pathex=[str(PKG_DIR)],
        binaries=[],
        datas=datas,
        hiddenimports=hidden_imports,
        hookspath=[],
        hooksconfig={{}},
        runtime_hooks=[],
        excludes=[
            'tkinter', '_tkinter',
            'PyQt5', 'PySide2', 'PySide6', 'wx', 'gi',
            'IPython', 'jupyter', 'notebook',
            'pytest', 'sphinx', 'docutils',
            'matplotlib.backends.backend_gtk3agg',
            'matplotlib.backends.backend_gtk3cairo',
            'matplotlib.backends.backend_wxagg',
            'matplotlib.backends.backend_tkagg',
            'matplotlib.backends.backend_nbagg',
            'matplotlib.backends._backend_tk',
        ],
        noarchive=False,
    )

    pyz = PYZ(a.pure, a.zipped_data)

    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='plotviz',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=_icon_arg,
        version_file=None,
    )

    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, upx_exclude=[],
        name='plotviz',
    )
""").lstrip()

pathlib.Path("plotviz_win.spec").write_text(spec, encoding="utf-8")
print("  plotviz_win.spec written")
PYEOF

:: ── Clean previous builds ─────────────────────────────────────────────────────
echo.
echo ^> Cleaning previous build...
if exist build     rmdir /s /q build
if exist "%DIST_DIR%\%APP_NAME%" rmdir /s /q "%DIST_DIR%\%APP_NAME%"

:: ── Build with PyInstaller ────────────────────────────────────────────────────
echo.
echo ^> Building %APP_NAME%.exe...
uv run pyinstaller "%SPEC_FILE%" --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    echo         Retry with: uv run pyinstaller %SPEC_FILE% --noconfirm --clean --log-level DEBUG
    exit /b 1
)

:: ── Verify build ─────────────────────────────────────────────────────────────
if not exist "%EXE%" (
    echo [ERROR] Build failed — %EXE% not found.
    exit /b 1
)
echo    %APP_NAME%.exe found.

:: ── Register file associations via reg files ─────────────────────────────────
:: We ship a .reg file in the bundle that the user can run (or the NSIS
:: installer applies automatically) to register .pviz / .pvizt / .pvizx.
echo.
echo ^> Writing file-association registry script...
uv run python - << "PYEOF"
import pathlib

reg = pathlib.Path("dist/plotviz/register_filetypes.reg")
content = r"""Windows Registry Editor Version 5.00

; plotviz file-type associations
; Double-click this file (or run as Administrator) to register.
; The NSIS installer applies these automatically.

; ── .pviz ────────────────────────────────────────────────────────────────────
[HKEY_CLASSES_ROOT\.pviz]
@="plotviz.Chart"

[HKEY_CLASSES_ROOT\plotviz.Chart]
@="plotviz Chart"

[HKEY_CLASSES_ROOT\plotviz.Chart\DefaultIcon]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"

[HKEY_CLASSES_ROOT\plotviz.Chart\shell\open\command]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""

; ── .pvizt ───────────────────────────────────────────────────────────────────
[HKEY_CLASSES_ROOT\.pvizt]
@="plotviz.Template"

[HKEY_CLASSES_ROOT\plotviz.Template]
@="plotviz Template"

[HKEY_CLASSES_ROOT\plotviz.Template\DefaultIcon]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"

[HKEY_CLASSES_ROOT\plotviz.Template\shell\open\command]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""

; ── .pvizx ───────────────────────────────────────────────────────────────────
[HKEY_CLASSES_ROOT\.pvizx]
@="plotviz.PaletteBundle"

[HKEY_CLASSES_ROOT\plotviz.PaletteBundle]
@="plotviz Palette Bundle"

[HKEY_CLASSES_ROOT\plotviz.PaletteBundle\DefaultIcon]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\",0"

[HKEY_CLASSES_ROOT\plotviz.PaletteBundle\shell\open\command]
@="\"C:\\Program Files\\plotviz\\plotviz.exe\" \"%1\""
"""
reg.write_text(content, encoding="utf-16")
print(f"  {reg} written")
PYEOF

:: ── Write NSIS installer script ───────────────────────────────────────────────
echo.
echo ^> Writing NSIS installer script...
uv run python - << "PYEOF"
import pathlib

version = open("src/plotviz/config/_version.py").read().split('"')[1]
app_dir = pathlib.Path("dist/plotviz")
nsi = pathlib.Path("dist/installer.nsi")

lines = [
    f'Name "plotviz {version}"',
    f'OutFile "plotviz-{version}-setup.exe"',
    'InstallDir "$PROGRAMFILES64\\plotviz"',
    'InstallDirRegKey HKLM "Software\\plotviz" "Install_Dir"',
    'RequestExecutionLevel admin',
    'SetCompressor /SOLID lzma',
    '',
    '!include "MUI2.nsh"',
    '!define MUI_ABORTWARNING',
    '!define MUI_ICON "..\\assets\\plotviz.ico"',
    '!define MUI_UNICON "..\\assets\\plotviz.ico"',
    '!insertmacro MUI_PAGE_WELCOME',
    '!insertmacro MUI_PAGE_DIRECTORY',
    '!insertmacro MUI_PAGE_INSTFILES',
    '!insertmacro MUI_PAGE_FINISH',
    '!insertmacro MUI_UNPAGE_CONFIRM',
    '!insertmacro MUI_UNPAGE_INSTFILES',
    '!insertmacro MUI_LANGUAGE "English"',
    '',
    'Section "plotviz (required)" SecMain',
    '  SectionIn RO',
    '  SetOutPath "$INSTDIR"',
    '  File /r "plotviz\\*.*"',
    '',
    '  ; Write uninstaller',
    '  WriteUninstaller "$INSTDIR\\Uninstall.exe"',
    '',
    '  ; Add/Remove Programs entry',
    '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "DisplayName"      "plotviz"',
    f'  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "DisplayVersion"   "{version}"',
    '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "UninstallString"  "$INSTDIR\\Uninstall.exe"',
    '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "InstallLocation"  "$INSTDIR"',
    '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "Publisher"        "Paulo Cachim"',
    '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "NoModify" 1',
    '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz" "NoRepair" 1',
    '',
    '  ; Start Menu shortcut',
    '  CreateDirectory "$SMPROGRAMS\\plotviz"',
    '  CreateShortcut  "$SMPROGRAMS\\plotviz\\plotviz.lnk" "$INSTDIR\\plotviz.exe"',
    '  CreateShortcut  "$SMPROGRAMS\\plotviz\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"',
    '',
    '  ; Desktop shortcut',
    '  CreateShortcut "$DESKTOP\\plotviz.lnk" "$INSTDIR\\plotviz.exe"',
    '',
    '  ; File associations — .pviz',
    '  WriteRegStr HKCR ".pviz"                          "" "plotviz.Chart"',
    '  WriteRegStr HKCR "plotviz.Chart"                  "" "plotviz Chart"',
    '  WriteRegStr HKCR "plotviz.Chart\\DefaultIcon"     "" "$INSTDIR\\assets\\pviz.ico"',
    '  WriteRegStr HKCR "plotviz.Chart\\shell\\open\\command" "" \'"$INSTDIR\\plotviz.exe" "%1"\'',
    '',
    '  ; File associations — .pvizt',
    '  WriteRegStr HKCR ".pvizt"                            "" "plotviz.Template"',
    '  WriteRegStr HKCR "plotviz.Template"                  "" "plotviz Template"',
    '  WriteRegStr HKCR "plotviz.Template\\DefaultIcon"     "" "$INSTDIR\\assets\\pvizt.ico"',
    '  WriteRegStr HKCR "plotviz.Template\\shell\\open\\command" "" \'"$INSTDIR\\plotviz.exe" "%1"\'',
    '',
    '  ; File associations — .pvizx',
    '  WriteRegStr HKCR ".pvizx"                               "" "plotviz.PaletteBundle"',
    '  WriteRegStr HKCR "plotviz.PaletteBundle"                "" "plotviz Palette Bundle"',
    '  WriteRegStr HKCR "plotviz.PaletteBundle\\DefaultIcon"   "" "$INSTDIR\\assets\\pvizx.ico"',
    '  WriteRegStr HKCR "plotviz.PaletteBundle\\shell\\open\\command" "" \'"$INSTDIR\\plotviz.exe" "%1"\'',
    '',
    '  ; Refresh shell icons',
    '  System::Call "shell32::SHChangeNotify(i 0x8000000, i 0, i 0, i 0)"',
    '',
    'SectionEnd',
    '',
    'Section "Uninstall"',
    '  Delete "$INSTDIR\\Uninstall.exe"',
    '  RMDir /r "$INSTDIR"',
    '  Delete "$SMPROGRAMS\\plotviz\\plotviz.lnk"',
    '  Delete "$SMPROGRAMS\\plotviz\\Uninstall.lnk"',
    '  RMDir  "$SMPROGRAMS\\plotviz"',
    '  Delete "$DESKTOP\\plotviz.lnk"',
    '  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\plotviz"',
    '  DeleteRegKey HKLM "Software\\plotviz"',
    '  DeleteRegKey HKCR ".pviz"',
    '  DeleteRegKey HKCR "plotviz.Chart"',
    '  DeleteRegKey HKCR ".pvizt"',
    '  DeleteRegKey HKCR "plotviz.Template"',
    '  DeleteRegKey HKCR ".pvizx"',
    '  DeleteRegKey HKCR "plotviz.PaletteBundle"',
    '  System::Call "shell32::SHChangeNotify(i 0x8000000, i 0, i 0, i 0)"',
    'SectionEnd',
]

nsi.write_text("\n".join(lines), encoding="utf-8")
print(f"  {nsi} written")
PYEOF

:: ── Build NSIS installer (if makensis available) ─────────────────────────────
echo.
where makensis >nul 2>&1
if errorlevel 1 (
    echo ^> makensis not found — skipping installer creation.
    echo    Install NSIS from https://nsis.sourceforge.io to build a setup.exe
) else (
    echo ^> Building NSIS installer...
    cd "%DIST_DIR%"
    makensis installer.nsi
    cd "%ROOT_DIR%"
    if exist "%INSTALLER_OUT%" (
        echo    %INSTALLER_OUT% created.
    ) else (
        echo    WARNING: NSIS ran but installer not found at %INSTALLER_OUT%
    )
)

:: ── Create portable zip ───────────────────────────────────────────────────────
echo.
echo ^> Creating portable zip...
if exist "%ZIP_OUT%" del "%ZIP_OUT%"

where powershell >nul 2>&1
if errorlevel 1 (
    where 7z >nul 2>&1
    if errorlevel 1 (
        echo    WARNING: Neither PowerShell nor 7-Zip found — skipping zip.
    ) else (
        7z a -tzip "%ZIP_OUT%" ".\%APP_DIR%\*" >nul
        echo    %ZIP_OUT% created via 7-Zip.
    )
) else (
    powershell -NoProfile -Command "Compress-Archive -Path '%APP_DIR%\*' -DestinationPath '%ZIP_OUT%' -Force"
    echo    %ZIP_OUT% created via PowerShell.
)

:: ── Final report ──────────────────────────────────────────────────────────────
echo.
echo ================================================
echo   Build succeeded
echo   EXE     : %EXE%
if exist "%INSTALLER_OUT%" echo   Installer: %INSTALLER_OUT%
if exist "%ZIP_OUT%"       echo   Portable : %ZIP_OUT%
echo.
echo   Test    : %EXE%
echo ================================================
