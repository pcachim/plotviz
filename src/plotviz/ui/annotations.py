"""
Copyright (c) 2026 Paulo Cachim
ui/annotations.py  –  plotviz

AnnotationUIMixin: the annotation toolbar modes (text / arrow / image), the
annotation list, and select/edit/delete actions. Split out of main_window;
mixed into PlotVizApp so it shares the canvas and annotation list via `self`.
"""
import os

from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from ui.helpers import _get_dir, _remember_dir
from ui.dialogs import AnnotationEditDialog


class AnnotationUIMixin:
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
            self.ann_image_btn.setChecked(False)
            return
        _remember_dir(fp)
        self.canvas._pending_image_path = fp
        self.canvas.ann_image_zoom      = self.ann_image_zoom.value()
        self.set_annotation_mode('image')

    def refresh_annotation_list(self):
        if not hasattr(self,'ann_list_widget'): return
        # Preserve the current selection across the rebuild (clear() drops it).
        # Track the selected annotation by identity so it survives a refresh
        # triggered by a drag/redraw.
        sel_idx = self._selected_ann_index()
        sel_ann = (self.canvas.annotations[sel_idx]
                   if 0 <= sel_idx < len(self.canvas.annotations)
                   else getattr(self, '_selected_ann_obj', None))
        self.ann_list_widget.clear()
        # Filter to current subplot shown in annotations tab
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        sel_row = -1
        row = 0
        for ann in self.canvas.annotations:
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
            if ann is sel_ann:
                sel_row = row
            row += 1
        if sel_row >= 0:
            self.ann_list_widget.setCurrentRow(sel_row)

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

    def select_annotation_in_list(self, ann):
        """Select, in the annotations list, the row matching *ann* (the object
        clicked on the canvas). Honours the current subplot filter."""
        if not hasattr(self, 'ann_list_widget'):
            return
        self._selected_ann_obj = ann   # remembered so refresh() can restore it
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        row = 0
        for a in self.canvas.annotations:
            if filter_idx >= 0 and a.get('axes_index', 0) != filter_idx:
                continue
            if a is ann:
                self.ann_list_widget.setCurrentRow(row)
                return
            row += 1

    def edit_annotation(self, ann):
        """Open the edit dialog for a specific annotation (e.g. from a canvas
        double-click)."""
        dlg = AnnotationEditDialog(ann, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.apply()
            self.update_preview()
            self.refresh_annotation_list()

    def _edit_selected_annotation(self):
        idx = self._selected_ann_index()
        if idx < 0:
            QMessageBox.information(self,'Edit','Select an annotation from the list first.')
            return
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
            QMessageBox.information(self,'Delete','Select an annotation first.')
            return
        self.canvas.remove_annotation_at(idx)
