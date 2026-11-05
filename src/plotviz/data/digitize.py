"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.

data/digitize.py  –  plotviz
The arithmetic of reading values off a picture of a chart: the calibration of the axes
(two known positions on each axis give the value at any pixel, on a linear or a logarithmic
scale) and the tracing of a curve by its colour.  No Qt here: pixels are plain numbers.

Pixel coordinates are those of the image: x to the right, y down, the centre of the first
pixel at (0.5, 0.5).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class CalibrationError(ValueError):
    """The two reference points of an axis cannot define a scale."""


@dataclass(frozen=True)
class AxisCalibration:
    """One axis: the pixel position and the value of two points on it."""
    p1: float
    v1: float
    p2: float
    v2: float
    log: bool = False

    def __post_init__(self):
        if self.p1 == self.p2:
            raise CalibrationError('the two reference points are at the same position')
        if self.v1 == self.v2:
            raise CalibrationError('the two reference values are equal')
        if self.log and (self.v1 <= 0 or self.v2 <= 0):
            raise CalibrationError('a logarithmic axis needs positive reference values')

    def _scale(self):
        v1, v2 = (np.log10(self.v1), np.log10(self.v2)) if self.log else (self.v1, self.v2)
        return v1, (v2 - v1) / (self.p2 - self.p1)

    def value(self, pixel):
        """The value at *pixel* (a number or an array)."""
        v1, slope = self._scale()
        out = v1 + (np.asarray(pixel, dtype=float) - self.p1) * slope
        return 10.0 ** out if self.log else out

    def pixel(self, value):
        """The pixel position of *value* (the inverse of value())."""
        v1, slope = self._scale()
        v = np.asarray(value, dtype=float)
        return self.p1 + ((np.log10(v) if self.log else v) - v1) / slope


@dataclass(frozen=True)
class Calibration:
    """Both axes.  The x axis is read from the horizontal pixel position, the y axis from the vertical one."""
    x: AxisCalibration
    y: AxisCalibration

    def to_data(self, px, py):
        return self.x.value(px), self.y.value(py)

    def to_pixel(self, x, y):
        return self.x.pixel(x), self.y.pixel(y)


def pick_color_mask(rgb: np.ndarray, color: tuple[int, int, int], tolerance: float) -> np.ndarray:
    """Boolean mask of the pixels whose colour is within *tolerance* of *color*
    (Euclidean distance in RGB, 0..441)."""
    diff = rgb[..., :3].astype(float) - np.asarray(color, dtype=float)
    return np.sqrt((diff ** 2).sum(axis=-1)) <= tolerance


def trace_by_color(rgb: np.ndarray, color: tuple[int, int, int], tolerance: float = 40.0, step: int = 4,
                   region: tuple[float, float, float, float] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Follow a curve of one colour: for every *step*-th pixel column that has pixels of that
    colour, one point at the middle of them.  *region* = (left, top, right, bottom) in pixels
    limits the search (the plot area, so that a legend or a title of the same colour is ignored).
    Returns (px, py) in pixel coordinates."""
    height, width = rgb.shape[:2]
    mask = pick_color_mask(rgb, color, tolerance)
    left, top, right, bottom = region if region else (0, 0, width, height)
    left, right = max(0, int(np.floor(left))), min(width, int(np.ceil(right)))
    top, bottom = max(0, int(np.floor(top))), min(height, int(np.ceil(bottom)))
    xs, ys = [], []
    rows = np.arange(top, bottom)
    for column in range(left, right, max(1, int(step))):
        hits = mask[top:bottom, column]
        if hits.any():
            xs.append(column + 0.5)
            ys.append(rows[hits].mean() + 0.5)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


class PointCalibration:
    """Calibration from three or four reference points whose pixel position and (x, y) values are
    known, for a picture whose axes are rotated or seen in perspective.  Three points give an
    affine map (rotation, skew, different scales); four give a projective one (a chart photographed
    at an angle).  Same interface as Calibration: to_data() and to_pixel()."""

    def __init__(self, pixels, values, log_x: bool = False, log_y: bool = False):
        pix = np.asarray(pixels, dtype=float).reshape(-1, 2)
        val = np.asarray(values, dtype=float).reshape(-1, 2).copy()
        if len(pix) not in (3, 4) or len(pix) != len(val):
            raise CalibrationError('three or four reference points are needed')
        for col, is_log, name in ((0, log_x, 'x'), (1, log_y, 'y')):
            if is_log:
                if (val[:, col] <= 0).any():
                    raise CalibrationError(f'a logarithmic {name} axis needs positive reference values')
                val[:, col] = np.log10(val[:, col])
        self.log_x, self.log_y = log_x, log_y
        self._forward = self._solve(pix, val)
        try:
            self._backward = np.linalg.inv(self._forward)
        except np.linalg.LinAlgError as e:
            raise CalibrationError('the reference points do not define a scale (are they on one line?)') from e
        self.pixels, self.values = pix, val

    @staticmethod
    def _solve(pix: np.ndarray, val: np.ndarray) -> np.ndarray:
        n = len(pix)
        if n == 3:                                              # affine: 6 unknowns, 6 equations
            design = np.column_stack([pix, np.ones(3)])
            if abs(np.linalg.det(design)) < 1e-9 * max(1.0, float(np.ptp(pix)) ** 2):
                raise CalibrationError('the reference points are on one line')
            coef = np.linalg.solve(design, val)                  # 3x2
            return np.vstack([coef.T, [0.0, 0.0, 1.0]])
        rows, rhs = [], []                                       # projective: 8 unknowns, h33 = 1
        for (px, py), (vx, vy) in zip(pix, val):
            rows.append([px, py, 1, 0, 0, 0, -vx * px, -vx * py])
            rows.append([0, 0, 0, px, py, 1, -vy * px, -vy * py])
            rhs += [vx, vy]
        system = np.asarray(rows)
        if np.linalg.cond(system) > 1e12:
            raise CalibrationError('the reference points do not define a scale (three on one line?)')
        h = np.linalg.solve(system, np.asarray(rhs))
        return np.append(h, 1.0).reshape(3, 3)

    @staticmethod
    def _apply(matrix: np.ndarray, a, b):
        a, b = np.broadcast_arrays(np.asarray(a, dtype=float), np.asarray(b, dtype=float))
        out = np.einsum('ij,j...->i...', matrix, np.stack([a, b, np.ones_like(a)]))
        return out[0] / out[2], out[1] / out[2]

    def to_data(self, px, py):
        x, y = self._apply(self._forward, px, py)
        return (10.0 ** x if self.log_x else x), (10.0 ** y if self.log_y else y)

    def to_pixel(self, x, y):
        vx = np.log10(x) if self.log_x else np.asarray(x, dtype=float)
        vy = np.log10(y) if self.log_y else np.asarray(y, dtype=float)
        return self._apply(self._backward, vx, vy)
