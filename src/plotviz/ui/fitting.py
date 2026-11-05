"""
Copyright (c) 2026 Paulo Cachim
ui/fitting.py  –  plotviz

FitPresetMixin: chart presets and the curve-fitting workflow (fit dialog,
running fits, fit-result display/export). Split out of main_window; mixed into
PlotVizApp so its methods share the series table, fit state and widgets via
`self`.
"""
import csv
import io
from dataclasses import dataclass
from typing import Any

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QMessageBox, QSpinBox, QTableWidgetItem,
)
from data.scientific import (
    CurveFitter, CUSTOM_CHOICE, LOWESS_CHOICE, POLYNOMIAL_CHOICE, POLYNOMIAL_PREFIX, parse_start_values,
)
from ui.tab_builders import PLOT_MODE_GROUPS, PER_SERIES_TYPES
from data.fit_text import FitTextOptions, fit_annotation_text
from data.transforms import downsample_minmax
from ui.mixin_base import MixinBase


@dataclass
class GeneratePlan:
    """What Generate would create, worked out without changing anything (the preview draws it)."""
    label: str
    expr: str
    x: Any                    # the generated x (range mode), else None
    source: str | None        # the source column (column mode)
    y: Any
    x_new: str | None         # the names the results would be stored under
    y_new: str
    log_x: bool = False       # logspace / geomspace

    @property
    def made(self):
        return ([self.x_new] if self.x_new else []) + [self.y_new]


@dataclass
class GridPlan:
    """What a z = f(x, y) or (u, v) = f(x, y) generator would create, worked out without
    changing anything (the preview draws it)."""
    label: str
    x: Any                          # the points the expressions are evaluated at
    y: Any
    outputs: list[tuple[str, str, Any]]     # (role, name it would be stored under, values)
    x_name: str                     # the x / y series the results belong to
    y_name: str
    x_new: str | None               # set when x / y would be created (generated, or meshgrid)
    y_new: str | None
    shape: tuple[int, int] | None   # (ny, nx) of a meshgrid
    log_x: bool
    log_y: bool
    vector: bool                    # (u, v) rather than z

    @property
    def made(self):
        return [n for n in (self.x_new, self.y_new) if n] + [name for _, name, _ in self.outputs]


