"""
Copyright (c) 2026 Paulo Cachim
ui/digitizer.py  –  plotviz

Digitize Image: read the values of a chart that exists only as a picture.  Open the image,
tell the program where two known values are on each axis, click on the curve (or let it follow
a colour) and add the points to the chart as two columns.

The window keeps the points as pixel positions, so changing the calibration afterwards moves
every value.  The arithmetic is in data/digitize.py.
"""
from __future__ import annotations

import os

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QKeySequence, QPainterPath, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from data.digitize import AxisCalibration, Calibration, CalibrationError, trace_by_color

CALIBRATION_KEYS = ('x1', 'x2', 'y1', 'y2')
CALIBRATION_COLORS = {'x1': '#d62728', 'x2': '#d62728', 'y1': '#1f77b4', 'y2': '#1f77b4'}
POINT_COLOR = '#2ca02c'
IMAGE_FILTER = 'Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp);;All files (*)'


def parse_number(text: str) -> float | None:
    """A number typed by the user (a decimal comma is accepted), or None."""
    try:
        return float(text.strip().replace(',', '.'))
    except ValueError:
        return None


def image_to_rgb(image: QImage) -> np.ndarray:
    """The picture as an array (height, width, 3) of 0..255."""
    converted = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    buffer = converted.constBits()
    assert buffer is not None
    rows = np.frombuffer(buffer.asstring(stride * height), dtype=np.uint8).reshape(height, stride)
    return rows[:, :width * 3].reshape(height, width, 3).copy()


class ImageView(QGraphicsView):
    """The picture, with the wheel to zoom and the middle button (or the Pan tool) to move it.
    Reports clicks and the pointer in the pixel coordinates of the picture."""
    clicked = pyqtSignal(float, float, object)       # x, y, Qt.MouseButton
    moved = pyqtSignal(float, float)

    def __init__(self, scene):
        super().__init__(scene)
        self.pan_tool = False
        self._panning = False
        self._press_pos = None
        self._last = None
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor('#808080')))
        self.setMinimumSize(520, 420)

    def zoom_by(self, factor: float):
        scale = self.transform().m11() * factor
        if 0.05 <= scale <= 40:
            self.scale(factor, factor)

    def fit(self):
        self.resetTransform()
        if self.scene() is not None and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        self.zoom_by(1.25 if event.angleDelta().y() > 0 else 0.8)
        event.accept()

    def mousePressEvent(self, event):
        self._press_pos = event.position()
        self._last = event.position()
        if event.button() == Qt.MouseButton.MiddleButton or (self.pan_tool and event.button() == Qt.MouseButton.LeftButton):
            self._panning = True
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        self.moved.emit(scene_pos.x(), scene_pos.y())
        if self._panning and self._last is not None:
            delta = event.position() - self._last
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
        self._last = event.position()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor if self.pan_tool else Qt.CursorShape.CrossCursor)
        elif self._press_pos is not None and (event.position() - self._press_pos).manhattanLength() < 5:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.clicked.emit(scene_pos.x(), scene_pos.y(), event.button())
        self._press_pos = None
        event.accept()


def _cross(size: float = 9.0) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(-size, 0)
    path.lineTo(size, 0)
    path.moveTo(0, -size)
    path.lineTo(0, size)
    return path


