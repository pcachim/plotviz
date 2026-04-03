"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.

ui/code_runner.py  –  plotviz
Python Code Runner: a QDialog that lets users write or load arbitrary Python
code to produce a matplotlib / seaborn chart, then renders it in a live canvas.
"""

from __future__ import annotations

import io
import logging
import traceback
import textwrap
import types

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QPushButton, QLabel, QFileDialog, QMessageBox, QSizePolicy,
    QSpinBox, QPlainTextEdit, QFrame,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QSyntaxHighlighter, QTextCharFormat,
    QKeySequence, QShortcut,
)

import re

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

log = logging.getLogger('plotviz')

# ── Sample code shown on first open ──────────────────────────────────────────

_SAMPLE_CODE = textwrap.dedent("""\
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns

    # ── Data ─────────────────────────────────────────────────────────────────
    rng = np.random.default_rng(42)
    x   = np.linspace(0, 2 * np.pi, 300)
    y1  = np.sin(x) + rng.normal(0, 0.08, len(x))
    y2  = np.cos(x) + rng.normal(0, 0.08, len(x))

    # ── Figure ───────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle('Python Code Runner — sample chart', fontsize=13, y=1.02)

    # Left: line plot
    axes[0].plot(x, y1, label='sin(x)', linewidth=1.8)
    axes[0].plot(x, y2, label='cos(x)', linewidth=1.8, linestyle='--')
    axes[0].set_title('Trigonometric functions')
    axes[0].set_xlabel('x'); axes[0].set_ylabel('y')
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    # Right: seaborn KDE
    data = rng.standard_normal((200, 2))
    import pandas as pd
    df = pd.DataFrame(data, columns=['A', 'B'])
    sns.kdeplot(data=df, x='A', y='B', ax=axes[1], fill=True, cmap='Blues')
    axes[1].set_title('2-D KDE (seaborn)')

    fig.tight_layout()
