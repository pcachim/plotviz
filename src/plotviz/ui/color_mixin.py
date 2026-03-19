"""
Copyright (c) 2026 Paulo Cachim
ui/color_mixin.py — color/palette helpers, annotation handlers, figure size,
                    grid color, annotation mode, annotation list management
"""
from PyQt6.QtWidgets import QMessageBox, QDialog, QFileDialog, QInputDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.helpers import _show_color_dialog, _get_dir, _remember_dir
from ui.dialogs import AnnotationEditDialog, PaletteColorDialog


from ui.palette_mixin import PaletteMixin
from ui.annotation_mixin import AnnotationMixin

class ColorAnnotationMixin(PaletteMixin, AnnotationMixin):
    def _apply_colour_scheme(self, scheme: str = None):
        """Apply Light / Dark / System colour scheme using Qt's native API."""
        app = QApplication.instance()

        if scheme is None:
            scheme = getattr(self, 'colour_scheme_combo',
                             None) and self.colour_scheme_combo.currentText() or 'System'

        self._colour_mode = scheme.lower()
        settings.set('theme', scheme)

        try:
            # Qt 6.5+ native path — lets the platform handle the palette
            hints = app.styleHints()
            mapping = {
                'Light':  Qt.ColorScheme.Light,
                'Dark':   Qt.ColorScheme.Dark,
                'System': Qt.ColorScheme.Unknown,
            }
            hints.setColorScheme(mapping.get(scheme, Qt.ColorScheme.Unknown))
        except AttributeError:
            # Fallback for Qt < 6.5: manual palette
            from PyQt6.QtGui import QColor, QPalette
            if scheme == 'Dark':
                p = QPalette()
                p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
                p.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.Base,            QColor(45, 45, 45))
                p.setColor(QPalette.ColorRole.AlternateBase,   QColor(55, 55, 55))
                p.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
                p.setColor(QPalette.ColorRole.Button,          QColor(55, 55, 55))
                p.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
                p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
                p.setColor(QPalette.ColorRole.Link,            QColor(42, 130, 218))
                p.setColor(QPalette.ColorRole.Mid,             QColor(70, 70, 70))
                p.setColor(QPalette.ColorRole.Shadow,          QColor(20, 20, 20))
                p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(45, 45, 45))
                p.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
                app.setPalette(p)
            elif scheme == 'Light':
                app.setPalette(QPalette())
            else:
                app.setPalette(app.style().standardPalette())

        self.update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # CHART TYPE VISIBILITY
    # ═══════════════════════════════════════════════════════════════════════════
    def _update_option_group_visibility(self, ct):
        """Show/hide chart-type option groups for the given chart type string."""
        if not hasattr(self, 'hist_group'):
            return
        vis = {
            self.line_group:      ct == 'Line',
            self.scatter_group:   ct == 'Scatter',
            self.bar_group:       ct == 'Bar',
            self.hist_group:      ct == 'Histogram',
            self.err_group:       ct == 'Errorbar',
            self.heat_group:      ct in ('Heatmap', 'Contour', '3D Surface'),
            self.pie_group:       ct == 'Pie',
            self.area_group:      ct == 'Area',
            self.violin_group:    ct == 'Violin',
            self.boxplot_group:   ct == 'Boxplot',
            self.step_group:      ct == 'Step',
            self.stem_group:      ct == 'Stem',
            self.bubble_group:    ct == 'Bubble',
            self.waterfall_group: ct == 'Waterfall',
            self.hist2d_group:    ct == 'Hist2D',
            self.hexbin_group:    ct == 'Hexbin',
            self.polar_group:     ct == 'Polar',
            self.radar_group:     ct == 'Radar',
            self.ecdf_group:      ct == 'ECDF',
            self.quiver_group:    ct == 'Quiver',
        }
        for grp, show in vis.items():
            grp.setVisible(show)

    def _on_chart_type_changed(self, ct):
        """Chart type selector changed — push to all selected series rows, update option groups."""
        # Push to every selected row's Type combo (col 3)
        if hasattr(self, 'series_table'):
            selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
            if not selected_rows:
                selected_rows = set(range(self.series_table.rowCount()))
            for row in selected_rows:
                type_cb = self.series_table.cellWidget(row, 3)
                if type_cb:
                    type_cb.blockSignals(True)
                    i = type_cb.findText(ct)
                    if i >= 0: type_cb.setCurrentIndex(i)
                    type_cb.blockSignals(False)
        self._update_option_group_visibility(ct)
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _on_series_selection_changed(self):
        """Series table selection changed — pull chart type from the first selected row."""
        if not hasattr(self, 'chart_type_combo'): return
        selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
        if not selected_rows: return
        row = min(selected_rows)
        type_cb = self.series_table.cellWidget(row, 3)
        if type_cb:
            ct = type_cb.currentText()
            self.chart_type_combo.blockSignals(True)
            i = self.chart_type_combo.findText(ct)
            if i >= 0: self.chart_type_combo.setCurrentIndex(i)
            self.chart_type_combo.blockSignals(False)
            self._update_option_group_visibility(ct)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _hline(self):
        ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine); ln.setFrameShadow(QFrame.Shadow.Sunken)
        return ln

    @staticmethod
    def _sec_label(txt):
        """Section header label styled like the DATASETS label."""
        from PyQt6.QtWidgets import QLabel
        lbl = QLabel(txt.upper())
        lbl.setStyleSheet('font-weight:bold; color:#888; font-size:10px;')
        return lbl

    def _get_xscale(self):
        for b in self.xscale_group.buttons():
            if b.isChecked(): return b.property('scale_value')
        return 'linear'

    def _get_yscale(self):
        for b in self.yscale_group.buttons():
            if b.isChecked(): return b.property('scale_value')
        return 'linear'

    def _set_scale_rb(self, group, value):
        """Check the radio button whose scale_value matches value."""
        for b in group.buttons():
            b.blockSignals(True)
            b.setChecked(b.property('scale_value') == value)
            b.blockSignals(False)

    def _apply_scale(self, ax, xs, ys):
        for scale, inv_fn, set_fn in [(xs, ax.invert_xaxis, ax.set_xscale),
                                       (ys, ax.invert_yaxis, ax.set_yscale)]:
            if scale == 'inverted':
                set_fn('linear'); inv_fn()
            else:
                try: set_fn(scale)
                except Exception: set_fn('linear')

    def _tab10(self, n):
        """Legacy shim — returns n colors from the active palette (cycling if needed)."""
        return [self._palette_color(i) for i in range(n)]

    def _palette_color(self, idx):
        """Return the hex color for series index `idx` using the active palette."""
        all_pals = get_all_palettes()
        pal_name = getattr(self, '_color_palette', 'Matplotlib')
        colors = all_pals.get(pal_name, COLOR_PALETTES['Matplotlib'])
        return colors[idx % len(colors)]

    def _refresh_palette_swatches(self):
        """Update the 16 swatch squares in the Data tab to show the active palette."""
        all_pals = get_all_palettes()
        pal_name = getattr(self, '_color_palette', 'Matplotlib')
        colors = all_pals.get(pal_name, COLOR_PALETTES['Matplotlib'])
        for i, sw in enumerate(getattr(self, '_palette_swatches', [])):
            c = colors[i % len(colors)]
            sw.setStyleSheet(f'background:{c}; border:1px solid #888;')

    def _on_palette_changed(self, name):
        """Called when the palette combo changes. Updates state and re-colors unlocked series."""
        self._color_palette = name
        settings.set('color_palette', name)
        self._refresh_palette_swatches()
        # Re-assign auto-colors to every series row that has no manually locked color.
        for row in range(self.series_table.rowCount()):
            lbl = self._resolve_series_label(row)
            s = self.curve_styles.get(lbl, {})
            if not s.get('color_locked', False):
                new_color = self._palette_color(self._local_palette_index(row))
                s['color'] = new_color
                s['marker_color'] = new_color
                self.curve_styles[lbl] = s
        self._refresh_lock_indicator()
        # Refresh the curve colour swatches visible in the Style tab
        self.load_curve_style()
        self.update_preview()

    def _resolve_series_label(self, row):
        """Return the label string for a series table row — same logic as _get_series."""
        lbl_item = self.series_table.item(row, 2)
        ycb = self.series_table.cellWidget(row, 1)
        cell_text = lbl_item.text() if lbl_item else ''
        y_col = ycb.currentText() if ycb else ''
        return cell_text if cell_text else (y_col if y_col else f'Series {row+1}')

    def _local_palette_index(self, global_row):
        """Return how many valid series rows before `global_row` share the same subplot.
        This is the local colour index — so every subplot restarts at 0."""
        n = self.subplot_rows * self.subplot_cols
        plot_spin_target = self.series_table.cellWidget(global_row, 4)
        if plot_spin_target is None:
            return global_row  # fallback
        target_subplot = (plot_spin_target.value() - 1) if n > 1 else 0
        local_idx = 0
        for r in range(global_row):
            xcb = self.series_table.cellWidget(r, 0)
            ycb = self.series_table.cellWidget(r, 1)
            if xcb is None or ycb is None:
                continue
            ps = self.series_table.cellWidget(r, 4)
            row_subplot = (ps.value() - 1) if (ps and n > 1) else 0
            if row_subplot == target_subplot:
                xc = xcb.currentText()
                yc = ycb.currentText()
                if xc in self.datasets and yc in self.datasets:
                    local_idx += 1
        return local_idx

    def _reset_all_color_locks(self):
        """Remove color_locked from every series and re-apply the active palette."""
        for row in range(self.series_table.rowCount()):
            lbl = self._resolve_series_label(row)
            s = self.curve_styles.get(lbl, {})
            s.pop('color_locked', None)
            new_color = self._palette_color(self._local_palette_index(row))
            s['color'] = new_color
            s['marker_color'] = new_color
            self.curve_styles[lbl] = s
        self._refresh_lock_indicator()
        self.update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # RECENT FILES
    # ═══════════════════════════════════════════════════════════════════════════
    def _rebuild_recent_files_ui(self):
        """Refresh the recent-files list widget in the File tab."""
        if not hasattr(self, '_recent_list'):
            return
        self._recent_list.clear()
        for fp in settings.get_recent_files():
            self._recent_list.addItem(os.path.basename(fp))
            item = self._recent_list.item(self._recent_list.count() - 1)
            item.setToolTip(fp)
            item.setData(Qt.ItemDataRole.UserRole, fp)

    def _open_recent_file(self, item):
        """Open a recently used chart file chosen from the list."""
        fp = item.data(Qt.ItemDataRole.UserRole)
        if not fp or not os.path.isfile(fp):
            QMessageBox.warning(self, 'Not found', f'File no longer exists:\n{fp}')
            settings.prune_recent_files()
            self._rebuild_recent_files_ui()
            return
        self._load_project_from_path(fp)

    # ═══════════════════════════════════════════════════════════════════════════
    # CUSTOM PALETTE EDITOR
    # ═══════════════════════════════════════════════════════════════════════════
    def pick_color(self, target):
        # Determine current color for initial value
        _cur = {
            'chart_bg':     getattr(self, 'chart_bg_color',    '#ffffff'),
            'chart_fg':     getattr(self, 'chart_fg_color',    '#000000'),
            'plot_bg':      getattr(self, 'plot_bg_color',     '#ffffff'),
            'fit_color':    getattr(self, 'fit_color',         '#ff7700'),
            'title':        getattr(self, 'title_color',       '#000000'),
            'xlabel':       getattr(self, 'xlabel_color',      '#000000'),
            'ylabel':       getattr(self, 'ylabel_color',      '#000000'),
            'y2label':      getattr(self, 'y2label_color',     '#000000'),
            'curve':        getattr(self, 'curve_color',       '#1f77b4'),
            'curve_marker': getattr(self, 'curve_marker_color','#1f77b4'),
        }.get(target, '#000000')
        color = PaletteColorDialog.getColor(
            QColor(_cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        # Chart-canvas colors
        if target in ('chart_bg', 'chart_fg', 'plot_bg'):
            attr = target + '_color'
            setattr(self, attr, hx)
            getattr(self, attr + '_swatch').setStyleSheet(f'color:{hx};font-size:18px;')
            getattr(self, attr + '_hex').setText(hx)
            self.update_preview()
            return
        if target == 'fit_color':
            self.fit_color = hx
            self.fit_color_swatch.setStyleSheet(f'color:{hx};font-size:18px;')
            self.fit_color_hex_lbl.setText(hx)
            self.update_preview(); return
        mapping = {
            'title':        ('title_color',        'title_color_label',        'style'),
            'xlabel':       ('xlabel_color',        'xlabel_color_label',       'style'),
            'ylabel':       ('ylabel_color',        'ylabel_color_label',       'style'),
            'y2label':      ('y2label_color',       'y2label_color_label',      'style'),
            'curve':        ('curve_color',         'curve_color_label',        'swatch'),
            'curve_marker': ('curve_marker_color',  'curve_marker_color_label', 'swatch'),
        }
        attr, lbl_attr, mode = mapping[target]
        setattr(self, attr, hx)
        lbl = getattr(self, lbl_attr)
        if mode == 'style':
            lbl.setStyleSheet(f'color:{hx};font-size:16px;')
        else:  # swatch — force the square to render in the chosen color
            lbl.setText('■')
            lbl.setStyleSheet(f'color:{hx};font-size:16px;')
        if target in ('curve', 'curve_marker'):
            self.save_curve_style(lock_color=True)
        self.update_preview()

    def _sync_ann_style(self):
        if not hasattr(self,'canvas'): return
        self.canvas.ann_style = {
            'fontsize':   self.ann_fontsize.value(),
            'fontcolor':  self.ann_fontcolor,
            'fontfamily': self.ann_font.currentText(),
            'bg_color':   self.ann_bgcolor,
            'bg_alpha':   self.ann_bg_alpha.value(),
            'edge_color': self.ann_edgecolor,
        }

