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
from PyQt6.QtGui import QBrush, QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from data.digitize import AxisCalibration, Calibration, CalibrationError, PointCalibration, trace_by_color

CALIBRATION_KEYS = ('x1', 'x2', 'y1', 'y2')          # two points on each axis (a straight picture)
REFERENCE_KEYS = ('p1', 'p2', 'p3', 'p4')            # points with both values (a rotated or tilted picture)
CALIBRATION_COLORS = {'x1': '#d62728', 'x2': '#d62728', 'y1': '#1f77b4', 'y2': '#1f77b4',
                      'p1': '#9467bd', 'p2': '#9467bd', 'p3': '#9467bd', 'p4': '#9467bd'}
GRAB_RADIUS_PX = 10                                  # how near the pointer must be to take a marked point
MAGNIFIER_SIZE = 150
MAGNIFIER_SPAN = 25                                  # picture pixels shown across the magnifier
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
    dragged = pyqtSignal(float, float)               # the pointer, while a marked point is carried along
    drag_ended = pyqtSignal()
    left = pyqtSignal()

    def __init__(self, scene):
        super().__init__(scene)
        self.pan_tool = False
        self.grab_test = None            # callable(x, y) -> bool: is there a marked point to take at (x, y)?
        self._dragging = False
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
        if event.button() == Qt.MouseButton.LeftButton and self.grab_test is not None and not self.pan_tool:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self.grab_test(scene_pos.x(), scene_pos.y()):
                self._dragging = True
                event.accept()
                return
        if event.button() == Qt.MouseButton.MiddleButton or (self.pan_tool and event.button() == Qt.MouseButton.LeftButton):
            self._panning = True
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        self.moved.emit(scene_pos.x(), scene_pos.y())
        if self._dragging:
            self.dragged.emit(scene_pos.x(), scene_pos.y())
        if self._panning and self._last is not None:
            delta = event.position() - self._last
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
        self._last = event.position()
        event.accept()

    def leaveEvent(self, a0):
        self.left.emit()
        super().leaveEvent(a0)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.drag_ended.emit()
        elif self._panning:
            self._panning = False
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor if self.pan_tool else Qt.CursorShape.CrossCursor)
        elif self._press_pos is not None and (event.position() - self._press_pos).manhattanLength() < 5:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.clicked.emit(scene_pos.x(), scene_pos.y(), event.button())
        self._press_pos = None
        event.accept()


