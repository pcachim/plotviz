# -*- mode: python ; coding: utf-8 -*-
"""
xd-chart.spec — PyInstaller spec for macOS .app bundle
Location: ~/xd-chart/xd-chart.spec  (repo root)

Build:
    cd ~/xd-chart
    bash build_macos.sh
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import importlib.util as _ilu

# Read version from the single source of truth
_vspec = Path(SPECPATH) / 'src' / 'xd-chart' / 'config' / '_version.py'  # noqa: F821
_vmod  = _ilu.spec_from_file_location('_version', _vspec)
_vm    = _ilu.module_from_spec(_vmod); _vmod.loader.exec_module(_vm)
APP_VERSION = _vm.__version__

# SPECPATH = ~/xd-chart/ (where this spec lives)
ROOT_DIR = Path(SPECPATH)                          # noqa: F821
PKG_DIR  = ROOT_DIR / 'src' / 'xd-chart'          # where ui/, data/, styling/ live

hidden_imports = [
    # Qt
    'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
    'PyQt6.QtPrintSupport', 'PyQt6.sip',
    # Matplotlib
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
    # numpy
    'numpy', 'numpy.core._multiarray_umath', 'numpy.core.multiarray',
    'numpy.random', 'numpy.fft', 'numpy.linalg',
    # scipy
    'scipy', 'scipy.optimize', 'scipy.stats', 'scipy.interpolate',
    'scipy.special', 'scipy.linalg',
    'scipy._lib.messagestream', 'scipy._lib._util',
    # pandas
    'pandas',
    'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timedeltas', 'pandas._libs.tslibs.timestamps',
    'pandas._libs.tslibs.offsets', 'pandas._libs.tslibs.period',
    'pandas._libs.tslibs.timezones', 'pandas._libs.missing',
    'pandas.io.formats.style', 'pandas.io.excel._openpyxl',
    # openpyxl
    'openpyxl', 'openpyxl.cell._writer', 'openpyxl.styles',
    'openpyxl.reader.excel', 'openpyxl.writer.excel',
    'openpyxl.utils', 'openpyxl.utils.dataframe',
    # App packages
    'ui', 'ui.main_window', 'ui.tab_builders', 'ui.plot_engine',
    'ui.serialization', 'ui.canvas',
    'data', 'data.loader', 'data.scientific',
    'styling', 'styling.presets',
    'config', 'config.settings', 'config._version',
    # stdlib
    'zipfile', 'json', 'tempfile', 'traceback',
    'multiprocessing', 'multiprocessing.pool',
]

hidden_imports += collect_submodules('matplotlib')
hidden_imports += collect_submodules('mpl_toolkits')
hidden_imports += collect_submodules('scipy')
hidden_imports += collect_submodules('pandas')
hidden_imports += collect_submodules('openpyxl')
hidden_imports += collect_submodules('PyQt6')

datas = []
# Bundle the assets folder (icon etc.) if it exists
_assets = ROOT_DIR / 'assets'
if _assets.exists():
    datas += [(str(_assets), 'assets')]
datas += collect_data_files('matplotlib')
datas += collect_data_files('mpl_toolkits')
datas += collect_data_files('pandas')
datas += collect_data_files('openpyxl')
datas += collect_data_files('scipy')

a = Analysis(
    [str(PKG_DIR / 'main.py')],
    pathex=[str(PKG_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
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
    name='xd-chart',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,   # set to 'entitlements.plist' when signing
    icon=str(ROOT_DIR / 'assets' / 'xd-chart.icns') if (ROOT_DIR / 'assets' / 'xd-chart.icns').exists() else None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name='xd-chart',
)

app = BUNDLE(
    coll,
    name='xd-chart.app',
    icon=str(ROOT_DIR / 'assets' / 'xd-chart.icns') if (ROOT_DIR / 'assets' / 'xd-chart.icns').exists() else None,
    bundle_identifier='com.xdchart.app',
    version=APP_VERSION,
    info_plist={
        'CFBundleName':               'xd-chart',
        'CFBundleDisplayName':        'xd-chart',
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion':            APP_VERSION,
        'CFBundleIdentifier':         'com.xdchart.app',
        'CFBundleExecutable':         'xd-chart',
        'CFBundlePackageType':        'APPL',
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName':       'xd-chart Document',
            'CFBundleTypeExtensions': ['xdchart'],
            'CFBundleTypeRole':       'Editor',
            'LSHandlerRank':          'Owner',
        }],
        'LSMinimumSystemVersion':     '11.0',
        'LSApplicationCategoryType':  'public.app-category.productivity',
        'NSHighResolutionCapable':    True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSDocumentsFolderUsageDescription':
            'xd-chart needs access to open and save chart files.',
        'NSDownloadsFolderUsageDescription':
            'xd-chart needs access to open files from Downloads.',
        'NSDesktopFolderUsageDescription':
            'xd-chart needs access to files on the Desktop.',
    },
)