""")

# ── Minimal Python syntax highlighter ────────────────────────────────────────

class _PythonHighlighter(QSyntaxHighlighter):
    """Lightweight syntax colouring for the code editor."""

    _RULES: list[tuple[re.Pattern, QTextCharFormat]] = []

    def __init__(self, document):
        super().__init__(document)
        if not _PythonHighlighter._RULES:
            _PythonHighlighter._RULES = self._build_rules()

    @staticmethod
    def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(700)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    @classmethod
    def _build_rules(cls) -> list[tuple[re.Pattern, QTextCharFormat]]:
        kw_fmt    = cls._fmt('#569cd6', bold=True)   # blue  – keywords
        builtin_fmt = cls._fmt('#4ec9b0')            # teal  – builtins
        str_fmt   = cls._fmt('#ce9178')              # orange – strings
        num_fmt   = cls._fmt('#b5cea8')              # green  – numbers
        cmt_fmt   = cls._fmt('#6a9955', italic=True) # green  – comments
        dec_fmt   = cls._fmt('#dcdcaa')              # yellow – decorators
        func_fmt  = cls._fmt('#dcdcaa')              # yellow – def names

        keywords = (
            'False|None|True|and|as|assert|async|await|break|class|continue|'
            'def|del|elif|else|except|finally|for|from|global|if|import|in|'
            'is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield'
        )
        builtins = (
            'abs|all|any|bin|bool|bytes|callable|chr|dict|dir|divmod|enumerate|'
            'eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|'
            'hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|'
            'locals|map|max|min|next|object|oct|open|ord|pow|print|property|'
            'range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|'
            'str|sum|super|tuple|type|vars|zip'
        )
        return [
            (re.compile(r'#[^\n]*'),                                      cmt_fmt),
            (re.compile(r'@\w+'),                                         dec_fmt),
            (re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL),        str_fmt),
            (re.compile(r'"[^"\n]*"|\'[^\'\n]*\''),                      str_fmt),
            (re.compile(r'\b(?:' + keywords + r')\b'),                   kw_fmt),
            (re.compile(r'\b(?:' + builtins + r')\b'),                   builtin_fmt),
            (re.compile(r'\bdef\s+(\w+)'),                               func_fmt),   # matched via group
            (re.compile(r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[jJ]?\b'),   num_fmt),
        ]

    def highlightBlock(self, text: str):
        for pattern, fmt in self._RULES:
            for m in pattern.finditer(text):
                start = m.start(1) if m.lastindex else m.start()
                length = len(m.group(1)) if m.lastindex else len(m.group())
                self.setFormat(start, length, fmt)


# ── Code editor widget ────────────────────────────────────────────────────────

class _CodeEditor(QPlainTextEdit):
    """Monospaced editor with Tab→4-spaces and Shift+Tab→dedent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont('Menlo', 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setTabStopDistance(32)   # ~4 chars
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        _PythonHighlighter(self.document())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._indent_selection(cursor, dedent=False)
            else:
                cursor.insertText('    ')
            return
        if event.key() == Qt.Key.Key_Backtab:
            cursor = self.textCursor()
            self._indent_selection(cursor, dedent=True)
            return
        super().keyPressEvent(event)

    def _indent_selection(self, cursor, dedent: bool):
        start = cursor.selectionStart()
        end   = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        block_text = cursor.selectedText().replace('\u2029', '\n')
        lines = block_text.split('\n')
        if dedent:
            new_lines = [l[4:] if l.startswith('    ') else l.lstrip('\t') for l in lines]
        else:
            new_lines = ['    ' + l for l in lines]
        cursor.insertText('\n'.join(new_lines))


# ── Main dialog ───────────────────────────────────────────────────────────────

class CodeRunnerDialog(QDialog):
    """
    Python Code Runner tool window.

    Left panel  – code editor (with syntax highlighting) + toolbar buttons.
    Right panel – matplotlib FigureCanvas + navigation toolbar.

    The user's code runs in a sandboxed namespace that pre-imports numpy,
    matplotlib, seaborn and exposes the plotviz datasets dict.  The code
    is expected to create a matplotlib Figure; if it calls plt.show() that
    is intercepted and the figure is rendered inside the dialog instead.
    """

    def __init__(self, datasets: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Python Code Runner')
        self.resize(1280, 760)
        self.setMinimumSize(900, 560)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.datasets = datasets
        self._build_ui()
        self._editor.setPlainText(_SAMPLE_CODE)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: editor panel ────────────────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(4)

        # Editor toolbar
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(4)

        lbl = QLabel('Python code')
        lbl.setStyleSheet('font-weight: bold; font-size: 12px;')

        self._btn_open   = QPushButton('📂 Open…')
        self._btn_open_pvizx = QPushButton('📦 Load .pvizx…')
        self._btn_save   = QPushButton('💾 Save…')
        self._btn_clear  = QPushButton('✕ Clear')
        self._btn_sample = QPushButton('↺ Sample')

        for btn in (self._btn_open, self._btn_open_pvizx, self._btn_save, self._btn_clear, self._btn_sample):
            btn.setFixedHeight(26)
            btn.setToolTip({
                self._btn_open:       'Load code from a .py file',
                self._btn_open_pvizx: 'Load and run a .pvizx Python bundle',
                self._btn_save:       'Save current code to a .py file',
                self._btn_clear:      'Clear the editor',
                self._btn_sample:     'Restore the built-in sample code',
            }[btn])

        self._btn_open_pvizx.setStyleSheet(
            'QPushButton { color: #c084fc; font-weight: bold; }'
            'QPushButton:hover { color: #a855f7; }'
        )

        toolbar_row.addWidget(lbl)
        toolbar_row.addStretch()
        toolbar_row.addWidget(self._btn_open)
        toolbar_row.addWidget(self._btn_open_pvizx)
        toolbar_row.addWidget(self._btn_save)
        toolbar_row.addWidget(self._btn_clear)
        toolbar_row.addWidget(self._btn_sample)
        ll.addLayout(toolbar_row)

        # Code editor
        self._editor = _CodeEditor()
        self._editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ll.addWidget(self._editor)

        # Line/col status + char count
        status_row = QHBoxLayout()
        self._lbl_pos   = QLabel('Ln 1, Col 1')
        self._lbl_chars = QLabel('0 chars')
        self._lbl_pos.setStyleSheet('color: #888; font-size: 11px;')
        self._lbl_chars.setStyleSheet('color: #888; font-size: 11px;')
        status_row.addWidget(self._lbl_pos)
        status_row.addStretch()
        status_row.addWidget(self._lbl_chars)
        ll.addLayout(status_row)

        # Run button (big, prominent)
        self._btn_run = QPushButton('▶  Run Code')
        self._btn_run.setFixedHeight(34)
        self._btn_run.setStyleSheet(
            'QPushButton { background: #2ecc71; color: white; font-weight: bold; '
            'font-size: 13px; border-radius: 4px; }'
            'QPushButton:hover { background: #27ae60; }'
            'QPushButton:pressed { background: #1e8449; }'
        )
        ll.addWidget(self._btn_run)

        # ── Error panel (hidden until a runtime error occurs) ────────────
        self._error_panel = QFrame()
        self._error_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self._error_panel.setStyleSheet(
            'QFrame { background: #1e1010; border: 1px solid #c0392b; border-radius: 4px; }'
        )
        ep_layout = QVBoxLayout(self._error_panel)
        ep_layout.setContentsMargins(6, 4, 6, 4)
        ep_layout.setSpacing(3)

        ep_header = QHBoxLayout()
        ep_title = QLabel('⚠  Runtime Error')
        ep_title.setStyleSheet('color: #e74c3c; font-weight: bold; font-size: 11px; background: transparent; border: none;')
        self._btn_copy_error  = QPushButton('Copy')
        self._btn_close_error = QPushButton('✕')
        for b in (self._btn_copy_error, self._btn_close_error):
            b.setFixedHeight(20)
            b.setFixedWidth(44)
            b.setStyleSheet(
                'QPushButton { background: #3a1a1a; color: #e0e0e0; border: 1px solid #7f2222; '
                'border-radius: 3px; font-size: 11px; }'
                'QPushButton:hover { background: #5a2a2a; }'
            )
        ep_header.addWidget(ep_title)
        ep_header.addStretch()
        ep_header.addWidget(self._btn_copy_error)
        ep_header.addWidget(self._btn_close_error)
        ep_layout.addLayout(ep_header)

        self._error_text = QPlainTextEdit()
        self._error_text.setReadOnly(True)
        self._error_text.setMaximumHeight(160)
        self._error_text.setMinimumHeight(80)
        self._error_text.setFont(QFont('Menlo', 9))
        self._error_text.setStyleSheet(
            'QPlainTextEdit { background: #1e1010; color: #f1948a; border: none; }'
        )
        ep_layout.addWidget(self._error_text)
        self._error_panel.setVisible(False)
        ll.addWidget(self._error_panel)

        left.setMinimumWidth(360)
        splitter.addWidget(left)

        # ── Right: canvas panel ───────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)

        self._canvas_fig = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvas(self._canvas_fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._nav = NavigationToolbar2QT(self._canvas, right)

        rl.addWidget(self._nav)
        rl.addWidget(self._canvas)

        # Bottom row: DPI + export + close
        bottom_row = QHBoxLayout()
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(150)
        self._dpi_spin.setSuffix(' DPI')
        self._dpi_spin.setFixedWidth(90)
        self._dpi_spin.setFixedHeight(28)
        self._dpi_spin.setToolTip('Export resolution')

        self._btn_export = QPushButton('Export…')
        self._btn_export.setFixedHeight(28)
        self._btn_close  = QPushButton('Close')
        self._btn_close.setFixedHeight(28)

        bottom_row.addWidget(self._dpi_spin)
        bottom_row.addWidget(self._btn_export)
        bottom_row.addStretch()
        bottom_row.addWidget(self._btn_close)
        rl.addLayout(bottom_row)

        splitter.addWidget(right)
        splitter.setSizes([440, 840])
        root.addWidget(splitter)

        # ── Wire signals ──────────────────────────────────────────────────────
        self._btn_run.clicked.connect(self._run)
        self._btn_open.clicked.connect(self._open_file)
        self._btn_open_pvizx.clicked.connect(self._open_pvizx)
        self._btn_save.clicked.connect(self._save_file)
        self._btn_clear.clicked.connect(self._editor.clear)
        self._btn_sample.clicked.connect(lambda: self._editor.setPlainText(_SAMPLE_CODE))
        self._btn_export.clicked.connect(self._export)
        self._btn_close.clicked.connect(self.close)

        self._editor.cursorPositionChanged.connect(self._update_status)
        self._editor.textChanged.connect(self._update_status)

        self._btn_copy_error.clicked.connect(self._copy_error)
        self._btn_close_error.clicked.connect(lambda: self._error_panel.setVisible(False))

        # Ctrl+Enter / Cmd+Enter → Run
        run_sc = QShortcut(QKeySequence('Ctrl+Return'), self)
        run_sc.activated.connect(self._run)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _update_status(self):
        cursor = self._editor.textCursor()
        line   = cursor.blockNumber() + 1
        col    = cursor.columnNumber() + 1
        chars  = len(self._editor.toPlainText())
        self._lbl_pos.setText(f'Ln {line}, Col {col}')
        self._lbl_chars.setText(f'{chars:,} chars')

    # ── File operations ───────────────────────────────────────────────────────

    def _open_pvizx(self):
        """Prompt the user to pick a .pvizx file, then load and run it."""
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open Python Bundle', '',
            'plotviz Python Bundle (*.pvizx);;All files (*)'
        )
        if path:
            self.load_pvizx(path)

    def load_pvizx(self, path: str):
        """Load plot.py from a .pvizx zip into the editor and run it.

        The zip is extracted to a temp directory so that the generated
        script's ``_here = os.path.dirname(os.path.abspath(__file__))``
        resolves correctly and the data/ CSVs can be read by the script.
        """
        import zipfile, tempfile, shutil, pathlib
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                if 'plot.py' not in zf.namelist():
                    QMessageBox.warning(
                        self, 'Invalid bundle',
                        f'No plot.py found inside:\n{path}'
                    )
                    return
                # Clean up any previous temp extraction
                if getattr(self, '_pvizx_tmpdir', None):
                    shutil.rmtree(self._pvizx_tmpdir, ignore_errors=True)
                tmp = tempfile.mkdtemp(prefix='pvizx_')
                self._pvizx_tmpdir = tmp
                zf.extractall(tmp)
                code = zf.read('plot.py').decode('utf-8')
        except Exception as exc:
            QMessageBox.warning(self, 'Open error', str(exc))
            return

        self._pvizx_script_path = str(pathlib.Path(tmp) / 'plot.py')
        code = self._patch_pvizx_script(code, tmp)
        self._editor.setPlainText(code)
        self._run()
        self.raise_()
        self.activateWindow()
        self._editor.setFocus()

    @staticmethod
    def _patch_pvizx_script(code: str, tmp_dir: str) -> str:
        """Fix legacy .pvizx scripts that use NaN-padded df['col'] references.

        When a bundle has columns of different lengths, pd.concat pads shorter
        columns with NaN.  Old exporters always used df['col'], causing
        griddata / scipy to crash.  This method detects that situation and
        rewrites every df['<col>'] reference to the per-column frame
        _df_<safe>['<col>'] that was already loaded without padding.
        """
        import os, re, csv as _csv

        data_dir = os.path.join(tmp_dir, 'data')
        if not os.path.isdir(data_dir):
            return code

        # Measure each CSV length (fast: count lines, subtract 1 for header)
        col_lengths: dict[str, int] = {}
        for fname in os.listdir(data_dir):
            if not fname.endswith('.csv'):
                continue
            col = fname[:-4]
            fpath = os.path.join(data_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as fh:
                n = sum(1 for _ in fh) - 1   # subtract header row
            col_lengths[col] = max(n, 0)

        if not col_lengths:
            return code

        # Only patch when lengths differ (use_combined=False case)
        if len(set(col_lengths.values())) <= 1:
            return code

        # Replace df['col'] -> _df_<safe>['col'] for every known column.
        # Use a word-boundary aware regex so we don't touch _df_cx['cx'] twice.
        def _safe(col: str) -> str:
            return col.replace(' ', '_').replace('-', '_')

        for col, length in col_lengths.items():
            safe = _safe(col)
            # Match df['col'] or df["col"] but NOT _df_xxx['col'] (preceded by _)
            pattern = re.compile(
                r'(?<![_a-zA-Z0-9])\bdf\[(["\'])'
                + re.escape(col)
                + r'\1\]',
            )
            replacement = "_df_" + safe + r"[\g<1>" + col + r"\g<1>]"
            code = pattern.sub(replacement, code)

        return code

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open Python file', '', 'Python files (*.py);;All files (*)'
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                self._editor.setPlainText(fh.read())
        except Exception as exc:
            QMessageBox.warning(self, 'Open error', str(exc))

    def _save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save Python file', 'chart.py', 'Python files (*.py);;All files (*)'
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(self._editor.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, 'Save error', str(exc))

    # ── Code execution ────────────────────────────────────────────────────────

    def _run(self):
        """Execute the editor contents and render any resulting figure."""
        code = self._editor.toPlainText().strip()
        if not code:
            return

        # Clear any previous error and close pre-existing plt figures
        self._clear_error()
        plt.close('all')
        self._canvas_fig.clear()

        # Build a sandboxed namespace.  Expose datasets so the code can use
        # `datasets['col_name']` arrays directly.
        import numpy as np
        import matplotlib as mpl
        sandbox: dict = {
            '__name__': '__code_runner__',
            '__file__':  getattr(self, '_pvizx_script_path', __file__),
            '__builtins__': __builtins__,
            'np':          np,
            'numpy':       np,
            'matplotlib':  matplotlib,
            'mpl':         mpl,
            'plt':         plt,
            'datasets':    self.datasets,
        }
        try:
            import seaborn as sns
            sandbox['sns'] = sns
            sandbox['seaborn'] = sns
        except ImportError:
            pass
        try:
            import pandas as pd
            sandbox['pd'] = pd
            sandbox['pandas'] = pd
        except ImportError:
            pass
        try:
            import scipy
            sandbox['scipy'] = scipy
        except ImportError:
            pass

        with matplotlib.rc_context({'text.usetex': False}):
            try:
                exec(compile(code, '<code_runner>', 'exec'), sandbox)   # noqa: S102
            except Exception:
                tb = traceback.format_exc()
                self._show_error(tb)
                return

        # Collect whichever figure(s) the code produced.
        figs = [plt.figure(n) for n in plt.get_fignums()]

        if not figs:
            # Code ran but created no figure — show a message.
            self._canvas_fig.clear()
            ax = self._canvas_fig.add_subplot(111)
            ax.text(0.5, 0.5,
                    'Code ran successfully but produced no figure.\n'
                    'Make sure your code calls plt.figure() / plt.subplots()\n'
                    'or creates a seaborn figure-level chart.',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=10, color='#555',
                    bbox=dict(boxstyle='round,pad=0.6', fc='#f9f9f9', ec='#ccc'))
            ax.axis('off')
            self._canvas.draw()
            return

        # Render the last figure the code produced into the embedded canvas.
        user_fig = figs[-1]
        buf = io.BytesIO()
        with matplotlib.rc_context({'text.usetex': False}):
            user_fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                             facecolor=user_fig.get_facecolor())
        buf.seek(0)
        import matplotlib.image as mpimg
        img = mpimg.imread(buf)
        self._canvas_fig.clear()
        ax = self._canvas_fig.add_axes([0, 0, 1, 1])
        ax.imshow(img, aspect='equal', interpolation='lanczos')
        ax.axis('off')
        self._canvas.draw()
        plt.close('all')

    # ── Error display ─────────────────────────────────────────────────────────

    def _show_error(self, tb: str):
        """Show the full traceback in the copyable error panel below the editor."""
        self._error_text.setPlainText(tb.strip())
        self._error_panel.setVisible(True)
        # Also render a minimal notice in the canvas so the right side isn't blank
        self._canvas_fig.clear()
        ax = self._canvas_fig.add_subplot(111)
        ax.text(0.5, 0.5,
                'Runtime error — see error panel\nbelow the editor for details.',
                ha='center', va='center', transform=ax.transAxes,
                fontsize=11, color='#c0392b',
                bbox=dict(boxstyle='round,pad=0.8', fc='#fdf2f2', ec='#e74c3c'))
        ax.axis('off')
        self._canvas.draw()

    def _copy_error(self):
        """Copy the full traceback text to the clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._error_text.toPlainText())
        # Brief visual confirmation
        self._btn_copy_error.setText('✓')
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1200, lambda: self._btn_copy_error.setText('Copy'))

    def _clear_error(self):
        """Hide the error panel (called at the start of each run)."""
        self._error_panel.setVisible(False)
        self._error_text.clear()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self):
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Export chart', 'chart.png',
            'PNG (*.png);;SVG (*.svg);;PDF (*.pdf);;JPEG (*.jpg)'
        )
        if not fp:
            return
        ext = fp.rsplit('.', 1)[-1].lower() if '.' in fp else 'png'
        fmt = 'jpeg' if ext == 'jpg' else ext
        try:
            with matplotlib.rc_context({'text.usetex': False}):
                self._canvas_fig.savefig(fp, dpi=self._dpi_spin.value(),
                                         format=fmt, bbox_inches='tight')
            QMessageBox.information(self, 'Export', f'Saved to:\n{fp}')
        except Exception as exc:
            QMessageBox.warning(self, 'Export error', str(exc))

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def reject(self):
        """Escape → hide (not destroy) so window can be re-opened with state intact."""
        self.hide()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def _cleanup_pvizx_tmp(self):
        """Remove the temp dir extracted from the last .pvizx bundle."""
        tmp = getattr(self, '_pvizx_tmpdir', None)
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            self._pvizx_tmpdir = None
            self._pvizx_script_path = None

    def refresh_datasets(self, datasets: dict):
        """Called by main window when datasets change."""
        self.datasets = datasets