class Magnifier(QLabel):
    """A small enlarged view of the picture around the pointer, with a cross at the exact position,
    shown over a corner of the image so that a point can be placed to the pixel."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(MAGNIFIER_SIZE, MAGNIFIER_SIZE)
        self.setStyleSheet('border: 2px solid #222; background: #808080;')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def show_around(self, image: QImage, x: float, y: float, marks=()):
        """Show *image* around (x, y).  *marks*: positions (picture pixels) of marked points to draw in it."""
        span = MAGNIFIER_SPAN
        left, top = int(np.floor(x)) - span // 2, int(np.floor(y)) - span // 2
        patch = QImage(span, span, QImage.Format.Format_RGB32)
        patch.fill(QColor('#808080'))
        painter = QPainter(patch)
        painter.drawImage(-left, -top, image)
        painter.end()
        zoom = MAGNIFIER_SIZE / span
        pixmap = QPixmap.fromImage(patch.scaled(MAGNIFIER_SIZE, MAGNIFIER_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                Qt.TransformationMode.FastTransformation))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(POINT_COLOR), 2))
        for mx, my in marks:
            sx, sy = (mx - left) * zoom, (my - top) * zoom
            if 0 <= sx < MAGNIFIER_SIZE and 0 <= sy < MAGNIFIER_SIZE:
                painter.drawEllipse(QPointF(sx, sy), 5, 5)
        centre = QPointF((x - left) * zoom, (y - top) * zoom)
        painter.setPen(QPen(QColor('#ff00ff'), 1))
        painter.drawLine(QPointF(centre.x(), 0), QPointF(centre.x(), MAGNIFIER_SIZE))
        painter.drawLine(QPointF(0, centre.y()), QPointF(MAGNIFIER_SIZE, centre.y()))
        painter.end()
        self.setPixmap(pixmap)
        self.show()


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
        self._grabbed_point: int | None = None       # the marked point being dragged
        self._grabbed_marker: str | None = None      # or the reference marker being dragged
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
        self.view.grab_test = self._grab_at
        self.view.dragged.connect(self._on_drag)
        self.view.drag_ended.connect(self._on_drag_end)
        self.view.left.connect(lambda: self.magnifier.hide())
        self.magnifier = Magnifier(self.view)
        self.magnifier.move(8, 8)
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
        box = QGroupBox('2. Axes')
        outer = QVBoxLayout(box)
        self.cal_mode = QComboBox()
        self.cal_mode.addItems(['Straight picture: two values on each axis',
                                'Rotated or tilted: three or four points'])
        self.cal_mode.setToolTip('Use the second way when the axes are not horizontal and vertical in the picture '
                                 '(a scan that is turned, a photograph taken at an angle)')
        self.cal_mode.currentIndexChanged.connect(self._on_cal_mode)
        outer.addWidget(self.cal_mode)
        self.cal_buttons: dict[str, QPushButton] = {}
        self.cal_values: dict[str, QLineEdit] = {}
        self.axes_widget = QWidget()
        form = QFormLayout(self.axes_widget)
        form.setContentsMargins(0, 0, 0, 0)
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
        outer.addWidget(self.axes_widget)
        self.ref_widget = QWidget()
        ref_form = QFormLayout(self.ref_widget)
        ref_form.setContentsMargins(0, 0, 0, 0)
        for n in ('1', '2', '3', '4'):
            key = f'p{n}'
            button = QPushButton(f'Set point {n}' + ('' if n != '4' else ' (optional)'))
            button.setCheckable(True)
            button.setToolTip('Click here, then on the image at a place whose x and y you both know '
                              '(a crossing of two grid lines, the corner of the plot)')
            button.clicked.connect(lambda checked, k=key: self._await(k if checked else None))
            vx, vy = QLineEdit(), QLineEdit()
            for field, label in ((vx, 'x'), (vy, 'y')):
                field.setPlaceholderText(label)
                field.setFixedWidth(60)
                field.textChanged.connect(self._refresh)
            self.cal_buttons[key], self.cal_values[key + 'x'], self.cal_values[key + 'y'] = button, vx, vy
            row = QHBoxLayout()
            row.addWidget(button)
            row.addWidget(vx)
            row.addWidget(vy)
            ref_form.addRow(row)
        outer.addWidget(self.ref_widget)
        self.ref_widget.hide()
        for axis in ('x', 'y'):
            check = QCheckBox(f'{axis.upper()} axis is logarithmic')
            check.stateChanged.connect(self._refresh)
            setattr(self, f'log_{axis}', check)
            outer.addWidget(check)
        self.cal_status = QLabel('')
        self.cal_status.setWordWrap(True)
        outer.addWidget(self.cal_status)
        panel.addWidget(box)

        # 3. points
        box = QGroupBox('3. Points')
        lay = QVBoxLayout(box)
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(['Add points: click on the curve', 'Pan: drag the image'])
        self.tool_combo.currentIndexChanged.connect(self._on_tool)
        lay.addWidget(self.tool_combo)
        hint = QLabel('Right-click a point to remove it, drag it to move it. Wheel to zoom, middle button to drag the image.')
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
        self._grabbed_point = self._grabbed_marker = None
        self.magnifier.hide()
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
            self.magnifier.hide()
            return
        self._update_magnifier(x, y)
        if cal is not None:
            vx, vy = cal.to_data(x, y)
            self.readout.setText(f'x = {float(vx):.6g},  y = {float(vy):.6g}      (pixel {x:.0f}, {y:.0f})')
        else:
            self.readout.setText(f'pixel {x:.0f}, {y:.0f}')

    def _update_magnifier(self, x, y):
        """The enlarged view follows the pointer, in the corner that the pointer is not near."""
        if self.view.pan_tool or self._image is None:
            self.magnifier.hide()
            return
        self.magnifier.show_around(self._image, x, y, self._points)
        spot = self.view.mapFromScene(QPointF(x, y))
        margin = 8
        left = QRectF(margin, margin, MAGNIFIER_SIZE, MAGNIFIER_SIZE)
        near = left.adjusted(-30, -30, 30, 30).contains(QPointF(spot))
        self.magnifier.move(self.view.width() - MAGNIFIER_SIZE - margin - 18 if near else margin, margin)

    # ─── dragging marked points ───────────────────────────────────────────────
    def _grab_at(self, x, y) -> bool:
        """Called when the left button goes down: take the marked point (or reference marker) under
        the pointer, if any, so that it follows the pointer until the button is released."""
        if self._image is None or self._awaiting:
            return False
        zoom = self.view.transform().m11() or 1.0
        reach = GRAB_RADIUS_PX / zoom
        if self._points:
            pts = np.asarray(self._points)
            dist = np.hypot(pts[:, 0] - x, pts[:, 1] - y)
            i = int(np.argmin(dist))
            if dist[i] <= reach:
                self._grabbed_point = i
                return True
        for key in self._active_keys():
            if key in self._cal_points:
                cx, cy = self._cal_points[key]
                if np.hypot(cx - x, cy - y) <= reach:
                    self._grabbed_marker = key
                    return True
        return False

    def _on_drag(self, x, y):
        if self._image is None or (self._grabbed_point is None and self._grabbed_marker is None):
            return
        x = min(max(x, 0.0), self._image.width() - 1e-6)
        y = min(max(y, 0.0), self._image.height() - 1e-6)
        if self._grabbed_point is not None:
            self._points[self._grabbed_point] = (x, y)
            self._point_items[self._grabbed_point].setPos(QPointF(x, y))
        elif self._grabbed_marker is not None:
            self._cal_points[self._grabbed_marker] = (x, y)
            self._cal_items[self._grabbed_marker].setPos(QPointF(x, y))

    def _on_drag_end(self):
        self._grabbed_point = self._grabbed_marker = None
        self._refresh()

    def move_point(self, index: int, x: float, y: float):
        """Put marked point *index* at (x, y)."""
        self._grabbed_point = index
        self._on_drag(x, y)
        self._on_drag_end()

    def _on_click(self, x, y, button):
        if self._image is None:
            return
        if not (0 <= x < self._image.width() and 0 <= y < self._image.height()):
            return
        if self._awaiting in CALIBRATION_KEYS + REFERENCE_KEYS:
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
        item.setVisible(key in self._active_keys())
        self._cal_items[key] = item
        self._refresh()

    def calibration(self) -> Calibration | None:
        """The calibration, or None until both axes have their two points and values."""
        return self._calibration_or_reason()[0]

    def _calibration_or_reason(self):
        if self.cal_mode.currentIndex() == 1:
            return self._reference_calibration()
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

    def _reference_points(self):
        """(pixels, values, reason): the reference points that are complete (position and both values).
        Point 4 is used only when it is complete; a half-set one is reported."""
        pixels, values = [], []
        for n in ('1', '2', '3', '4'):
            key = f'p{n}'
            vx, vy = parse_number(self.cal_values[key + 'x'].text()), parse_number(self.cal_values[key + 'y'].text())
            placed = key in self._cal_points
            if placed and vx is not None and vy is not None:
                pixels.append(self._cal_points[key])
                values.append((vx, vy))
            elif n != '4' or placed or vx is not None or vy is not None:
                what = 'Set' if not placed else 'Type the x and y of'
                return pixels, values, f'{what} point {n}.'
        return pixels, values, ''

    def _reference_calibration(self):
        pixels, values, reason = self._reference_points()
        if reason:
            return None, reason
        try:
            return PointCalibration(pixels, values, log_x=self.log_x.isChecked(), log_y=self.log_y.isChecked()), ''
        except CalibrationError as e:
            return None, f'{e}.'

    def _on_cal_mode(self, index):
        self.axes_widget.setVisible(index == 0)
        self.ref_widget.setVisible(index == 1)
        self._await(None)
        used = REFERENCE_KEYS if index == 1 else CALIBRATION_KEYS
        for key, item in self._cal_items.items():
            item.setVisible(key in used)
        self._refresh()

    def _active_keys(self):
        return REFERENCE_KEYS if self.cal_mode.currentIndex() == 1 else CALIBRATION_KEYS

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
        keys = [k for k in self._active_keys() if k in self._cal_points]
        if self.cal_mode.currentIndex() == 0 and len(keys) == 4:
            xs = [self._cal_points['x1'][0], self._cal_points['x2'][0]]
            ys = [self._cal_points['y1'][1], self._cal_points['y2'][1]]
            region = (min(xs), min(ys), max(xs), max(ys))
        elif self.cal_mode.currentIndex() == 1 and len(keys) >= 3:
            pts = np.asarray([self._cal_points[k] for k in keys])
            region = (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))
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

