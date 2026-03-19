"""
Copyright (c) 2026 Paulo Cachim
ui/annotation_mixin.py  –  plotviz
AnnotationMixin: annotation placement mode, list management, figure size helpers.
"""
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog
from PyQt6.QtCore import Qt
from ui.dialogs import AnnotationEditDialog, PaletteColorDialog


class AnnotationMixin:
    def _fig_size_in_inches(self):
        """Convert current fig_width/fig_height spinbox values to inches."""
        w, h = self.fig_width.value(), self.fig_height.value()
        unit = self.fig_unit.currentText()
        if unit == 'cm':
            return w / 2.54, h / 2.54
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            return w / dpi, h / dpi
        return w, h   # already inches

    def _on_fig_preset_changed(self, idx):
        """Apply a size preset (values are always in cm; convert to current unit)."""
        _, w_cm, h_cm = self._fig_presets[idx]
        if w_cm is None: return  # Custom — don't touch spinboxes
        unit = self.fig_unit.currentText()
        self.fig_width.blockSignals(True); self.fig_height.blockSignals(True)
        if unit == 'cm':
            self.fig_width.setValue(w_cm); self.fig_height.setValue(h_cm)
        elif unit == 'inches':
            self.fig_width.setValue(round(w_cm / 2.54, 2))
            self.fig_height.setValue(round(h_cm / 2.54, 2))
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            self.fig_width.setValue(round(w_cm / 2.54 * dpi))
            self.fig_height.setValue(round(h_cm / 2.54 * dpi))
        self.fig_width.blockSignals(False); self.fig_height.blockSignals(False)
        self.update_preview()

    def _on_figsize_manual_change(self):
        """When user edits W/H manually, switch preset combo to 'Custom'."""
        self.fig_preset_combo.blockSignals(True)
        self.fig_preset_combo.setCurrentText('Custom')
        self.fig_preset_combo.blockSignals(False)
        self.update_preview()

    def _on_fig_unit_changed(self, unit):
        """When unit changes, convert current displayed values to the new unit."""
        # First read current inches value
        wi, hi = self._fig_size_in_inches()
        self.fig_width.blockSignals(True); self.fig_height.blockSignals(True)
        if unit == 'cm':
            self.fig_width.setRange(2, 500); self.fig_height.setRange(2, 500)
            self.fig_width.setDecimals(1); self.fig_height.setDecimals(1)
            self.fig_width.setSingleStep(0.5); self.fig_height.setSingleStep(0.5)
            self.fig_width.setValue(round(wi * 2.54, 1))
            self.fig_height.setValue(round(hi * 2.54, 1))
        elif unit == 'inches':
            self.fig_width.setRange(1, 200); self.fig_height.setRange(1, 200)
            self.fig_width.setDecimals(2); self.fig_height.setDecimals(2)
            self.fig_width.setSingleStep(0.25); self.fig_height.setSingleStep(0.25)
            self.fig_width.setValue(round(wi, 2))
            self.fig_height.setValue(round(hi, 2))
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            self.fig_width.setRange(50, 20000); self.fig_height.setRange(50, 20000)
            self.fig_width.setDecimals(0); self.fig_height.setDecimals(0)
            self.fig_width.setSingleStep(10); self.fig_height.setSingleStep(10)
            self.fig_width.setValue(round(wi * dpi))
            self.fig_height.setValue(round(hi * dpi))
        self.fig_width.blockSignals(False); self.fig_height.blockSignals(False)
        self.update_preview()

    def _pick_grid_color(self, which):
        cur = self.grid_color if which == 'major' else self.minor_grid_color
        color = PaletteColorDialog.getColor(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        if which == 'major':
            self.grid_color = hx
            self.grid_color_sw.setStyleSheet(f'color:{hx};font-size:16px;')
        else:
            self.minor_grid_color = hx
            self.minor_grid_color_sw.setStyleSheet(f'color:{hx};font-size:16px;')
        self.update_preview()

    def _pick_ann_color_attr(self, attr):
        """Generic color picker that writes to self.<attr> and updates <attr>_sw swatch."""
        cur = getattr(self, attr, '#000000')
        color = PaletteColorDialog.getColor(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        setattr(self, attr, hx)
        sw = getattr(self, attr + '_sw', None)
        if sw: sw.setStyleSheet(f'color:{hx};font-size:16px;')
        self._sync_ann_style()

    def _pick_ann_color(self, target):
        """Legacy shim — routes to the generic attr picker."""
        mapping = {'font': 'ann_fontcolor', 'bg': 'ann_bgcolor', 'edge': 'ann_edgecolor'}
        if target in mapping:
            self._pick_ann_color_attr(mapping[target])

    def _place_at_override(self):
        try: x,y = float(self.ann_x_override.text()), float(self.ann_y_override.text())
        except ValueError:
            QMessageBox.warning(self,'Invalid','Enter numeric X and Y.'); return
        if not self.canvas.axes_list: return
        self._sync_ann_style()
        self.canvas._place_text_annotation(self.canvas.axes_list[0], 0, x, y)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANNOTATION MODES & EDIT
    # ═══════════════════════════════════════════════════════════════════════════
    def set_annotation_mode(self, mode):
        self.canvas.annotation_mode = mode
        self.canvas._arrow_start    = None
        for btn, m in [(self.ann_none_btn, None),(self.ann_text_btn,'text'),
                       (self.ann_arrow_btn,'arrow'),(self.ann_image_btn,'image')]:
            btn.setChecked(mode == m)

    def _start_image_annotation(self):
        fp, _ = QFileDialog.getOpenFileName(
            self,'Select Image',_get_dir(),
            'Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;All (*)')
        if not fp:
            self.ann_image_btn.setChecked(False); return
        _remember_dir(fp)
        self.canvas._pending_image_path = fp
        self.canvas.ann_image_zoom      = self.ann_image_zoom.value()
        self.set_annotation_mode('image')

    def refresh_annotation_list(self):
        if not hasattr(self,'ann_list_widget'): return
        self.ann_list_widget.clear()
        # Filter to current subplot shown in annotations tab
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        for i, ann in enumerate(self.canvas.annotations):
            if filter_idx >= 0 and ann.get('axes_index', 0) != filter_idx:
                continue
            if ann['type']=='text':
                self.ann_list_widget.addItem(f"📝 \"{ann['label']}\"  @ ({ann['x']:.3g},{ann['y']:.3g})")
            elif ann['type']=='arrow':
                self.ann_list_widget.addItem(
                    f"➡  ({ann['x0']:.3g},{ann['y0']:.3g})→({ann['x1']:.3g},{ann['y1']:.3g})")
            elif ann['type']=='image':
                self.ann_list_widget.addItem(
                    f"🖼 {os.path.basename(ann['filepath'])}  zoom={ann.get('zoom',0.15):.2f}  @ ({ann['x']:.3g},{ann['y']:.3g})")

    def _selected_ann_index(self):
        """Return the index into canvas.annotations for the selected list item."""
        rows = self.ann_list_widget.selectedItems()
        if not rows: return -1
        list_row = self.ann_list_widget.row(rows[0])
        # Map list row back to canvas.annotations index (accounting for subplot filter)
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        count = 0
        for i, ann in enumerate(self.canvas.annotations):
            if filter_idx >= 0 and ann.get('axes_index', 0) != filter_idx:
                continue
            if count == list_row:
                return i
            count += 1
        return -1

    def _edit_selected_annotation(self):
        idx = self._selected_ann_index()
        if idx < 0:
            QMessageBox.information(self,'Edit','Select an annotation from the list first.'); return
        ann = self.canvas.annotations[idx]
        dlg = AnnotationEditDialog(ann, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.apply()
            # update_preview will clear figure, re-plot, then redraw_annotations
            self.update_preview()
            self.refresh_annotation_list()

    def _delete_selected_annotation(self):
        idx = self._selected_ann_index()
        if idx < 0:
            QMessageBox.information(self,'Delete','Select an annotation first.'); return
        self.canvas.remove_annotation_at(idx)