class FitPresetMixin(MixinBase):

    def _rename_table_col(self, col_idx):
        from PyQt6.QtWidgets import QInputDialog
        old = self.data_table.horizontalHeaderItem(col_idx)
        old_name = old.text() if old else f'col_{col_idx+1}'
        name, ok = QInputDialog.getText(self, 'Rename column', 'Column name:', text=old_name)
        if ok and name.strip():
            self.data_table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(name.strip()))

    # ── y = f(x): compute (no side effects, shared with the preview) and apply ───────

    def _gen_seed_value(self):
        """The seed of the random spacings: kept until Apply, so the preview is what Apply makes."""
        if getattr(self, '_gen_seed', None) is None:
            self._gen_seed = int(np.random.default_rng().integers(2**32))
        return self._gen_seed

    def _gen_eval(self, expr, var, arr):
        return self._gen_eval_vars(expr, {var: arr})

    @staticmethod
    def _gen_eval_vars(expr, variables):
        ns = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        ns.update({**variables, 'pi': np.pi, 'e': np.e,
                   'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                   'exp': np.exp, 'log': np.log, 'log10': np.log10,
                   'sqrt': np.sqrt, 'abs': np.abs})
        return eval(expr, {'__builtins__': {}}, ns)

    def _gen_unique(self, base, taken=()):
        name, cnt = base, 1
        while name in self.datasets or name in taken:
            name = f'{base}_{cnt}'
            cnt += 1
        return name

    def _gen_x_array(self, spacing, x_min, x_max, n, salt=0):
        if spacing != 'logspace' and x_min >= x_max:
            raise ValueError('x_min must be less than x_max')
        if spacing == 'logspace' and x_min >= x_max:
            raise ValueError('exponent start must be less than stop')
        if spacing == 'logspace':
            return np.logspace(x_min, x_max, n)
        if spacing == 'geomspace':
            if x_min <= 0 or x_max <= 0:
                raise ValueError('geomspace requires start and stop > 0')
            return np.geomspace(x_min, x_max, n)
        if spacing == 'random':
            rng = np.random.default_rng(self._gen_seed_value() + salt)
            return np.sort(rng.normal((x_min + x_max) / 2, (x_max - x_min) / 6, n))
        if spacing == 'uniform':
            rng = np.random.default_rng(self._gen_seed_value() + salt)
            return np.sort(rng.uniform(x_min, x_max, n))
        return np.linspace(x_min, x_max, n)

    def _compute_generate(self):
        """What the Generate button would create, without changing anything: a GeneratePlan.
        Raises ValueError with a message for the panel when it cannot be done."""
        expr = self.gen_expr.text().strip()
        if not expr:
            raise ValueError('Type an expression')
        if self._adv_mode_range.isChecked():
            spacing = self.gen_x_spacing.currentText() if hasattr(self, 'gen_x_spacing') else 'linspace'
            n = self.gen_x_n.value()
            x = self._gen_x_array(spacing, self.gen_x_min.value(), self.gen_x_max.value(), n)
            y = np.asarray(self._gen_eval(expr, 'x', x), dtype=float)
            if y.shape == ():
                y = np.full(n, float(y))
            x_new = self._gen_unique(self.gen_x_name.text().strip() or 'x')
            y_new = self._gen_unique(self.gen_y_name.text().strip() or 'y', {x_new})
            return GeneratePlan('y = f(x)', expr, x, None, y, x_new, y_new, spacing in ('logspace', 'geomspace'))
        source = self.fn_source_combo.currentText()
        if source not in self.datasets:
            raise ValueError('No source column selected')
        src = self.datasets[source]
        result = np.asarray(self._gen_eval(expr, self.fn_var_name.text().strip() or 'x', src))
        if result.shape == ():
            result = np.full(len(src), float(result))
        y_new = self._gen_unique(self.gen_y_name.text().strip() or 'result')
        return GeneratePlan('f(column)', expr, None, source, result, None, y_new, False)

    def _gen_draw_plan(self, ax, plan, fg):
        y = np.asarray(plan.y, dtype=float)
        colour = self._palette_color(1)
        n = len(y)
        if plan.x is not None:
            x = np.asarray(plan.x, dtype=float)
        else:
            x = np.arange(n, dtype=float)             # a column: drawn against the point number
            src = np.asarray(self.datasets[plan.source], dtype=float) if plan.source else None
            if src is not None and len(src) == n:
                ax.plot(*downsample_minmax(x, src), color='#9a9a9a', lw=0.9, label=plan.source)
            ax.set_xlabel('point', fontsize=7, color=fg)
        ax.plot(*downsample_minmax(x, y), color=colour, lw=1.3, marker='.' if n <= 200 else None,
                ms=3.5, label=plan.y_new)
        finite = y[np.isfinite(y)]
        if self.gen_preview.log_check.isChecked() and len(finite) and finite.min() > 0:
            ax.set_yscale('log')
        if plan.log_x and len(x) and x.min() > 0:
            ax.set_xscale('log')
        leg = ax.legend(fontsize=7, loc='best', frameon=False)
        for text in leg.get_texts():
            text.set_color(fg)
        names = ' and '.join(f'"{n}"' for n in plan.made)
        return f'{plan.label}: {n:,} points → would create {names}.'

    def _gen_size(self):
        if self._adv_mode_range.isChecked():
            return self.gen_x_n.value()
        return len(self.datasets.get(self.fn_source_combo.currentText(), ()))

    def _schedule_generate_previews(self, *_):
        """The page shown may have changed, or the datasets: ask each preview to refresh."""
        for name in ('gen_preview', 'fxy_preview', 'fuv_preview'):
            if hasattr(self, name):
                getattr(self, name).schedule()

    def _gen_connect_preview_triggers(self):
        schedule = self.gen_preview.schedule
        for edit in (self.gen_expr, self.gen_x_name, self.gen_y_name, self.fn_var_name):
            edit.textChanged.connect(schedule)
        for spin in (self.gen_x_min, self.gen_x_max, self.gen_x_n):
            spin.valueChanged.connect(schedule)
        self.gen_x_spacing.currentTextChanged.connect(schedule)
        self.fn_source_combo.currentTextChanged.connect(schedule)
        self._adv_mode_range.toggled.connect(schedule)

    def _generate_fx(self):
        try:
            plan = self._compute_generate()
            if plan.x_new:
                self.datasets[plan.x_new] = plan.x
            self.datasets[plan.y_new] = plan.y
            self._gen_seed = None                    # the next random spacing is a new draw
            self._schedule_undo_snapshot('Generate y = f(x)' if plan.x_new else 'Apply function to column')
            self.update_lists()
            names = ', '.join(f'"{n}"' for n in plan.made)
            self.gen_status.setText(f'✓  Created {names}  ({len(plan.y)} points)')
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.gen_status.setText(f'❌  {e}')

    # ── z = f(x, y) and (u, v) = f(x, y): one calculation for the buttons and the previews ──

    def _grid_axis(self, prefix, axis, salt):
        """One input axis of a grid generator: (values, variable name, column name to use,
        whether it is generated, whether it is spaced logarithmically)."""
        def widget(name):
            return getattr(self, f'{prefix}_{axis}_{name}')
        if widget('mode_range').isChecked():
            spacing = widget('spacing').currentText()
            try:
                arr = self._gen_x_array(spacing, widget('min').value(), widget('max').value(),
                                        widget('n').value(), salt)
            except ValueError as e:
                raise ValueError(f'{axis}: {e}') from e
            var = widget('col_name').text().strip() or axis
            return arr, var, var, True, spacing in ('logspace', 'geomspace')
        col = widget('combo').currentText()
        if col not in self.datasets:
            raise ValueError(f'{axis} column not found')
        return (np.asarray(self.datasets[col], dtype=float), widget('var').text().strip() or axis,
                col, False, False)

    def _compute_grid(self, prefix, label, outputs):
        """What a grid generator would create, without changing anything: a GridPlan.
        *outputs* lists (role, expression widget, name widget, default name)."""
        wanted = []
        for role, expr_widget, name_widget, default in outputs:
            expr = expr_widget.text().strip()
            if not expr:
                raise ValueError(f'{role} expression is empty' if len(outputs) > 1 else 'Expression is empty')
            wanted.append((role, expr, name_widget.text().strip() or default))
        x_arr, x_var, x_col, x_gen, log_x = self._grid_axis(prefix, 'x', 0)
        y_arr, y_var, y_col, y_gen, log_y = self._grid_axis(prefix, 'y', 1)
        meshgrid = getattr(self, f'{prefix}_meshgrid').isChecked()
        if meshgrid:
            gx, gy = np.meshgrid(x_arr, y_arr)
            x_eval, y_eval, shape = gx.ravel(), gy.ravel(), (len(y_arr), len(x_arr))
        else:
            n = min(len(x_arr), len(y_arr))
            x_eval, y_eval, shape = x_arr[:n], y_arr[:n], None
        n = len(x_eval)
        taken: set[str] = set()
        x_new = self._gen_unique(x_col) if (x_gen or meshgrid) else None
        taken.update(filter(None, [x_new]))
        y_new = self._gen_unique(y_col, taken) if (y_gen or meshgrid) else None
        taken.update(filter(None, [y_new]))
        results = []
        for role, expr, name in wanted:
            values = np.asarray(self._gen_eval_vars(expr, {x_var: x_eval, y_var: y_eval}), dtype=float)
            if values.shape == ():
                values = np.full(n, float(values))
            stored = self._gen_unique(name, taken)
            taken.add(stored)
            results.append((role, stored, values))
        return GridPlan(label, x_eval, y_eval, results, x_new or x_col, y_new or y_col, x_new, y_new,
                        shape, log_x, log_y, vector=len(results) == 2)

    def _store_grid(self, plan, undo_label):
        if plan.x_new:
            self.datasets[plan.x_new] = plan.x
        if plan.y_new:
            self.datasets[plan.y_new] = plan.y
        for _, name, values in plan.outputs:
            self.datasets[name] = values
        self._gen_seed = None                        # the next random spacing is a new draw
        self._schedule_undo_snapshot(undo_label)
        self.update_lists()
        mesh = 'meshgrid ' if plan.shape else ''
        parts = [f'x={plan.x_name}', f'y={plan.y_name}'] + [f'{role}={name}' for role, name, _ in plan.outputs]
        return f'\u2713  {mesh}Created {", ".join(parts)}  ({len(plan.x)} pts)'

    def _compute_fxy(self):
        return self._compute_grid('fxy', 'z = f(x, y)', [('z', self.fxy_expr, self.fxy_z_name, 'z')])

    def _compute_fuv(self):
        return self._compute_grid('fuv', '(u, v) = f(x, y)', [
            ('u', self.fuv_u_expr, self.fuv_u_name, 'u'), ('v', self.fuv_v_expr, self.fuv_v_name, 'v')])

    def _generate_fxy(self):
        """Generate z = f(x, y) — supports per-axis range/column input and meshgrid."""
        try:
            self.fxy_status.setText(self._store_grid(self._compute_fxy(), 'Generate z = f(x, y)'))
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.fxy_status.setText(f'\u274c  {e}')

    def _generate_fuv(self):
        """Generate (u, v) = f(x, y) — vector-field components over a 2-D grid."""
        try:
            self.fuv_status.setText(self._store_grid(self._compute_fuv(), 'Generate (u, v) = f(x, y)'))
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.fuv_status.setText(f'\u274c  {e}')

    def _grid_size(self, prefix):
        """Points a grid generator would evaluate (Live pauses for very many)."""
        sizes = []
        for axis in ('x', 'y'):
            if getattr(self, f'{prefix}_{axis}_mode_range').isChecked():
                sizes.append(getattr(self, f'{prefix}_{axis}_n').value())
            else:
                sizes.append(len(self.datasets.get(getattr(self, f'{prefix}_{axis}_combo').currentText(), ())))
        return sizes[0] * sizes[1] if getattr(self, f'{prefix}_meshgrid').isChecked() else min(sizes)

    def _grid_connect_preview_triggers(self, prefix, panel):
        from PyQt6.QtWidgets import QAbstractButton, QDoubleSpinBox, QLineEdit
        names = ['meshgrid'] + [f'{a}_{n}' for a in 'xy' for n in
                                ('mode_range', 'min', 'max', 'n', 'spacing', 'col_name', 'combo', 'var')]
        names += {'fxy': ['expr', 'z_name'], 'fuv': ['u_expr', 'v_expr', 'u_name', 'v_name']}[prefix]
        for name in names:
            w = getattr(self, f'{prefix}_{name}')
            if isinstance(w, QLineEdit):
                w.textChanged.connect(panel.schedule)
            elif isinstance(w, QComboBox):
                w.currentTextChanged.connect(panel.schedule)
            elif isinstance(w, QAbstractButton):
                w.toggled.connect(panel.schedule)
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                w.valueChanged.connect(panel.schedule)

    def _grid_draw_plan(self, ax, plan, fg):
        x, y = plan.x, plan.y
        n = len(x)
        if plan.vector:
            u, v = plan.outputs[0][2], plan.outputs[1][2]
            if plan.shape:                       # a grid: an arrow every few cells (at most 20 per side)
                ny, nx = plan.shape
                sy, sx = max(1, ny // 20), max(1, nx // 20)
                pick = np.arange(n).reshape(plan.shape)[::sy, ::sx].ravel()
            else:
                pick = np.arange(0, n, max(1, n // 400))
            magnitude = np.hypot(u, v)
            ax.quiver(x[pick], y[pick], u[pick], v[pick], magnitude[pick], cmap='viridis', angles='xy')
            shown = magnitude[np.isfinite(magnitude)]
            summary = f'|(u, v)| from {shown.min():.4g} to {shown.max():.4g}' if len(shown) else 'no finite values'
        else:
            z = plan.outputs[0][2]
            if plan.shape:                       # a grid: filled contours with their lines (at most ~150 per side)
                ny, nx = plan.shape
                sy, sx = max(1, ny // 150), max(1, nx // 150)
                xs = x.reshape(plan.shape)[0, ::sx]
                ys = y.reshape(plan.shape)[::sy, 0]
                zs = z.reshape(plan.shape)[::sy, ::sx]
                finite = zs[np.isfinite(zs)]
                if len(finite) and finite.max() > finite.min() and min(zs.shape) >= 2:
                    ax.contourf(xs, ys, zs, levels=12, cmap='viridis')
                    ax.contour(xs, ys, zs, levels=12, colors=fg, linewidths=0.3, alpha=0.5)
                else:                            # flat or too small to contour
                    ax.pcolormesh(xs, ys, zs, shading='nearest', cmap='viridis')
            else:
                step = max(1, n // 3000)
                ax.scatter(x[::step], y[::step], c=z[::step], s=6, cmap='viridis')
            shown = z[np.isfinite(z)]
            summary = f'z from {shown.min():.4g} to {shown.max():.4g}' if len(shown) else 'no finite values'
        if plan.log_x and len(x) and x.min() > 0:
            ax.set_xscale('log')
        if plan.log_y and len(y) and y.min() > 0:
            ax.set_yscale('log')
        ax.set_xlabel(plan.x_name, fontsize=7, color=fg, labelpad=1)
        ax.set_ylabel(plan.y_name, fontsize=7, color=fg, labelpad=1)
        names = ', '.join(f'"{name}"' for name in plan.made)
        grid = f' ({plan.shape[1]} × {plan.shape[0]} grid)' if plan.shape else ''
        if not plan.shape:
            summary += '. Without Meshgrid, x and y are paired point by point'
        return f'{plan.label}: {n:,} points{grid} → would create {names}; {summary}.'

    # ── A label with the fit on the chart (an ordinary text annotation) ───────────────

    def _fit_subplot_index(self, key):
        """The subplot (0-based) that the curve of fit *key* is drawn in."""
        for row in range(self.series_table.rowCount()):
            item = self.series_table.item(row, 2)
            if item and item.text() == key:
                spin = self.series_table.cellWidget(row, 4)
                if spin:
                    return max(0, spin.value() - 1)
        return 0

    @staticmethod
    def _text_block_pts(text, style):
        """Measure a label: (distance from its anchor down to the bottom of the text, its height,
        distance from the anchor to its left edge), all in points. The size of a text in points
        does not depend on the size of the window, so this holds for the exported file too."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        fig = Figure(dpi=100)
        FigureCanvasAgg(fig)
        artist = fig.text(0.5, 0.5, text, fontsize=style.get('fontsize', 10),
                          fontfamily=style.get('fontfamily', 'sans-serif'))
        box = artist.get_window_extent(fig.canvas.get_renderer())
        anchor_x, anchor_y = fig.transFigure.transform((0.5, 0.5))
        k = 72 / fig.dpi
        return (anchor_y - box.y0) * k, box.height * k, (box.x0 - anchor_x) * k

    def _axes_size_pts(self, ax_idx):
        """Width and height in points of subplot *ax_idx* in the exported figure."""
        wi, hi = self._fig_size_in_inches()
        figure = self._build_export_figure(wi, hi, 100)
        position = figure._pviz_axes[min(ax_idx, len(figure._pviz_axes) - 1)].get_position()
        return position.width * wi * 72, position.height * hi * 72

    def _add_fit_label(self, key, options=None):
        """Put the text of fit *key* on the chart as a text annotation, at the top left of its
        subplot (under the labels of other fits already there). The text is fixed: it does not
        follow the fit if the fit is made again. Returns the annotation, or None.

        The place is worked out in points on the exported figure (a label is as big in points
        whatever the size of the window), then stored in data coordinates like any annotation."""
        fit = self._fits.get(key)
        canvas = self.canvas
        if fit is None or not getattr(canvas, 'axes_list', None):
            return None
        text = fit_annotation_text(fit, options or getattr(self, '_fit_label_options', FitTextOptions()))
        ax_idx = min(self._fit_subplot_index(key), len(canvas.axes_list) - 1)
        ax = canvas.axes_list[ax_idx]
        style = dict(canvas.ann_style)
        font = style.get('fontsize', 10)
        pad, edge, gap = 0.3 * font, 0.8 * font, 0.8 * font       # the box padding; from the edge; between labels
        width, height = self._axes_size_pts(ax_idx)
        canvas.draw()                                             # final limits, for the transforms

        def from_top(x, y):
            """How far below the top of the axes (points) is the anchor at data (x, y)."""
            return (1 - ax.transAxes.inverted().transform(ax.transData.transform((x, y)))[1]) * height

        top = edge + pad                                          # of the text
        for other in canvas.annotations:
            if other.get('source_fit') and other.get('axes_index') == ax_idx:
                other_down, _, _ = self._text_block_pts(other['label'], other.get('style', style))
                bottom = from_top(other['x'], other['y']) + other_down + 0.3 * other.get('style', style).get('fontsize', 10)
                top = max(top, bottom + gap + pad)
        down, block, left = self._text_block_pts(text, style)
        fx, fy = (edge + pad - left) / width, 1 - (top + block - down) / height
        x, y = (float(v) for v in ax.transData.inverted().transform(ax.transAxes.transform((fx, fy))))
        canvas._place_text_annotation(ax, ax_idx, x, y, label=text)
        ann = canvas.annotations[-1]
        ann['source_fit'] = key
        self._schedule_undo_snapshot('Add fit label')
        return ann

    def _add_fit_label_dialog(self):
        """Ask what the label shows, then add it for the selected fit, or for every fit when
        **All fits** (the box of the Results row, shared with Export) is ticked."""
        from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout
        if not self._fits:
            QMessageBox.information(self, 'No fits', 'Fit a curve first.')
            return
        every = self.fit_export_all_check.isChecked()
        key = self._selected_curve_key()
        if not every and key not in self._fits:
            QMessageBox.information(self, 'No Fit Selected', 'Select a fit curve first, or tick "All fits".')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Fit label')
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Add to the chart as a text annotation:\n'
                                + (f'one label for each of the {len(self._fits)} fits' if every else key)))
        opt = getattr(self, '_fit_label_options', FitTextOptions())
        boxes = {}
        for name, text in (('name', 'Title (model and series)'), ('equation', 'Equation'),
                           ('latex', 'Write the equation as math text ($…$)'),
                           ('parameters', 'Parameters, with their errors'), ('r2', 'R²'),
                           ('rmse', 'RMSE'), ('aic', 'AIC'), ('n', 'Number of points')):
            boxes[name] = QCheckBox(text)
            boxes[name].setChecked(getattr(opt, name))
            layout.addWidget(boxes[name])
        note = QLabel('The text is fixed: make the label again if you fit again.\n'
                      'Drag it, or double-click it, like any annotation.')
        note.setStyleSheet('color:#888;font-size:11px;')
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._fit_label_options = FitTextOptions(**{name: box.isChecked() for name, box in boxes.items()})
        for each in (list(self._fits) if every else [key]):
            self._add_fit_label(each, self._fit_label_options)

    def _apply_col_function(self):
        self._generate_fx()

    # ── Inspect loaded series values ───────────────────────────────────────────

    def _inspect_series(self):
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                     QTableWidget, QTableWidgetItem,
                                     QPushButton, QLabel, QSizePolicy,
                                     QLineEdit, QFrame)
        if not self.datasets:
            return

        selected_items = [item.text() for item in self.dataset_list.selectedItems()]
        cols = selected_items if selected_items else sorted(self.datasets)
        cols = [c for c in cols if c in self.datasets]
        if not cols:
            return

        n_rows = max(len(self.datasets[c]) for c in cols)

        dlg = QDialog(self)
        dlg.setWindowTitle('Inspect / Edit Series Values')
        dlg.resize(min(140 + 110 * len(cols), 1100), 600)
        vlay = QVBoxLayout(dlg)

        info = QLabel(
            f'{len(cols)} column(s)   ·   up to {n_rows} row(s)   —   '
            '<b>double-click a cell to edit</b>')
        info.setStyleSheet('color:#555; font-size:11px;')
        vlay.addWidget(info)

        # ── Column rename row ──────────────────────────────────────────────────
        rename_frame = QFrame()
        rename_frame.setFrameShape(QFrame.Shape.StyledPanel)
        rename_layout = QHBoxLayout(rename_frame)
        rename_layout.setContentsMargins(6, 4, 6, 4)
        rename_layout.setSpacing(6)
        rename_layout.addWidget(QLabel('<b>Column name:</b>'))
        name_edits = []   # one QLineEdit per column, same order as cols
        for col in cols:
            ed = QLineEdit(col)
            ed.setPlaceholderText('column name')
            ed.setMinimumWidth(90)
            name_edits.append(ed)
            rename_layout.addWidget(ed, 1)
        vlay.addWidget(rename_frame)

        tbl = QTableWidget(n_rows, len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        for ci, col in enumerate(cols):
            arr = self.datasets[col]
            is_cat = self._is_categorical(arr)
            for ri in range(len(arr)):
                v = arr[ri]
                text = str(v) if is_cat else f'{v:.6g}'
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(ri, ci, item)
            tbl.resizeColumnToContents(ci)

        # Keep table header in sync as user types a new name
        def _sync_header(ci, text):
            tbl.setHorizontalHeaderItem(ci, QTableWidgetItem(text or cols[ci]))
        for ci, ed in enumerate(name_edits):
            ed.textChanged.connect(lambda text, ci=ci: _sync_header(ci, text))

        vlay.addWidget(tbl)

        note2 = QLabel('Changes are written back when you click Apply or OK.')
        note2.setStyleSheet('color:#888; font-size:10px;')
        vlay.addWidget(note2)

        def _apply_edits():
            # ── 1. Apply column renames first ─────────────────────────────────
            renamed = {}   # old_name -> new_name for changed names
            for ci, (old_col, ed) in enumerate(zip(cols, name_edits)):
                new_name = ed.text().strip()
                if not new_name or new_name == old_col:
                    continue
                if new_name in self.datasets and new_name != old_col:
                    info.setText(f'⚠  Column "{new_name}" already exists — rename skipped.')
                    continue
                # Rename: preserve insertion order by rebuilding the dict
                self.datasets = {
                    (new_name if k == old_col else k): v
                    for k, v in self.datasets.items()
                }
                renamed[old_col] = new_name
                cols[ci] = new_name   # update working list for the data-write step

            # ── 2. Write edited cell values back ──────────────────────────────
            for ci, col in enumerate(cols):
                arr = self.datasets[col]
                is_cat = self._is_categorical(arr)
                new_vals = []
                for ri in range(n_rows):
                    cell = tbl.item(ri, ci)
                    if cell is None or cell.text().strip() == '':
                        new_vals.append('' if is_cat else np.nan)
                        continue
                    txt = cell.text().strip()
                    if is_cat:
                        new_vals.append(txt)
                    else:
                        try:
                            new_vals.append(float(txt))
                        except ValueError:
                            new_vals.append(np.nan)
                if is_cat:
                    self.datasets[col] = np.array(new_vals, dtype=object)
                else:
                    self.datasets[col] = np.array(new_vals, dtype=float)

            # ── 3. Refresh all column pickers if any rename happened ──────────
            if renamed:
                # update_lists() snapshots currentText() at the very top before
                # clearing, so we must make each combo report the *new* name
                # before update_lists() runs.  setCurrentText() only works when
                # the text already exists as an item, so we rename the matching
                # item in-place with setItemText() instead.
                def _rename_item(cb, old_new):
                    for i in range(cb.count()):
                        txt = cb.itemText(i)
                        if txt in old_new:
                            cb.setItemText(i, old_new[txt])

                # Series table X / Y combos (cols 0 and 1)
                for row in range(self.series_table.rowCount()):
                    for col_idx in (0, 1):
                        cb = self.series_table.cellWidget(row, col_idx)
                        if cb is not None:
                            _rename_item(cb, renamed)

                # Single-select combos that update_lists() snapshots at the top
                for attr in ('combo_z', 'combo_err', 'combo_fill_y2',
                             'quiver_u_combo', 'quiver_v_combo',
                             'barbs_u_combo',  'barbs_v_combo',
                             'stream_u_combo', 'stream_v_combo',
                             'bubble_size_combo', 'fn_source_combo',
                             'err_xerr_combo'):
                    cb = getattr(self, attr, None)
                    if cb is not None:
                        _rename_item(cb, renamed)

                self._schedule_undo_snapshot('Edit values')
                self.update_lists()
                parts = ', '.join(f'"{o}" → "{n}"' for o, n in renamed.items())
                info.setText(f'✓  Renamed: {parts}')
            else:
                info.setText(f'✓  Applied edits to: {", ".join(cols)}')
            self.update_preview()

        btn_row = QHBoxLayout()
        btn_apply = QPushButton('✔ Apply')
        btn_apply.clicked.connect(_apply_edits)
        btn_ok    = QPushButton('OK')
        btn_ok.clicked.connect(lambda: (_apply_edits(), dlg.accept()))
        btn_cancel = QPushButton('Cancel')
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_apply)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        vlay.addLayout(btn_row)

        dlg.exec()
    def _new_data_table(self):
        rows = self.table_rows_spin.value()
        cols = self.table_cols_spin.value()
        self.data_table.blockSignals(True)
        self.data_table.setRowCount(rows)
        self.data_table.setColumnCount(cols)
        self.data_table.setHorizontalHeaderLabels([f'col_{i+1}' for i in range(cols)])
        self.data_table.clearContents()
        self.data_table.blockSignals(False)
        self.table_status.setText('')

    def _table_add_row(self):
        self.data_table.insertRow(self.data_table.rowCount())

    def _table_del_row(self):
        rows = sorted({idx.row() for idx in self.data_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.data_table.removeRow(r)
        if not rows:
            r = self.data_table.rowCount() - 1
            if r >= 0: self.data_table.removeRow(r)

    def _table_add_col(self):
        c = self.data_table.columnCount()
        self.data_table.insertColumn(c)
        self.data_table.setHorizontalHeaderItem(c, QTableWidgetItem(f'col_{c+1}'))

    def _table_del_col(self):
        cols = sorted({idx.column() for idx in self.data_table.selectedIndexes()}, reverse=True)
        for c in cols:
            self.data_table.removeColumn(c)
        if not cols:
            c = self.data_table.columnCount() - 1
            if c >= 0: self.data_table.removeColumn(c)

    def _table_clear(self):
        for r in range(self.data_table.rowCount()):
            for c in range(self.data_table.columnCount()):
                self.data_table.setItem(r, c, QTableWidgetItem(''))

    def _table_paste_csv(self):
        """Paste clipboard CSV/TSV text into the table, expanding it as needed."""
        text = QApplication.clipboard().text().strip()
        if not text:
            self.table_status.setText('❌  Clipboard is empty')
            return
        # Detect delimiter
        delim = '\t' if '\t' in text.split('\n')[0] else ','
        reader = list(csv.reader(io.StringIO(text), delimiter=delim))
        if not reader:
            self.table_status.setText('❌  No data found')
            return
        # Check if first row looks like a header
        first = reader[0]
        def _is_num(v):
            try:
                float(v)
                return True
            except ValueError: return False
        has_header = any(v.strip() and not _is_num(v) for v in first)
        data_rows = reader[1:] if has_header else reader
        headers   = [v.strip() for v in first] if has_header else [f'col_{i+1}' for i in range(len(first))]
        n_cols = max(len(headers), max((len(r) for r in data_rows), default=0))
        n_rows = len(data_rows)
        # Resize table
        self.data_table.setRowCount(n_rows)
        self.data_table.setColumnCount(n_cols)
        while len(headers) < n_cols: headers.append(f'col_{len(headers)+1}')
        self.data_table.setHorizontalHeaderLabels(headers)
        for r, row in enumerate(data_rows):
            for c, val in enumerate(row):
                self.data_table.setItem(r, c, QTableWidgetItem(val.strip()))
        self.table_status.setText(f'✓  Pasted {n_rows} rows × {n_cols} cols')

    def _table_copy_csv(self):
        """Copy table contents to clipboard as CSV."""
        out = io.StringIO()
        w = csv.writer(out)
        headers = [self.data_table.horizontalHeaderItem(c).text()
                   if self.data_table.horizontalHeaderItem(c) else f'col_{c+1}'
                   for c in range(self.data_table.columnCount())]
        w.writerow(headers)
        for r in range(self.data_table.rowCount()):
            row = []
            for c in range(self.data_table.columnCount()):
                item = self.data_table.item(r, c)
                row.append(item.text() if item else '')
            w.writerow(row)
        QApplication.clipboard().setText(out.getvalue())
        self.table_status.setText(f'✓  Copied {self.data_table.rowCount()} rows to clipboard')

    def _load_table_data(self):
        """Parse the manual table and add each column as a dataset."""
        try:
            n_rows = self.data_table.rowCount()
            n_cols = self.data_table.columnCount()
            loaded = []
            for c in range(n_cols):
                header = self.data_table.horizontalHeaderItem(c)
                col_name = header.text() if header else f'col_{c+1}'
                raw = []
                for r in range(n_rows):
                    item = self.data_table.item(r, c)
                    raw.append(item.text().strip() if item else '')
                # Try all-numeric
                try:
                    arr = np.array([float(v) if v != '' else np.nan for v in raw], dtype=float)
                except ValueError:
                    arr = np.array(raw, dtype=object)
                base, cnt = col_name, 1
                while base in self.datasets:
                    base = f'{col_name}_{cnt}'
                    cnt += 1
                self.datasets[base] = arr
                loaded.append(base)
            self._schedule_undo_snapshot('Data table')
            self.update_lists()
            if self.series_table.rowCount() == 0:
                self._add_series_row()
            else:
                self.update_preview()
            self.table_status.setText(f'✓  Loaded: {", ".join(loaded)}')
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.table_status.setText(f'❌  {e}')

    # ── Fits list: every fit, side by side ────────────────────────────────────

    def _next_fit_color(self, source_label, name):
        """A colour for a new fit curve that neither the series nor its other fits use, so
        several fits of one series can be told apart (they used to share the series colour)."""
        used = {str(self.curve_styles.get(source_label, {}).get('color', '')).lower()}
        used |= {str(self.curve_styles.get(k, {}).get('color', '')).lower()
                 for k, f in self._fits.items() if f.get('lbl') == source_label and k != name}
        for i in range(16):
            colour = self._palette_color(i)
            if colour.lower() not in used:
                return colour
        return self._palette_color(0)

    def _fit_label(self, name):
        """The label of the series row that plots the fit *name* (it may have been renamed)."""
        for row in range(self.series_table.rowCount()):
            ycb = self.series_table.cellWidget(row, 1)
            item = self.series_table.item(row, 2)
            if ycb is not None and ycb.currentText() == name and item:
                return item.text()
        return name

    def _fit_series_labels(self):
        """Labels of the series rows that plot a fit curve."""
        return {self.series_table.item(row, 2).text()
                for row in range(self.series_table.rowCount())
                if self.series_table.item(row, 2) is not None
                and self.series_table.cellWidget(row, 1) is not None
                and self.series_table.cellWidget(row, 1).currentText() in self._fits}

    def _fit_row_is_hidden(self, row):
        """True for a series row that plots a fit the user has switched off in the Fits list."""
        ycb = self.series_table.cellWidget(row, 1)
        fit = self._fits.get(ycb.currentText()) if ycb is not None else None
        return bool(fit) and not fit.get('visible', True)

    def _without_hidden_fits(self, series_meta):
        """series_meta without the series of hidden fits (for the exported script)."""
        hidden = {name for name, f in self._fits.items() if not f.get('visible', True)}
        if not hidden:
            return series_meta
        out = dict(series_meta)
        out['series'] = [s for s in series_meta.get('series', []) if s.get('y_col') not in hidden]
        return out

    def _refresh_fit_table(self):
        """Rebuild the Fits list: one row per fit, with the numbers to compare them by."""
        if not hasattr(self, 'fit_table'):
            return
        t = self.fit_table
        selected = self._selected_curve_key()
        best = {}                                      # lowest AIC among the fits of each series
        for f in self._fits.values():
            aic = (f.get('stats') or {}).get('aic')
            if aic is not None and aic == aic:
                src = f.get('lbl')
                best[src] = min(best.get(src, aic), aic)
        t.blockSignals(True)
        t.setRowCount(len(self._fits))
        for r, (name, f) in enumerate(self._fits.items()):
            st = f.get('stats') or {}
            show = QTableWidgetItem()
            show.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                          | Qt.ItemFlag.ItemIsSelectable)
            show.setCheckState(Qt.CheckState.Checked if f.get('visible', True) else Qt.CheckState.Unchecked)
            show.setData(Qt.ItemDataRole.UserRole, name)
            show.setToolTip('Show or hide this fit (and its bands) on the chart')
            t.setItem(r, 0, show)
            aic = st.get('aic')
            cells = [f.get('model', '') + f.get('tag', ''), f.get('lbl', ''),
                     f'{st["r2"]:.4f}' if st.get('r2') is not None else '',
                     f'{st["rmse"]:.4g}' if st.get('rmse') is not None else '',
                     f'{aic:.1f}' if aic is not None and aic == aic else '']
            for c, text in enumerate(cells, start=1):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if c >= 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 5 and aic is not None and aic == best.get(f.get('lbl')) \
                        and sum(1 for g in self._fits.values() if g.get('lbl') == f.get('lbl')) > 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setToolTip('Lowest AIC of the fits of this series')
                t.setItem(r, c, item)
        t.resizeColumnsToContents()
        t.setMaximumHeight(34 + 24 * max(1, min(len(self._fits), 5)))
        t.blockSignals(False)
        self._select_fit_table_row(selected if selected in self._fits else None)

    def _select_fit_table_row(self, name):
        """Highlight the row of fit *name* (or none) without triggering the selection handler."""
        if not hasattr(self, 'fit_table'):
            return
        t = self.fit_table
        t.blockSignals(True)
        t.clearSelection()
        for r in range(t.rowCount()):
            item = t.item(r, 0)
            if name is not None and item and item.data(Qt.ItemDataRole.UserRole) == name:
                t.selectRow(r)
                break
        t.blockSignals(False)

    def _on_fit_table_selected(self):
        """A row of the Fits list was clicked: make that fit the selected curve."""
        rows = self.fit_table.selectionModel().selectedRows()
        if not rows:
            return
        name = self.fit_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        label = self._fit_label(name)
        if self.curve_select.findText(label) < 0:        # it is on another subplot than the selector shows
            for row in range(self.series_table.rowCount()):
                ycb = self.series_table.cellWidget(row, 1)
                spin = self.series_table.cellWidget(row, 4)
                if ycb is not None and ycb.currentText() == name and spin is not None \
                        and hasattr(self, 'series_curve_sp_active'):
                    self.series_curve_sp_active.setCurrentIndex(spin.value() - 1)
                    break
        self.curve_select.setCurrentText(label)

    def _on_fit_table_item_changed(self, item):
        """The Show box of a fit was ticked or cleared."""
        if item.column() != 0:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name in self._fits:
            self._fits[name]['visible'] = item.checkState() == Qt.CheckState.Checked
            self._schedule_undo_snapshot('Show / hide fit')
            self.update_preview()

    def _on_fit_model_changed(self, choice):
        """Show the options that belong to the chosen model."""
        smoothing = choice == LOWESS_CHOICE
        self.fit_degree_row.setVisible(choice == POLYNOMIAL_CHOICE)
        self.fit_custom_box.setVisible(choice == CUSTOM_CHOICE)
        self.fit_span_row.setVisible(smoothing)
        self.fit_weight_check.setVisible(not smoothing)
        self.fit_robust_check.setVisible(not smoothing)

    def _refresh_fit_weight_option(self, *_):
        """Weighting needs an error column chosen in the Plot tab."""
        name = self.combo_err.currentText()
        has_errors = name in self.datasets
        self.fit_weight_check.setEnabled(has_errors)
        if not has_errors:
            self.fit_weight_check.setChecked(False)
        self.fit_weight_check.setText('Weight by the error column' + (f'  ({name})' if has_errors else '  (choose one in Plot)'))

    def _fit_x_range(self, xd):
        """((lo, hi) or None, (typed lo, typed hi)) from the two boxes; dates when x is a date."""
        from core.dates import is_date, parse_date
        texts = (self.fit_xfrom_edit.text().strip(), self.fit_xto_edit.text().strip())
        if not any(texts):
            return None, ('', '')
        values = []
        for text in texts:
            if not text:
                values.append(None)
                continue
            try:
                values.append(parse_date(text) if is_date(xd) else float(text))
            except ValueError:
                raise ValueError(f'"{text}" is not a valid x value for the fit range') from None
        lo, hi = values
        if lo is not None and hi is not None and lo > hi:
            raise ValueError('the fit range starts after it ends')
        return (lo, hi), texts

    def _fit_sigma(self, yd):
        """(the error column's values, its name) when weighting is on, else (None, '')."""
        if not self.fit_weight_check.isChecked():
            return None, ''
        name = self.combo_err.currentText()
        if name not in self.datasets:
            return None, ''
        sigma = np.asarray(self.datasets[name], dtype=float)
        if len(sigma) != len(yd):
            raise ValueError(f'the error column "{name}" has {len(sigma)} points but the series has {len(yd)}')
        return sigma, name

    def _selected_curve_text(self):
        return self.curve_select.currentText() if hasattr(self, 'curve_select') else ''

    def _fit_key_of_label(self, label):
        """The key in self._fits of the series row labelled *label* when that row is a fit curve:
        the label itself, or the dataset the row plots when the row was renamed.  Else None."""
        if label in self._fits:
            return label
        for row in range(self.series_table.rowCount()):
            item = self.series_table.item(row, 2)
            if item and item.text() == label:
                combo = self.series_table.cellWidget(row, 1)
                name = combo.currentText() if combo else ''
                return name if name in self._fits else None
        return None

    def _selected_curve_key(self):
        """The selected curve's key in self._fits if it is a fit curve, else its label."""
        label = self._selected_curve_text()
        return self._fit_key_of_label(label) or label

    def _on_ci_changed(self):
        label = self._selected_curve_key()
        if label and label in self._fits:
            self._fits[label]['ci_idx'] = self.fit_ci_combo.currentIndex()
            self._fits[label]['pi_idx'] = self.fit_pi_combo.currentIndex()
        self._schedule_undo_snapshot('Fit confidence / prediction band')
        self._update_confidence_band_for(label)
        self.update_preview()

    def apply_fit(self):
        try:
            choice = self.fit_combo.currentText()
            if choice == 'None': return
            start = None
            try:
                if choice == POLYNOMIAL_CHOICE:
                    model = CurveFitter.polynomial_key(self.fit_degree_spin.value())
                elif choice == CUSTOM_CHOICE:
                    model = CurveFitter.custom_key(self.fit_expr_edit.text())
                    start = parse_start_values(self.fit_start_edit.text())
                elif choice == LOWESS_CHOICE:
                    model = CurveFitter.lowess_key(self.fit_span_spin.value())
                else:
                    model = choice
            except ValueError as err:
                QMessageBox.warning(self, 'Fit Failed', str(err))
                return
            series = self._get_series_full()
            if not series:
                QMessageBox.warning(self, 'Warning', 'Add at least one series in the Data tab first.')
                return

            # Find the series the user selected in the per-curve selector
            target_label = self._selected_curve_key()
            fit_key = self._fit_key_of_label(target_label)
            if fit_key is not None:
                # A fit curve is selected (the app selects it after a fit, to style it): fit the
                # series it came from, not the curve, which would fit a fit and give bands of no width.
                source = self._fits[fit_key]
                matched = (next((s for s in series if s[2] == source.get('lbl')), None)
                           or next((s for s in series
                                    if (s[3], s[4]) == (source.get('xc'), source.get('yc'))), None))
                if matched is None:
                    QMessageBox.warning(self, 'Fit Failed',
                                        'The series this curve was fitted to is no longer in the table.')
                    return
            else:
                matched = next((s for s in series if s[2] == target_label), None)
                if matched is None:
                    matched = series[0]
            xd, yd, lbl, xc, yc = matched

            # Find the subplot (Plot spin value) of the source series row
            source_plot_num = 1
            source_y2 = False          # the fit goes on the same Y axis as its series
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                if item and item.text() == lbl:
                    spin = self.series_table.cellWidget(row, 4)
                    if spin:
                        source_plot_num = spin.value()
                    y2_src = self.series_table.item(row, 5)
                    source_y2 = bool(y2_src and y2_src.checkState() == Qt.CheckState.Checked)
                    break
            smoothing = choice == LOWESS_CHOICE
            try:
                x_range, range_text = self._fit_x_range(xd)
                sigma, err_col = (None, '') if smoothing else self._fit_sigma(yd)
                robust = self.fit_robust_check.isChecked() and not smoothing
                result = CurveFitter.fit_ex(xd, yd, model, start, x_range=x_range, sigma=sigma,
                                            robust=robust)       # skips NaN points, explains failures
            except ValueError as err:
                QMessageBox.warning(self, 'Fit Failed', f'Could not fit {model}: {err}.')
                return
            popt, pcov, func = result['popt'], result['pcov'], result['func']
            eq_str, r2, x0 = result['eq_str'], result['r2'], result['x0']
            used = result['used']

            # Full statistics (over the points that were fitted)
            stats = CurveFitter.full_stats(np.asarray(xd, dtype=float)[used], np.asarray(yd, dtype=float)[used],
                                           popt, pcov, func, model,
                                           sigma=None if sigma is None else sigma[used])

            # What distinguishes this fit from another of the same model on the same series
            tag_parts = []
            if x_range is not None:
                tag_parts.append(f'x {range_text[0] or "…"}–{range_text[1] or "…"}')
            if sigma is not None:
                tag_parts.append('weighted')
            if robust:
                tag_parts.append('robust')
            tag = ''.join(f', {t}' for t in tag_parts)

            # Add fit curve as a new dataset (NaN where the data have a NaN x)
            nm = f'{lbl} ({model}{tag} fit)'
            with np.errstate(all='ignore'):
                self.datasets[nm] = func(xd, *popt)

            # Store per-series fit for independent CI/PI bands
            existing = self._fits.get(nm, {})
            replaced = nm in self._fits                  # the same model on the same series again
            self._fits[nm] = dict(xd=xd, yd=yd, popt=popt, pcov=pcov, func=func, x0=x0,
                                  n_dropped=result['n_dropped'], n_excluded=result['n_excluded'],
                                  used=used, x_range=x_range, range_text=range_text,
                                  weighted=result['weighted'], err_col=err_col, robust=result['robust'],
                                  outliers=result['outliers'], n_outliers=result['n_outliers'],
                                  tag=tag, curve=result.get('curve'),
                                  model=model, xc=xc, yc=yc, lbl=lbl,
                                  eq_str=eq_str, r2=r2, stats=stats,
                                  ci_idx=existing.get('ci_idx', 0),
                                  pi_idx=existing.get('pi_idx', 0),
                                  visible=existing.get('visible', True), replaced=replaced)
            self._last_fit = self._fits[nm]

            # Seed a default style for the fit curve if it has none yet.
            # This makes it immediately editable via the Per-Curve section
            # without any ambiguity. Use dashed orange to visually distinguish
            # fit curves from raw data series.
            if nm not in self.curve_styles:
                src_color = self._next_fit_color(lbl, nm)
                self.curve_styles[nm] = {
                    'color':        src_color,
                    'linestyle':    '--',
                    'marker':       'None',
                    'linewidth':    1.8,
                    'markersize':   6,
                    'marker_color': src_color,
                    'color_locked': False,
                }

            self._schedule_undo_snapshot('Apply fit')
            self.update_lists()

            # Add fit curve as a new series row if not already present
            labels_in_table = []
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                if item: labels_in_table.append(item.text())
            if nm not in labels_in_table:
                row = self.series_table.rowCount()
                self.series_table.insertRow(row)
                for col_idx, col_name in ((0, xc), (1, nm)):
                    cb = QComboBox()
                    cb.addItems(sorted(self.datasets))
                    idx = cb.findText(col_name)
                    if idx >= 0: cb.setCurrentIndex(idx)
                    handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                    cb.currentIndexChanged.connect(handler)
                    self.series_table.setCellWidget(row, col_idx, cb)
                self.series_table.setItem(row, 2, QTableWidgetItem(nm))
                _mode = self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard'
                _allowed = list(PLOT_MODE_GROUPS.get(_mode, PER_SERIES_TYPES))
                type_cb = QComboBox()
                type_cb.addItems(_allowed)
                type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
                self.series_table.setCellWidget(row, 3, type_cb)
                plot_spin = QSpinBox()
                plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
                plot_spin.setValue(source_plot_num)
                plot_spin.valueChanged.connect(self.update_preview)
                self.series_table.setCellWidget(row, 4, plot_spin)
                y2_item = QTableWidgetItem()
                y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                y2_item.setCheckState(Qt.CheckState.Checked if source_y2 else Qt.CheckState.Unchecked)
                self.series_table.setItem(row, 5, y2_item)
            else:
                # Row already exists — keep its subplot in sync with the source
                for row in range(self.series_table.rowCount()):
                    item = self.series_table.item(row, 2)
                    if item and item.text() == nm:
                        spin = self.series_table.cellWidget(row, 4)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(source_plot_num)
                            spin.blockSignals(False)
                        y2_cell = self.series_table.item(row, 5)
                        if y2_cell:
                            y2_cell.setCheckState(Qt.CheckState.Checked if source_y2
                                                  else Qt.CheckState.Unchecked)
                        break

            self._update_confidence_band_for(nm)
            self._refresh_fit_results_panel(nm)
            if hasattr(self, '_fit_export_widget'):
                self._fit_export_widget.setEnabled(True)
            # Switch the Per-Curve selector to the fit curve so the user can
            # immediately style it — no ambiguity about which curve is active.
            if hasattr(self, 'curve_select'):
                idx = self.curve_select.findText(nm)
                if idx >= 0:
                    self.curve_select.setCurrentIndex(idx)
            self._load_fit_combos_for(nm)
            self._refresh_fit_table()
            self.update_preview()
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            QMessageBox.critical(self, 'Error', str(e))

    def _refresh_fit_results_panel(self, label=None):
        """Populate the fit results QTextEdit with full regression output."""
        if label is None:
            label = self._selected_curve_key()
        fit = self._fits.get(label)
        if fit is None:
            self.fit_results_text.setPlainText(
                'Select a fit curve (in the list above, or in Per-Curve) to see its results.'
                if self._fits else 'Run a fit to see results.')
            return
        st   = fit.get('stats', {})
        if not st:
            self.fit_results_text.setPlainText('No results.')
            return

        ci_pct = int((1 - st.get('alpha', 0.05)) * 100)
        lines = []
        lines.append(f'Model:  {fit["model"]}')
        lines.append(f'Equation:  {fit.get("eq_str", "")}')
        if fit.get('replaced'):
            lines.append('  (replaces the previous fit of this model on this series)')
        if fit.get('curve') is not None:
            lines.append('  A smoothing: no parameters, no bands, no tests.')
        if fit.get('x_range') is not None:
            lo, hi = fit.get('range_text') or ('', '')
            lines.append(f'  Fitted only for x from {lo or "the start"} to {hi or "the end"}; '
                         f'{fit.get("n_excluded", 0)} point(s) outside it were left out')
        if fit.get('weighted'):
            lines.append(f'  Weighted by the error column "{fit.get("err_col", "")}" '
                         f'(χ² = {st.get("chi2", float("nan")):.4g}, reduced χ² = '
                         f'{st.get("chi2_red", float("nan")):.3g}; near 1 when the errors match the scatter)')
        if fit.get('robust'):
            lines.append(f'  Robust fit: {fit.get("n_outliers", 0)} point(s) flagged as outliers; '
                         f'R² and RMSE below still include them')
        if fit.get('x0'):
            lines.append(f'  x₀ = {fit["x0"]:.10g}   (the parameters refer to x − x₀; the fit is '
                         f'done on x − x₀ because x is far from 0)')
        if fit.get('n_dropped'):
            lines.append(f'  {fit["n_dropped"]} point(s) with a NaN x or y were ignored')
        lines.append('')
        lines.append('── Goodness of Fit ──────────────────')
        lines.append(f'  n            = {st["n"]}')
        lines.append(f'  Parameters   = {st["p"]}')
        lines.append(f'  DoF          = {st["dof"]}')
        lines.append(f'  R²           = {st["r2"]:.6f}')
        lines.append(f'  Adj. R²      = {st["r2_adj"]:.6f}')
        lines.append(f'  RMSE         = {st["rmse"]:.6g}')
        if st.get('weighted'):                           # the sums are of weighted squares
            lines.append(f'  χ² / DoF     = {st["mse"]:.6g}   (reduced χ²)')
            lines.append(f'  χ²           = {st["sse"]:.6g}')
            lines.append(f'  Weighted SST = {st["sst"]:.6g}')
        else:
            lines.append(f'  MSE          = {st["mse"]:.6g}')
            lines.append(f'  SSE          = {st["sse"]:.6g}')
            lines.append(f'  SST          = {st["sst"]:.6g}')
        fv = st.get('f_stat', float('nan'))
        fp = st.get('f_pvalue', float('nan'))
        import math
        if st.get('weighted'):
            no_f = ' (not defined for a weighted fit)'
        else:
            no_f = '' if CurveFitter.has_f_test(fit.get('model', '')) else ' (not defined for this model)'
        lines.append(f'  F-statistic  = {fv:.4g}' if not math.isnan(fv) else f'  F-statistic  = —{no_f}')
        lines.append(f'  F p-value    = {fp:.4g}' if not math.isnan(fp) else f'  F p-value    = —{no_f}')
        lines.append(f'  AIC          = {st["aic"]:.4g}')
        lines.append(f'  BIC          = {st["bic"]:.4g}')
        yd_ok = np.asarray(fit.get('yd') if fit.get('yd') is not None else [], dtype=float)
        yd_ok = yd_ok[np.isfinite(yd_ok)]
        scale = max(1.0, abs(float(yd_ok.mean()))) if len(yd_ok) else 1.0
        if st.get('rmse', 1.0) <= 1e-9 * scale:
            lines.append('  The data lie exactly on the curve: the confidence and prediction')
            lines.append('  bands have no width, so they cannot be seen.')
        pcov = fit.get('pcov')
        if pcov is not None and len(pcov) and not np.all(np.isfinite(np.asarray(pcov, dtype=float))):
            lines.append('  The uncertainty of the parameters could not be estimated (too few points')
            lines.append('  for this model, or the data do not follow it): no bands can be drawn.')
        lines.append('')
        lines.append(f'── Parameters  ({ci_pct}% CI) ──────────────')
        names  = st['param_names']
        vals   = st['param_values']
        ses    = st['param_se']
        tstats = st['param_tstat']
        pvals  = st['param_pvalue']
        cilo   = st['param_ci_lo']
        cihi   = st['param_ci_hi']
        for i in range(st['p']):
            pv = pvals[i]
            tv = tstats[i]
            pv_str = f'{pv:.4g}' if not math.isnan(pv) else '—'
            tv_str = f'{tv:.4g}' if not math.isnan(tv) else '—'
            lo_str = f'{cilo[i]:.4g}' if not math.isnan(cilo[i]) else '—'
            hi_str = f'{cihi[i]:.4g}' if not math.isnan(cihi[i]) else '—'
            lines.append(f'  {names[i]}')
            lines.append(f'    value  = {vals[i]:.6g}  ±{ses[i]:.4g}')
            lines.append(f'    t      = {tv_str}    p = {pv_str}')
            lines.append(f'    CI     = [{lo_str}, {hi_str}]')
        self.fit_results_text.setPlainText('\n'.join(lines))

    def _update_confidence_band_for(self, label):
        """Recompute CI/PI band datasets for one fit-curve label."""
        if not label:
            return
        fit = self._fits.get(label)
        if fit is None:
            return
        base = label
        ci_idx = fit.get('ci_idx', 0)
        pi_idx = fit.get('pi_idx', 0)
        for suffix in (' CI upper', ' CI lower', ' PI upper', ' PI lower'):
            self.datasets.pop(base + suffix, None)
        dof = (fit.get('stats') or {}).get('dof')
        if len(fit['popt']) == 0:                       # a smoothing has no parameters, so no bands
            return
        if ci_idx > 0:
            y_ci_hi, y_ci_lo = CurveFitter.confidence_band(
                fit['xd'], fit['popt'], fit['pcov'], fit['func'], ci_idx, dof)
            self.datasets[base + ' CI upper'] = y_ci_hi
            self.datasets[base + ' CI lower'] = y_ci_lo
        if pi_idx > 0 and 'yd' in fit:
            y_pi_hi, y_pi_lo = CurveFitter.prediction_band(
                fit['xd'], fit['yd'], fit['popt'], fit['pcov'], fit['func'], pi_idx,
                used=fit.get('used'))
            self.datasets[base + ' PI upper'] = y_pi_hi
            self.datasets[base + ' PI lower'] = y_pi_lo

    def _load_fit_combos_for(self, label):
        """Sync CI/PI combos to the stored state for a given fit-curve label."""
        fit = self._fits.get(label)
        self.fit_ci_combo.blockSignals(True)
        self.fit_pi_combo.blockSignals(True)
        self.fit_ci_combo.setCurrentIndex(fit['ci_idx'] if fit else 0)
        self.fit_pi_combo.setCurrentIndex(fit['pi_idx'] if fit else 0)
        self.fit_ci_combo.blockSignals(False)
        self.fit_pi_combo.blockSignals(False)
        has_bands = fit is None or len(fit['popt']) > 0       # a smoothing has no bands
        for combo in (self.fit_ci_combo, self.fit_pi_combo):
            combo.setEnabled(has_bands)
            combo.setToolTip('' if has_bands else 'A smoothing has no parameters, so no bands')

    def _on_fit_series_changed(self):
        """Called when curve_select changes — refresh CI/PI combos and results panel."""
        label = self._selected_curve_key()
        is_fit = label in self._fits
        has_any_fits = bool(self._fits)
        if hasattr(self, '_fit_controls_widget'):
            self._fit_controls_widget.setEnabled(is_fit)
        if hasattr(self, '_fit_export_widget'):
            self._fit_export_widget.setEnabled(has_any_fits)
        self._select_fit_table_row(label if is_fit else None)
        if not is_fit:
            if hasattr(self, 'fit_results_text'):
                self.fit_results_text.setPlainText(
                    'Select a fit curve (in the list above, or in Per-Curve) to see its results.'
                    if has_any_fits else 'Run a fit to see results.')
            self._load_fit_combos_for('')
            return
        self._load_fit_combos_for(label)
        self._refresh_fit_results_panel(label)

    def _remove_fits_for_labels(self, source_labels):
        """Remove all fitted curves whose source series is in source_labels.

        Does NOT call update_preview — callers are responsible for that.
        Returns True if anything was removed.
        """
        targets = []
        for lbl in source_labels:
            if lbl in self._fits:
                targets.append(lbl)          # fit curve itself selected
            else:
                targets += [nm for nm in list(self._fits) if self._fits[nm].get('lbl') == lbl]

        if not targets:
            return False

        for nm in targets:
            for suffix in ('', ' CI upper', ' CI lower', ' PI upper', ' PI lower'):
                self.datasets.pop(nm + suffix, None)
            self._fits.pop(nm, None)
            self.curve_styles.pop(nm, None)
            for row in range(self.series_table.rowCount() - 1, -1, -1):
                item = self.series_table.item(row, 2)
                ycb = self.series_table.cellWidget(row, 1)
                # the row of the fit curve, even if its label was renamed (it still plots nm)
                if (item and item.text() == nm) or (ycb is not None and ycb.currentText() == nm):
                    self.series_table.removeRow(row)
                    break

        if hasattr(self, 'fit_results_text'):
            self.fit_results_text.setPlainText(
                'Select a fit curve (in the list above, or in Per-Curve) to see its results.'
                if self._fits else 'Run a fit to see results.')
        self._refresh_fit_table()
        return True

    def _remove_fit(self):
        """Remove the fitted curve(s) associated with the currently selected series."""
        label = self._selected_curve_key()
        if not label:
            return

        if label in self._fits:
            targets = [label]                              # a fit curve is selected: only that one
        else:
            targets = [nm for nm, f in self._fits.items() if f.get('lbl') == label]
        if not targets:
            QMessageBox.information(self, 'No Fit', 'No fitted curve found for the selected series.')
            return
        if len(targets) > 1:
            answer = QMessageBox.question(
                self, 'Remove fits',
                f'Remove all {len(targets)} fits of "{label}"?\n\n'
                'To remove just one, select that fit curve first.')
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._schedule_undo_snapshot('Remove fit')
        self._remove_fits_for_labels(targets)

        self.update_lists()
        self.update_preview()

    def _export_fit_results(self):
        """Save fit results to .txt — either the current fit or all fits if the checkbox is ticked."""
        import math
        from PyQt6.QtWidgets import QFileDialog

        # ── Glossary tables (shared) ──────────────────────────────────────────
        _MODEL_GLOSSARY = {
            'Linear': [
                ('a', 'Slope — change in y per unit change in x'),
                ('b', 'Intercept — value of y when x = 0'),
            ],
            'Quadratic': [
                ('a', 'Coefficient of x² — controls the curvature and opening direction'),
                ('b', 'Coefficient of x — controls the tilt of the parabola'),
                ('c', 'Constant — value of y when x = 0'),
            ],
            'Cubic': [
                ('a', 'Coefficient of x³ — controls the dominant curvature at large |x|'),
                ('b', 'Coefficient of x² — controls secondary curvature'),
                ('c', 'Coefficient of x — controls the slope near x = 0'),
                ('d', 'Constant — value of y when x = 0'),
            ],
            'Exponential': [
                ('a', 'Amplitude — scaling factor / value of y when x = 0'),
                ('b', 'Rate — positive = growth, negative = decay; half-life = ln(2)/|b|'),
            ],
            'Power Law': [
                ('a', 'Coefficient — scaling factor'),
                ('b', 'Exponent — b > 1: super-linear, 0 < b < 1: sub-linear, b < 0: inverse'),
            ],
            'Logarithmic': [
                ('a', 'Log coefficient — steepness of the log curve'),
                ('b', 'Offset — vertical shift'),
            ],
            'Exponential + offset': [
                ('a', 'Amplitude of the exponential part (its value at x = 0, above the offset)'),
                ('b (rate)', 'Rate — negative: decays towards the offset; positive: grows away from it'),
                ('c (offset)', 'Offset — the value the curve settles at when b < 0'),
            ],
            'Gaussian': [
                ('a (amplitude)', 'Height of the peak above the offset (negative for a dip)'),
                ('μ (centre)', 'x position of the peak'),
                ('σ (width)', 'Standard deviation; the full width at half maximum is 2.355·σ'),
                ('c (offset)', 'Baseline the peak sits on'),
            ],
            'Sinusoid': [
                ('a (amplitude)', 'Half the peak-to-peak size of the oscillation'),
                ('f (frequency)', 'Cycles per x unit; the period is 1/f'),
                ('φ (phase, rad)', 'Shift of the oscillation (a sine starts at phase 0)'),
                ('c (offset)', 'Mean level the oscillation is centred on'),
            ],
            'Sigmoid': [
                ('a', 'Ceiling — upper asymptote (maximum value the curve approaches)'),
                ('b (midpoint)', 'Midpoint — x value at 50% of the ceiling (inflection point)'),
                ('c (scale)', 'Scale — steepness; small |c| = steep, large |c| = gradual'),
            ],
        }
        _STATS_GLOSSARY = [
            ('n',           'Number of data points used in the fit'),
            ('Parameters',  'Number of free parameters estimated by the model'),
            ('DoF',         'Degrees of freedom = n − Parameters'),
            ('R²',          'Coefficient of determination — fraction of variance explained (0–1; closer to 1 is better)'),
            ('Adj. R²',     'R² penalised for extra parameters; more reliable for comparing models with different complexity'),
            ('RMSE',        'Root Mean Squared Error — typical size of residuals in y-units (lower is better)'),
            ('MSE',         'Mean Squared Error = RMSE²'),
            ('SSE',         'Sum of Squared Errors — total squared deviation of fitted values from data'),
            ('SST',         'Total Sum of Squares — total squared deviation of data from its mean'),
            ('F-statistic', 'Tests whether the model explains significantly more variance than a flat mean'),
            ('F p-value',   'Probability of observing this F under the null hypothesis; < 0.05 is conventionally significant'),
            ('AIC',         'Akaike Information Criterion — lower = better trade-off of fit quality vs. model complexity'),
            ('BIC',         'Bayesian Information Criterion — like AIC but penalises complexity more heavily'),
        ]
        _PARAM_STATS_GLOSSARY = [
            ('value ± SE',  'Estimated parameter value and its standard error'),
            ('t',           't-statistic for H₀: parameter = 0 (larger |t| = stronger evidence the parameter matters)'),
            ('p',           'p-value for the t-test; < 0.05 suggests the parameter is statistically significant'),
            ('CI',          'Confidence interval — range likely to contain the true parameter value at the stated confidence level'),
        ]

        def _glossary_entries(model):
            if model in _MODEL_GLOSSARY:
                return _MODEL_GLOSSARY[model]
            try:
                names = CurveFitter.spec(model).param_names
            except ValueError:
                return []
            if model.startswith(POLYNOMIAL_PREFIX):
                return [(n, f'Coefficient of x^{n[1:]}') for n in names]
            return [(n, 'Parameter of the expression') for n in names]

        def _build_glossary(models_used):
            gl = ['', '═' * 52, 'GLOSSARY', '═' * 52]
            shown = set()
            for model in models_used:
                entries = _glossary_entries(model)
                if entries and model not in shown:
                    shown.add(model)
                    gl.append('')
                    gl.append(f'── Model parameters  ({model}) ──────────────')
                    for name, meaning in entries:
                        gl.append(f'  {name:<20}  {meaning}')
            gl.append('')
            gl.append('── Goodness-of-fit statistics ────────────────')
            for name, meaning in _STATS_GLOSSARY:
                gl.append(f'  {name:<16}  {meaning}')
            gl.append('')
            gl.append('── Per-parameter statistics ──────────────────')
            for name, meaning in _PARAM_STATS_GLOSSARY:
                gl.append(f'  {name:<16}  {meaning}')
            return gl

        def _fit_block(nm, fit):
            """Return lines for one fit result, including series/axis context."""
            st = fit.get('stats', {})
            if not st:
                return [f'  (no statistics available for {nm})']
            ci_pct = int((1 - st.get('alpha', 0.05)) * 100)
            lines = []
            lines.append(f'Series:    {fit.get("lbl", nm)}')
            lines.append(f'X column:  {fit.get("xc", "—")}')
            lines.append(f'Y column:  {fit.get("yc", "—")}')
            lines.append(f'Fit name:  {nm}')
            lines.append(f'Model:     {fit["model"]}')
            lines.append(f'Equation:  {fit.get("eq_str", "")}')
            lines.append('')
            lines.append('── Goodness of Fit ──────────────────')
            lines.append(f'  n            = {st["n"]}')
            lines.append(f'  Parameters   = {st["p"]}')
            lines.append(f'  DoF          = {st["dof"]}')
            lines.append(f'  R²           = {st["r2"]:.6f}')
            lines.append(f'  Adj. R²      = {st["r2_adj"]:.6f}')
            lines.append(f'  RMSE         = {st["rmse"]:.6g}')
            lines.append(f'  MSE          = {st["mse"]:.6g}')
            lines.append(f'  SSE          = {st["sse"]:.6g}')
            lines.append(f'  SST          = {st["sst"]:.6g}')
            fv = st.get('f_stat', float('nan'))
            fp = st.get('f_pvalue', float('nan'))
            lines.append(f'  F-statistic  = {fv:.4g}' if not math.isnan(fv) else '  F-statistic  = —')
            lines.append(f'  F p-value    = {fp:.4g}' if not math.isnan(fp) else '  F p-value    = —')
            lines.append(f'  AIC          = {st["aic"]:.4g}')
            lines.append(f'  BIC          = {st["bic"]:.4g}')
            lines.append('')
            lines.append(f'── Parameters  ({ci_pct}% CI) ──────────────')
            names  = st['param_names']
            vals   = st['param_values']
            ses    = st['param_se']
            tstats = st['param_tstat']
            pvals  = st['param_pvalue']
            cilo   = st['param_ci_lo']
            cihi   = st['param_ci_hi']
            for i in range(st['p']):
                pv = pvals[i]
                tv = tstats[i]
                pv_str = f'{pv:.4g}' if not math.isnan(pv) else '—'
                tv_str = f'{tv:.4g}' if not math.isnan(tv) else '—'
                lo_str = f'{cilo[i]:.4g}' if not math.isnan(cilo[i]) else '—'
                hi_str = f'{cihi[i]:.4g}' if not math.isnan(cihi[i]) else '—'
                lines.append(f'  {names[i]}')
                lines.append(f'    value  = {vals[i]:.6g}  ±{ses[i]:.4g}')
                lines.append(f'    t      = {tv_str}    p = {pv_str}')
                lines.append(f'    CI     = [{lo_str}, {hi_str}]')
            return lines

        # ── Determine what to export ──────────────────────────────────────────
        export_all = (hasattr(self, 'fit_export_all_check') and
                      self.fit_export_all_check.isChecked())

        if export_all:
            if not self._fits:
                QMessageBox.information(self, 'No Results', 'No fitted curves found.')
                return
            fits_to_export = list(self._fits.items())
            default_name = 'all_fits_results.txt'
        else:
            label = self._selected_curve_key()
            fit = self._fits.get(label)
            if fit is None or not fit.get('stats'):
                QMessageBox.information(self, 'No Results',
                                        'Select a fit curve first, or tick "All fits".')
                return
            fits_to_export = [(label, fit)]
            safe = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in label).strip() or 'fit'
            default_name = f'{safe}_results.txt'

        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Fit Results', default_name, 'Text files (*.txt);;All files (*)')
        if not path:
            return

        # ── Build full output ─────────────────────────────────────────────────
        all_lines = []
        models_used = []
        sep = '─' * 52

        if export_all:
            all_lines.append('═' * 52)
            all_lines.append(f'  CURVE FIT RESULTS  —  {len(fits_to_export)} fit(s)')
            all_lines.append('═' * 52)

        for i, (nm, fit) in enumerate(fits_to_export):
            if export_all and i > 0:
                all_lines.append('')
                all_lines.append(sep)
            all_lines += _fit_block(nm, fit)
            model = fit.get('model', '')
            if model and model not in models_used:
                models_used.append(model)

        all_lines += _build_glossary(models_used)

        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(all_lines))
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'Fit results saved to {path}', 4000)
        except (OSError, UnicodeError) as e:
            QMessageBox.critical(self, 'Export Failed', str(e))

        # ═══════════════════════════════════════════════════════════════════════════
    # PLOTTING
    # ═══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _is_categorical(arr):
        """Return True if arr is a string/object array (categorical)."""
        try:
            return arr is not None and hasattr(arr, 'dtype') and arr.dtype.kind in ('U', 'S', 'O')
        except (AttributeError, TypeError):
            return False
