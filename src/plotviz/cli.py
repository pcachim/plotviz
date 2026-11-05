"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.

cli.py  –  plotviz
The command line: draw saved charts to image files without opening the program.

    plotviz render chart.pviz -o figure.pdf
    plotviz render a.pviz b.pviz --outdir figures --format png --dpi 600
    plotviz render chart.pviz -o figure.svg --reload --template journal.pvizt

The charts are loaded into the same window that the program uses (never shown), so the file
is the same as the one written by File > Export Image.  Nothing is written to the settings of
the program, and a dialog that would ask a question is answered by a message on stderr.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

FORMATS = {'png': 'png', 'svg': 'svg', 'pdf': 'pdf', 'jpg': 'jpeg', 'jpeg': 'jpeg',
           'tif': 'tiff', 'tiff': 'tiff', 'eps': 'eps'}
EXTENSIONS = {'png': 'png', 'svg': 'svg', 'pdf': 'pdf', 'jpeg': 'jpg', 'tiff': 'tiff', 'eps': 'eps'}
UNITS_IN_INCHES = {'in': 1.0, 'cm': 1 / 2.54, 'mm': 1 / 25.4}
DEFAULT_DPI = 300


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='plotviz render',
        description='Draw saved plotviz charts (.pviz) to image files, without opening the program.')
    p.add_argument('charts', nargs='+', metavar='CHART', help='one or more .pviz files')
    out = p.add_mutually_exclusive_group()
    out.add_argument('-o', '--output', metavar='FILE',
                     help='the image to write (one chart only); the extension gives the format')
    out.add_argument('--outdir', metavar='DIR', help='folder for the images (default: next to each chart)')
    p.add_argument('-f', '--format', choices=sorted(FORMATS), help='png, svg, pdf, jpeg, tiff or eps (default: from -o, else png)')
    p.add_argument('--dpi', type=int, default=DEFAULT_DPI, help=f'resolution of raster images (default {DEFAULT_DPI})')
    p.add_argument('--width', type=float, help="figure width (default: the chart's own)")
    p.add_argument('--height', type=float, help="figure height (default: the chart's own)")
    p.add_argument('--unit', choices=sorted(UNITS_IN_INCHES), default='cm', help='unit of --width and --height (default cm)')
    p.add_argument('--each-subplot', action='store_true', help='also write every subplot to its own file (name_1, name_2, …)')
    p.add_argument('--reload', action='store_true',
                   help='read the data files that the columns came from again before drawing')
    p.add_argument('--template', metavar='FILE', help='apply the style of a .pvizt template to every chart')
    p.add_argument('-q', '--quiet', action='store_true', help='print only errors')
    return p


def _output_path(chart: str, args, fmt: str) -> str:
    stem = Path(chart).stem
    if args.output:
        return args.output
    folder = Path(args.outdir) if args.outdir else Path(chart).resolve().parent
    return str(folder / f'{stem}.{EXTENSIONS[fmt]}')


def _format_of(args) -> str:
    if args.format:
        return FORMATS[args.format]
    if args.output:
        ext = Path(args.output).suffix.lower().lstrip('.')
        if ext in FORMATS:
            return FORMATS[ext]
        raise ValueError(f'cannot tell the format from "{args.output}": use --format or one of '
                         + ', '.join(f'.{e}' for e in sorted(FORMATS)))
    return 'png'


class _Messages:
    """Stands in for the message boxes of the program: nothing waits for a click, the text is kept."""

    def __init__(self):
        self.items: list[tuple[str, str]] = []

    def install(self):
        from PyQt6.QtWidgets import QMessageBox
        keep = self.items

        def record(kind, answer=None):
            def static(*args, **kwargs):
                texts = [a for a in args if isinstance(a, str)]
                keep.append((kind, ' — '.join(texts[-2:]) if texts else kind))
                return answer
            return staticmethod(static)
        QMessageBox.warning = record('warning')
        QMessageBox.critical = record('error')
        QMessageBox.information = record('info')
        QMessageBox.question = record('question', QMessageBox.StandardButton.No)

    def problems(self, start: int = 0) -> list[str]:
        return [text for kind, text in self.items[start:] if kind in ('warning', 'error')]