class DigitizerDialog(QDialog):
    """The Digitize Image window.  Emits columns_ready({name: values}) when the points are added to the chart."""
    columns_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Digitize Image')
        self.resize(1180, 760)
        self._image: QImage | None = None
        self._rgb: np.ndarray | None = None
        self._path = ''
        self._cal_points: dict[str, tuple[float, float]] = {}
        self._cal_items: dict[str, QGraphicsPathItem] = {}
        self._points: list[tuple[float, float]] = []
        self._point_items: list[QGraphicsEllipseItem] = []
        self._awaiting: str | None = None            # a calibration key, or 'color', waiting for a click
        self._color: tuple[int, int, int] | None = None
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._build()
        QShortcut(QKeySequence(QKeySequence.StandardKey.Paste), self).activated.connect(self.paste_image)
        self._refresh()

    # ─── window ───────────────────────────────────────────────────────────────
    def _build(self):
        root = QHBoxLayout(self)
        self.scene = QGraphicsScene(self)
        self.view = ImageView(self.scene)
        self.view.clicked.connect(self._on_click)
        self.view.moved.connect(self._on_move)
        self.view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        left = QVBoxLayout()
        left.addWidget(self.view, 1)
        self.readout = QLabel('Open an image to start (or paste one with Ctrl+V).')
        self.readout.setStyleSheet('color:#555;')
        left.addWidget(self.readout)
        root.addLayout(left, 1)

        panel = QVBoxLayout()
        panel.setSpacing(8)
        root.addLayout(panel)

        # 1. image
        box = QGroupBox('1. Image')
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        self.open_btn = QPushButton('Open image…')
        self.open_btn.clicked.connect(self.open_image_dialog)
        self.paste_btn = QPushButton('Paste')
        self.paste_btn.setToolTip('Use the image on the clipboard (Ctrl+V)')
        self.paste_btn.clicked.connect(self.paste_image)
        fit_btn = QPushButton('Fit')
        fit_btn.setToolTip('Show the whole image')
        fit_btn.clicked.connect(self.view.fit)
        for b in (self.open_btn, self.paste_btn, fit_btn):
            row.addWidget(b)
        lay.addLayout(row)
        self.image_label = QLabel('no image')
        self.image_label.setStyleSheet('color:#555;')
        lay.addWidget(self.image_label)
        panel.addWidget(box)

        # 2. axes
        box = QGroupBox('2. Axes: two known values on each')
        form = QFormLayout(box)
        self.cal_buttons: dict[str, QPushButton] = {}
        self.cal_values: dict[str, QLineEdit] = {}
        for axis in ('x', 'y'):
            for n in ('1', '2'):
                key = f'{axis}{n}'
                button = QPushButton(f'Set {axis.upper()} point {n}')
                button.setCheckable(True)
                button.setToolTip(f'Click here, then on the image at a position of the {axis.upper()} axis whose value you know')
                button.clicked.connect(lambda checked, k=key: self._await(k if checked else None))
                value = QLineEdit()
                value.setPlaceholderText(f'value of {axis.upper()}')
                value.setFixedWidth(90)
                value.textChanged.connect(self._refresh)
                self.cal_buttons[key], self.cal_values[key] = button, value
                row = QHBoxLayout()
                row.addWidget(button)
                row.addWidget(value)
                form.addRow(row)
            check = QCheckBox(f'{axis.upper()} axis is logarithmic')
            check.stateChanged.connect(self._refresh)
            setattr(self, f'log_{axis}', check)
            form.addRow(check)
        self.cal_status = QLabel('')
        self.cal_status.setWordWrap(True)
        form.addRow(self.cal_status)
        panel.addWidget(box)

        # 3. points
        box = QGroupBox('3. Points')
        lay = QVBoxLayout(box)
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(['Add points: click on the curve', 'Pan: drag the image'])
        self.tool_combo.currentIndexChanged.connect(self._on_tool)
        lay.addWidget(self.tool_combo)
        hint = QLabel('Right-click a point to remove it. Wheel to zoom, middle button to drag.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#555;')
        lay.addWidget(hint)
        trace = QHBoxLayout()
        self.color_btn = QPushButton('Curve colour…')
        self.color_btn.setCheckable(True)
        self.color_btn.setToolTip('Click here, then on the curve, to pick its colour')
        self.color_btn.clicked.connect(lambda checked: self._await('color' if checked else None))
        self.tolerance = QSpinBox()
        self.tolerance.setRange(1, 300)
        self.tolerance.setValue(60)
        self.tolerance.setPrefix('± ')
        self.tolerance.setToolTip('How different from the picked colour a pixel may be')
        self.step = QSpinBox()
        self.step.setRange(1, 100)
        self.step.setValue(8)
        self.step.setPrefix('every ')
        self.step.setSuffix(' px')
        self.step.setToolTip('One point per this many pixel columns')
        self.trace_btn = QPushButton('Trace')
        self.trace_btn.setToolTip('Add points along the picked colour, between the reference points of the X axis')
        self.trace_btn.clicked.connect(self.trace_curve)
        for w in (self.color_btn, self.tolerance, self.step, self.trace_btn):
            trace.addWidget(w)
        lay.addLayout(trace)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['x', 'y'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(180)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.remove_btn = QPushButton('Remove selected')
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn = QPushButton('Clear all')
        self.clear_btn.clicked.connect(self.clear_points)
        row.addWidget(self.remove_btn)
        row.addWidget(self.clear_btn)
        lay.addLayout(row)
        panel.addWidget(box, 1)

        # 4. dataset
        box = QGroupBox('4. Add to the chart')
        form = QFormLayout(box)
        self.name_x = QLineEdit('x_digitized')
        self.name_y = QLineEdit('y_digitized')
        form.addRow('Column for x:', self.name_x)
        form.addRow('Column for y:', self.name_y)
        self.sort_check = QCheckBox('Sort by x')
        self.sort_check.setChecked(True)
        form.addRow(self.sort_check)
        self.add_btn = QPushButton('Add as columns')
        self.add_btn.clicked.connect(self.add_to_chart)
        form.addRow(self.add_btn)
        panel.addWidget(box)
        box_width = 380
        for i in range(panel.count()):
            w = panel.itemAt(i).widget()
            if w is not None:
                w.setFixedWidth(box_width)

    # ─── image ────────────────────────────────────────────────────────────────
    def open_image_dialog(self):
        import config.settings as settings
        path, _ = QFileDialog.getOpenFileName(self, 'Open image', settings.get_last_dir(), IMAGE_FILTER)
        if path:
            self.open_image(path)

    def open_image(self, path: str) -> bool:
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, 'Open image', f'The file could not be read as an image:\n{path}')
            return False
        self.set_image(image, os.path.basename(path))
        self._path = path
        return True

    def paste_image(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            self.readout.setText('There is no image on the clipboard.')
            return False
        self.set_image(image, 'pasted image')
        return True

    def set_image(self, image: QImage, name: str = ''):
        """Show *image* and start over (a new picture has other axes and other points)."""
        self.clear_points(refresh=False)
        for key in list(self._cal_items):
            self.scene.removeItem(self._cal_items.pop(key))
        self._cal_points.clear()
        self.scene.clear()
        self._cal_items.clear()
        self._point_items.clear()
        self._image = image
        self._rgb = image_to_rgb(image)
        self._color = None
        self._pixmap_item = self.scene.addPixmap(QPixmap.fromImage(image))
        self.scene.setSceneRect(QRectF(0, 0, image.width(), image.height()))
        self.view.fit()
        self.image_label.setText(f'{name}  ({image.width()} × {image.height()} px)')
        self.readout.setText('Set two points on each axis (step 2), then click on the curve.')
        self._refresh()

    # ─── interaction ──────────────────────────────────────────────────────────
    def _on_tool(self, index):
        self.view.pan_tool = index == 1
        self.view.viewport().setCursor(Qt.CursorShape.OpenHandCursor if index == 1 else Qt.CursorShape.CrossCursor)

    def _await(self, what: str | None):
        """The next click on the image sets calibration point *what* (or the curve colour)."""
        self._awaiting = what
        for key, button in self.cal_buttons.items():
            button.setChecked(key == what)
        self.color_btn.setChecked(what == 'color')
        if what:
            self.readout.setText('Click on the image…')

    def _on_move(self, x, y):
        if self._image is None:
            return
        cal = self.calibration()
        inside = 0 <= x < self._image.width() and 0 <= y < self._image.height()
        if not inside:
            return
        if cal is not None:
            vx, vy = cal.to_data(x, y)
            self.readout.setText(f'x = {float(vx):.6g},  y = {float(vy):.6g}      (pixel {x:.0f}, {y:.0f})')
        else:
            self.readout.setText(f'pixel {x:.0f}, {y:.0f}')

    def _on_click(self, x, y, button):
        if self._image is None:
            return
        if not (0 <= x < self._image.width() and 0 <= y < self._image.height()):
            return
        if self._awaiting in CALIBRATION_KEYS:
            self.set_calibration_point(self._awaiting, x, y)
            self._await(None)
            return
        if self._awaiting == 'color':
            self.pick_color_at(x, y)
            self._await(None)
            return
        if button == Qt.MouseButton.RightButton:
            self.remove_nearest(x, y)
        elif button == Qt.MouseButton.LeftButton and not self.view.pan_tool:
            self.add_point(x, y)

    # ─── calibration ──────────────────────────────────────────────────────────
    def set_calibration_point(self, key: str, x: float, y: float):
        """Mark where reference point *key* ('x1', 'x2', 'y1', 'y2') is on the picture."""
        self._cal_points[key] = (x, y)
        item = self._cal_items.pop(key, None)
        if item is not None:
            self.scene.removeItem(item)
        item = self.scene.addPath(_cross(), QPen(QColor(CALIBRATION_COLORS[key]), 2))
        assert item is not None
        item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations)
        item.setPos(QPointF(x, y))
        item.setToolTip(key.upper())
        item.setZValue(10)
        self._cal_items[key] = item
        self._refresh()

    def calibration(self) -> Calibration | None:
        """The calibration, or None until both axes have their two points and values."""
        return self._calibration_or_reason()[0]

    def _calibration_or_reason(self) -> tuple[Calibration | None, str]:
        axes = {}
        for axis, index in (('x', 0), ('y', 1)):
            ps, vs = [], []
            for n in ('1', '2'):
                key = f'{axis}{n}'
                if key not in self._cal_points:
                    return None, f'Set the {axis.upper()} point {n}.'
                value = parse_number(self.cal_values[key].text())
                if value is None:
                    return None, f'Type the value of the {axis.upper()} point {n}.'
                ps.append(self._cal_points[key][index])
                vs.append(value)
            try:
                axes[axis] = AxisCalibration(ps[0], vs[0], ps[1], vs[1],
                                             log=getattr(self, f'log_{axis}').isChecked())
            except CalibrationError as e:
                return None, f'{axis.upper()} axis: {e}.'
        return Calibration(axes['x'], axes['y']), ''

    # ─── points ───────────────────────────────────────────────────────────────
    def add_point(self, x: float, y: float):
        self._points.append((x, y))
        item = self.scene.addEllipse(-4, -4, 8, 8, QPen(QColor('white'), 1), QBrush(QColor(POINT_COLOR)))
        assert item is not None
        item.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)
        item.setPos(QPointF(x, y))
        item.setZValue(20)
        self._point_items.append(item)
        self._refresh()

    def remove_point(self, index: int):
        if 0 <= index < len(self._points):
            del self._points[index]
            self.scene.removeItem(self._point_items.pop(index))
            self._refresh()

    def remove_nearest(self, x: float, y: float, radius_px: float = 12.0):
        """Remove the point nearest to (x, y) if it is within *radius_px* screen pixels."""
        if not self._points:
            return
        zoom = self.view.transform().m11() or 1.0
        pts = np.asarray(self._points)
        dist = np.hypot(pts[:, 0] - x, pts[:, 1] - y) * zoom
        i = int(np.argmin(dist))
        if dist[i] <= radius_px:
            self.remove_point(i)

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        order = self._table_order()
        for r in rows:
            if r < len(order):
                self.remove_point(order[r])

    def clear_points(self, refresh: bool = True):
        for item in self._point_items:
            self.scene.removeItem(item)
        self._point_items.clear()
        self._points.clear()
        if refresh:
            self._refresh()

    def pick_color_at(self, x: float, y: float):
        if self._rgb is None:
            return
        r, g, b = (int(v) for v in self._rgb[min(int(y), self._rgb.shape[0] - 1), min(int(x), self._rgb.shape[1] - 1)])
        self._color = (r, g, b)
        self.color_btn.setStyleSheet(f'background-color: rgb({r},{g},{b}); color: {"white" if r + g + b < 380 else "black"};')
        self._refresh()

    def trace_curve(self) -> int:
        """Add points along the picked colour, within the horizontal range of the X reference points
        and the vertical range of the Y reference points.  Returns the number of points added."""
        if self._rgb is None or self._color is None:
            self.readout.setText('Pick the colour of the curve first (Curve colour…, then click on it).')
            return 0
        region = None
        if all(k in self._cal_points for k in CALIBRATION_KEYS):
            xs = [self._cal_points['x1'][0], self._cal_points['x2'][0]]
            ys = [self._cal_points['y1'][1], self._cal_points['y2'][1]]
            region = (min(xs), min(ys), max(xs), max(ys))
        px, py = trace_by_color(self._rgb, self._color, self.tolerance.value(), self.step.value(), region)
        for x, y in zip(px, py):
            self.add_point(float(x), float(y))
        self.readout.setText(f'{len(px)} point(s) added along the curve.' if len(px) else
                             'No pixel of that colour was found: raise the tolerance or pick the colour again.')
        return len(px)

    def points_data(self) -> tuple[np.ndarray, np.ndarray]:
        """The points as values of the axes (sorted by x when the option is on).  Empty until calibrated."""
        cal = self.calibration()
        if cal is None or not self._points:
            return np.array([]), np.array([])
        pts = np.asarray(self._points)
        x, y = cal.to_data(pts[:, 0], pts[:, 1])
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        if self.sort_check.isChecked():
            order = np.argsort(x, kind='stable')
            x, y = x[order], y[order]
        return x, y

    def _table_order(self) -> list[int]:
        """The index of each table row in self._points (the table follows the sort option)."""
        if not self._points:
            return []
        cal = self.calibration()
        if cal is None or not self.sort_check.isChecked():
            return list(range(len(self._points)))
        x = np.asarray(cal.to_data(np.asarray(self._points)[:, 0], 0.0)[0], dtype=float)
        return [int(i) for i in np.argsort(x, kind='stable')]

    def add_to_chart(self):
        x, y = self.points_data()
        if not len(x):
            reason = self._calibration_or_reason()[1] or 'Click on the curve to add points first.'
            QMessageBox.information(self, 'Add as columns', reason)
            return
        nx, ny = self.name_x.text().strip() or 'x_digitized', self.name_y.text().strip() or 'y_digitized'
        if nx == ny:
            QMessageBox.warning(self, 'Add as columns', 'The two columns need different names.')
            return
        self.columns_ready.emit({nx: x, ny: y})
        self.readout.setText(f'Added {len(x)} point(s) as "{nx}" and "{ny}".')

    # ─── display ──────────────────────────────────────────────────────────────
    def _refresh(self, *_):
        cal, reason = self._calibration_or_reason()
        if self._image is None:
            self.cal_status.setText('')
        elif cal is None:
            self.cal_status.setText(f'<span style="color:#b00">{reason}</span>')
        else:
            self.cal_status.setText('<span style="color:#080">Axes calibrated.</span>')
        have = self._image is not None
        for w in (self.trace_btn, self.color_btn, self.add_btn, self.remove_btn, self.clear_btn):
            w.setEnabled(have)
        for button in self.cal_buttons.values():
            button.setEnabled(have)
        self._fill_table(cal)

    def _fill_table(self, cal):
        order = self._table_order()
        self.table.setRowCount(len(order))
        if not order:
            return
        pts = np.asarray(self._points)
        if cal is not None:
            vx, vy = cal.to_data(pts[:, 0], pts[:, 1])
        else:
            vx = vy = None
        for row, i in enumerate(order):
            if vx is not None and vy is not None:
                texts = (f'{float(vx[i]):.6g}', f'{float(vy[i]):.6g}')
            else:
                texts = ('—', '—')
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

    def keyPressEvent(self, a0):
        if a0 is not None and a0.key() == Qt.Key.Key_Escape and self._awaiting:
            self._await(None)
            return
        super().keyPressEvent(a0)