def _prepare_app():
    """The Qt application without a screen, and a program that writes nothing to the user's settings."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('MPLBACKEND', 'Agg')
    os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.fonts=false')       # no Qt notes on stderr
    import config.settings as settings
    setattr(settings, 'save', lambda data: None)
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([sys.argv[0], '-platform', 'offscreen'])
    return app


def render_chart(window, messages: _Messages, chart: str, args, size_override) -> tuple[list[str], str | None]:
    """Draw one chart.  Returns (files written, error message or None)."""
    import matplotlib.pyplot as plt
    from core.serialize import read_project_zip

    if not os.path.isfile(chart):
        return [], 'no such file'
    try:
        read_project_zip(chart)
    except Exception as e:  # noqa: BLE001 - reported to the user
        return [], f'not a plotviz chart ({e})'
    first = len(messages.items)
    window._load_project_inner(chart, silent=True)
    load_error = getattr(window, '_last_load_error', None)
    if load_error:
        return [], f'could not be loaded: {load_error}'
    if args.template:
        window._load_template_inner(args.template)
    if args.reload:
        window._reload_datasets(quiet=True)
        problems = messages.problems(first)
        if problems:
            return [], 'the data files could not be read again: ' + '; '.join(problems)
    fmt = _format_of(args)
    path = _output_path(chart, args, fmt)
    wi, hi = window._fig_size_in_inches()
    if size_override[0]:
        wi = size_override[0]
    if size_override[1]:
        hi = size_override[1]
    written = [path]
    try:
        Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
        with window._export_rc():
            fig = window._build_export_figure(wi, hi, args.dpi)
            fig.savefig(path, dpi=args.dpi, format=fmt, bbox_inches=None)
            if args.each_subplot:
                stem = os.path.splitext(path)[0]
                extra = window._subplot_file_names(stem, EXTENSIONS[fmt], window._n_export_subplots())
                window._save_subplot_files(fig, extra, wi, hi, args.dpi, fmt)
                written += extra
            plt.close(fig)
    except Exception as e:  # noqa: BLE001 - reported to the user
        return [], f'could not be drawn ({e})'
    return written, None


def render_main(argv: list[str]) -> int:
    """`plotviz render …`: returns the exit status (0 all drawn, 1 some chart failed, 2 wrong use)."""
    args = build_parser().parse_args(argv)
    if args.output and len(args.charts) > 1:
        print('plotviz render: -o takes one chart; use --outdir for several', file=sys.stderr)
        return 2
    if args.template and not os.path.isfile(args.template):
        print(f'plotviz render: no such template: {args.template}', file=sys.stderr)
        return 2
    if args.dpi < 1:
        print('plotviz render: --dpi must be positive', file=sys.stderr)
        return 2
    try:
        _format_of(args)
    except ValueError as e:
        print(f'plotviz render: {e}', file=sys.stderr)
        return 2
    scale = UNITS_IN_INCHES[args.unit]
    size = (args.width * scale if args.width else None, args.height * scale if args.height else None)

    app = _prepare_app()                  # kept: the application must outlive the window
    messages = _Messages()
    messages.install()
    from ui.main_window import PlotVizApp
    PlotVizApp._load_on_startup = lambda self: None     # no last chart, no offer to restore one: only what was asked for
    window = PlotVizApp()
    failed = 0
    for chart in args.charts:
        written, error = render_chart(window, messages, chart, args, size)
        if error:
            failed += 1
            print(f'{chart}: {error}', file=sys.stderr)
        elif not args.quiet:
            print(f'{chart} -> {", ".join(written)}')
    return 1 if failed else 0
