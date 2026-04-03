"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

ui/canvas.py – Matplotlib canvas
• Fixed-size Qt widget (never resized); border rect shows the export page
• Cursor placed above the axes in figure-space
• Text / arrow / image annotations with drag-to-move
• hide_cursor / show_cursor for clean export
"""
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    # matplotlib < 3.5 fallback
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches


class CanvasPlotter(FigureCanvas):
    def __init__(self, parent=None):
        # Fixed screen figure – we NEVER call set_size_inches on this one.
        # Export uses a separate Figure built at the right size.
        self.figure = Figure(figsize=(10, 7), dpi=100)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

        self.cursor_label    = None   # kept for hide_cursor used by export
        self.annotation_mode = None   # None | 'text' | 'arrow' | 'image'
        self.annotations     = []
        self._arrow_start    = None
        self._pending_image_path = None
        self.ann_image_zoom  = 0.15
        self.axes_list       = [self.axes]
        self.main_window     = None
        self._cursor_hidden  = False

        # Drag state
        self._drag_ann  = None
        self._drag_offx = 0.0
        self._drag_offy = 0.0

        # Border rect artist (page boundary indicator)
        self._border_rect = None

        self.ann_style = {
            'fontsize':   10,
            'fontcolor':  '#000000',
            'fontfamily': 'sans-serif',
            'bg_color':   '#ffffcc',
            'bg_alpha':   0.9,
            'edge_color': '#aaaaaa',
        }

        self.mpl_connect('motion_notify_event',  self.on_mouse_move)
        self.mpl_connect('button_press_event',   self.on_click)
        self.mpl_connect('button_release_event', self.on_release)

    # ─── Border rectangle ─────────────────────────────────────────────────────
    def draw_border_rect(self, left, bottom, width, height,
                         color='#999999', linewidth=1.2):
        """
        Draw a dashed rectangle in figure-fraction coordinates to indicate
        the export page boundary.  Called by main_window after subplots_adjust.
        left, bottom, width, height are all in [0..1] figure fractions.
        """
        if self._border_rect is not None:
            try:
                self._border_rect.remove()
            except Exception:
                pass
            self._border_rect = None

        rect = mpatches.Rectangle(
            (left, bottom), width, height,
            linewidth=linewidth,
            edgecolor=color,
            facecolor='none',
            linestyle='--',
            transform=self.figure.transFigure,
            clip_on=False,
            zorder=300,
        )
        self.figure.add_artist(rect)
        self._border_rect = rect

    def clear_border_rect(self):
        if self._border_rect is not None:
            try:
                self._border_rect.remove()
            except Exception:
                pass
            self._border_rect = None

    # ─── Cursor helpers ───────────────────────────────────────────────────────
    def _remove_cursor(self):
        if self.cursor_label is not None:
            try:
                self.cursor_label.remove()
            except Exception:
                pass
            self.cursor_label = None

    def hide_cursor(self):
        self._cursor_hidden = True
        self._remove_cursor()
        self.draw()

    def show_cursor(self):
        self._cursor_hidden = False

    # ─── Mouse events ─────────────────────────────────────────────────────────
    def on_mouse_move(self, event):
        if event.inaxes is None:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Drag annotation — button check removed; _drag_ann is only set on press
        if self._drag_ann is not None:
            ann = self._drag_ann
            nx, ny = x - self._drag_offx, y - self._drag_offy
            if ann['type'] == 'text':
                ann['x'], ann['y'] = nx, ny
                try:
                    ann['artist'].set_position((nx, ny))
                    ann['artist'].xy = (nx, ny)   # arrow tip (same position for pure text)
                except Exception:
                    pass
            elif ann['type'] == 'arrow':
                dx = nx - ann['x0']; dy = ny - ann['y0']
                ann['x0'] += dx; ann['y0'] += dy
                ann['x1'] += dx; ann['y1'] += dy
                try:
                    ann['artist'].set_position((ann['x0'], ann['y0']))
                    ann['artist'].xy = (ann['x1'], ann['y1'])
                except Exception:
                    pass
            elif ann['type'] == 'image':
                ann['x'], ann['y'] = nx, ny
                try:
                    ann['artist'].xybox = (nx, ny)
                    ann['artist'].xy    = (nx, ny)
                except Exception:
                    pass
            self.draw_idle()

    # ── Tab-navigation constants ──────────────────────────────────────────────
    _TAB_AXES   = 2   # Chart / Data / Axes / Style / Series / Annotations / Advanced
    _TAB_STYLE  = 3
    _TAB_SERIES = 4

    def _nav_zone(self, event):
        """Classify a left-click for tab navigation.

        Returns one of:
          'data'   – inside the inner spine box (ax.bbox); try series hit first
          'axes'   – axis decoration: tick/axis labels, below/beside inner box
          'style'  – title area, figure background, margins

        Rule:
          matplotlib sets event.inaxes iff the click is inside ax.bbox.
          Anything above ax.bbox.y1 (title, figure top) → 'style'.
          Everything below/beside ax.bbox that is inside get_tightbbox → 'axes'.
          Everything else → 'style'.
        """
        if event.inaxes is not None:
            return 'data'

        px, py = event.x, event.y
        if px is None or py is None:
            return 'style'

        try:
            renderer = self.figure.canvas.get_renderer()
        except Exception:
            renderer = None

        for ax in self.axes_list:
            inner = ax.bbox
            # Anything above the inner box top → title / figure top → Style
            if py > inner.y1:
                continue
            # Check tightbbox for the decoration band (below/beside inner box)
            try:
                tb = ax.get_tightbbox(renderer) if renderer else None
            except Exception:
                tb = None
            if tb is None:
                # Fallback: generous fixed expansion of inner box
                from matplotlib.transforms import Bbox as _Bbox
                b = inner
                tb = _Bbox([[b.x0 - 80, b.y0 - 80], [b.x1 + 80, b.y1 + 80]])
            M = 10  # small tolerance for rounding
            if (tb.x0 - M <= px <= tb.x1 + M and
                    tb.y0 - M <= py <= tb.y1 + M):
                return 'axes'

        return 'style'

    def on_click(self, event):
        if event.button != 1:
            return

        mw = self.main_window

        # ── Annotation placement modes ────────────────────────────────────────
        if self.annotation_mode is not None:
            if event.inaxes is None:
                return
            ax     = event.inaxes
            ax_idx = self._axes_index(ax)
            x, y   = event.xdata, event.ydata
            if x is None or y is None:
                return
            hit = self._find_annotation_at(ax, x, y)
            if hit is not None:
                self._drag_ann = hit
                self._deactivate_toolbar()
                if hit['type'] == 'text':
                    self._drag_offx = x - hit['x']
                    self._drag_offy = y - hit['y']
                elif hit['type'] == 'arrow':
                    self._drag_offx = x - hit['x0']
                    self._drag_offy = y - hit['y0']
                elif hit['type'] == 'image':
                    self._drag_offx = x - hit['x']
                    self._drag_offy = y - hit['y']
                return
            if self.annotation_mode == 'text':
                self._place_text_annotation(ax, ax_idx, x, y)
            elif self.annotation_mode == 'arrow':
                if self._arrow_start is None:
                    self._arrow_start = (x, y, ax_idx)
                else:
                    x0, y0, ax0 = self._arrow_start
                    self._arrow_start = None
                    if ax0 == ax_idx:
                        self._place_arrow_annotation(ax, ax_idx, x0, y0, x, y)
            elif self.annotation_mode == 'image':
                if self._pending_image_path:
                    self._place_image_annotation(ax, ax_idx, x, y,
                                                  self._pending_image_path,
                                                  zoom=self.ann_image_zoom)
            return

        # ── Default mode ──────────────────────────────────────────────────────
        zone = self._nav_zone(event)

        if zone == 'data':
            ax     = event.inaxes
            ax_idx = self._axes_index(ax)
            x, y   = event.xdata, event.ydata
            if x is not None and y is not None:
                # Annotation drag
                hit = self._find_annotation_at(ax, x, y)
                if hit is not None:
                    self._drag_ann = hit
                    self._deactivate_toolbar()
                    if hit['type'] == 'text':
                        self._drag_offx = x - hit['x']
                        self._drag_offy = y - hit['y']
                    elif hit['type'] == 'arrow':
                        self._drag_offx = x - hit['x0']
                        self._drag_offy = y - hit['y0']
                    elif hit['type'] == 'image':
                        self._drag_offx = x - hit['x']
                        self._drag_offy = y - hit['y']
                    return
                # Series hit
                label = self._find_series_at(ax, x, y, event)
                if label and mw:
                    mw.select_series_by_label(label)
                    return
            # No series hit — go to Axes tab for this subplot
            if mw:
                if hasattr(mw, 'sp_active'):
                    mw.sp_active.setCurrentIndex(ax_idx)
                mw.tabs.setCurrentIndex(self._TAB_AXES)

        elif zone == 'axes':
            # Axis decoration area — find which subplot and go to Axes tab
            px, py = event.x, event.y
            ax_idx = 0
            # Pick the subplot whose inner box is closest vertically/horizontally
            best_d = float('inf')
            for i, ax in enumerate(self.axes_list):
                b = ax.bbox
                cx = max(b.x0, min(px, b.x1))
                cy = max(b.y0, min(py, b.y1))
                d = (px - cx) ** 2 + (py - cy) ** 2
                if d < best_d:
                    best_d, ax_idx = d, i
            if mw:
                if hasattr(mw, 'sp_active'):
                    mw.sp_active.setCurrentIndex(ax_idx)
                mw.tabs.setCurrentIndex(self._TAB_AXES)

        else:  # 'style'
            if mw:
                mw.tabs.setCurrentIndex(self._TAB_STYLE)

    def on_release(self, event):
        if self._drag_ann is not None:
            self._drag_ann = None
            self._notify()

    def _axes_index(self, ax):
        try:
            return self.axes_list.index(ax)
        except ValueError:
            return 0

    def _find_annotation_at(self, ax, x, y, tol_frac=0.05):
        """Find the closest annotation within tol_frac of axis range."""
        xlim = ax.get_xlim(); ylim = ax.get_ylim()
        tx = abs(xlim[1] - xlim[0]) * tol_frac
        ty = abs(ylim[1] - ylim[0]) * tol_frac
        best, best_d = None, float('inf')
        for ann in self.annotations:
            if ann['axes_index'] != self._axes_index(ax): continue
            cx, cy = (ann['x'],  ann['y'])  if ann['type'] in ('text','image') \
                else (ann['x0'], ann['y0'])
            dx = (x - cx) / max(tx, 1e-15)
            dy = (y - cy) / max(ty, 1e-15)
            d  = dx*dx + dy*dy
            if d < 1.0 and d < best_d:
                best, best_d = ann, d
        return best

    def _find_series_at(self, ax, x, y, event, px_threshold=20):
        """Return the label of the plotted series closest to the click, or None.

        Strategy:
        1. For Line2D: convert all data points to display (pixel) coords and find
           the minimum pixel distance to the click.  Accept if within px_threshold.
           This avoids the unreliable artist.contains() path and works regardless
           of axis scale, zoom level, or whether the canvas has been drawn.
        2. For PathCollection (scatter): use artist.contains() which works reliably
           for filled markers, plus the same pixel-distance fallback.
        Artists with labels starting with '_' are matplotlib-internal and skipped.
        """
        import numpy as np
        from matplotlib.lines import Line2D
        from matplotlib.collections import PathCollection

        best_label = None
        best_px    = float('inf')

        if event.x is None or event.y is None:
            return None

        # event.x/y and ax.transData.transform() are both in figure DPI
        # display coordinates — no pixel-ratio conversion needed.
        ex = event.x
        ey = event.y

        for artist in ax.get_children():
            lbl = artist.get_label()
            lbl = lbl.get_text() if hasattr(lbl, 'get_text') else str(lbl) if lbl is not None else ''
            if not lbl or lbl.startswith('_'):
                continue

            # --- Line2D (line, step, errorbar spine) ------------------------
            if isinstance(artist, Line2D):
                try:
                    xd = np.asarray(artist.get_xdata(), dtype=float)
                    yd = np.asarray(artist.get_ydata(), dtype=float)
                    if len(xd) == 0:
                        continue
                    # Transform ALL data points to pixel coords in one call
                    pts = ax.transData.transform(np.column_stack([xd, yd]))
                    px_dists = np.hypot(pts[:, 0] - ex, pts[:, 1] - ey)
                    min_d = float(np.nanmin(px_dists))
                    if min_d < px_threshold and min_d < best_px:
                        best_px, best_label = min_d, lbl
                except Exception:
                    pass

            # --- PathCollection (scatter / bubble) --------------------------
            elif isinstance(artist, PathCollection):
                # contains() is reliable for scatter markers
                try:
                    hit, info = artist.contains(event)
                    if hit:
                        offsets = np.asarray(artist.get_offsets())
                        ind = info.get('ind', [0])
                        if len(offsets) and len(ind):
                            pt = ax.transData.transform(offsets[ind[0]])
                            d = float(np.hypot(pt[0] - ex, pt[1] - ey))
                            if d < best_px:
                                best_px, best_label = d, lbl
                except Exception:
                    pass
                # Pixel-distance fallback for sparse scatter
                try:
                    offsets = np.asarray(artist.get_offsets())
                    if len(offsets):
                        pts = ax.transData.transform(offsets)
                        px_dists = np.hypot(pts[:, 0] - ex, pts[:, 1] - ey)
                        min_d = float(np.nanmin(px_dists))
                        if min_d < px_threshold and min_d < best_px:
                            best_px, best_label = min_d, lbl
                except Exception:
                    pass

        return best_label

    def _deactivate_toolbar(self):
        """Deactivate any active zoom/pan tool so our drag can take over."""
        try:
            if self.main_window and hasattr(self.main_window, 'toolbar'):
                tb = self.main_window.toolbar
                if hasattr(tb, '_active') and tb._active:
                    tb._active = None
                # Toggle off zoom/pan if active
                if hasattr(tb, 'mode') and tb.mode:
                    tb.pan()  # calling pan() again toggles it off if active
        except Exception:
            pass

    # ─── Annotation placement ─────────────────────────────────────────────────
    def _place_text_annotation(self, ax, ax_idx, x, y, label=None, style=None):
        if label is None:
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self.main_window, 'Add Annotation', 'Text:')
            if not ok or not text.strip(): return
            label = text.strip()
        s = style if style is not None else self.ann_style
        bp = None if s.get('bg_alpha', 0.9) == 0 else dict(
            boxstyle='round,pad=0.3',
            facecolor=s.get('bg_color', '#ffffcc'),
            edgecolor=s.get('edge_color', '#aaaaaa'),
            alpha=s.get('bg_alpha', 0.9))
        artist = ax.annotate(label, xy=(x, y), xytext=(x, y),
                             fontsize=s.get('fontsize', 10),
                             color=s.get('fontcolor', '#000000'),
                             fontfamily=s.get('fontfamily', 'sans-serif'),
                             bbox=bp, zorder=50, annotation_clip=False)
        self.annotations.append({'type':'text','axes_index':ax_idx,
                                  'x':x,'y':y,'label':label,'style':dict(s),'artist':artist})
        self.draw_idle(); self._notify()

    def _place_arrow_annotation(self, ax, ax_idx, x0, y0, x1, y1, label=''):
        s = self.ann_style
        artist = ax.annotate(label, xy=(x1, y1), xytext=(x0, y0),
                             fontsize=s.get('fontsize', 10),
                             color=s.get('fontcolor', '#000000'),
                             arrowprops=dict(arrowstyle='->',
                                             color=s.get('fontcolor', '#cc3300'), lw=1.8),
                             zorder=50, annotation_clip=False)
        self.annotations.append({'type':'arrow','axes_index':ax_idx,
                                  'x0':x0,'y0':y0,'x1':x1,'y1':y1,
                                  'label':label,'style':dict(s),'artist':artist})
        self.draw_idle(); self._notify()

    def _place_image_annotation(self, ax, ax_idx, x, y, filepath, zoom=0.15):
        try:
            img = mpimg.imread(filepath)
            ib = OffsetImage(img, zoom=zoom); ib.image.axes = ax
            ab = AnnotationBbox(ib, (x, y), frameon=True,
                                bboxprops=dict(edgecolor='#aaaaaa', linewidth=1.0),
                                zorder=50, annotation_clip=False)
            ax.add_artist(ab)
            self.annotations.append({'type':'image','axes_index':ax_idx,
                                      'x':x,'y':y,'filepath':filepath,
                                      'zoom':zoom,'artist':ab})
            self.draw_idle(); self._notify()
        except Exception as e:
            print(f'Image annotation error: {e}')

    # ─── Annotation management ────────────────────────────────────────────────
    def remove_last_annotation(self):
        if self.annotations:
            try: self.annotations.pop()['artist'].remove()
            except Exception: pass
            self.draw_idle(); self._notify()

    def remove_annotation_at(self, idx):
        if 0 <= idx < len(self.annotations):
            try: self.annotations[idx]['artist'].remove()
            except Exception: pass
            self.annotations.pop(idx)
            self.draw_idle(); self._notify()

    def clear_annotations(self):
        for ann in self.annotations:
            try: ann['artist'].remove()
            except Exception: pass
        self.annotations.clear()
        self.draw_idle(); self._notify()

    def _notify(self):
        if self.main_window:
            try: self.main_window.refresh_annotation_list()
            except Exception: pass

    def redraw_annotations(self):
        surviving = []
        mw = getattr(self, 'main_window', None)
        for ann in self.annotations:
            ax_idx = ann['axes_index']
            if ax_idx >= len(self.axes_list): continue
            # Honour per-subplot visibility toggle
            if mw and not mw.subplot_ann_visible.get(ax_idx, True):
                surviving.append(ann)   # keep data, just don't draw
                continue
            ax = self.axes_list[ax_idx]
            s  = ann.get('style', self.ann_style)
            artist = None
            if ann['type'] == 'text':
                bp = None if s.get('bg_alpha', 0.9) == 0 else dict(
                    boxstyle='round,pad=0.3',
                    facecolor=s.get('bg_color', '#ffffcc'),
                    edgecolor=s.get('edge_color', '#aaaaaa'),
                    alpha=s.get('bg_alpha', 0.9))
                artist = ax.annotate(ann['label'],
                                     xy=(ann['x'], ann['y']),
                                     xytext=(ann['x'], ann['y']),
                                     fontsize=s.get('fontsize', 10),
                                     color=s.get('fontcolor', '#000000'),
                                     fontfamily=s.get('fontfamily', 'sans-serif'),
                                     bbox=bp, zorder=50, annotation_clip=False)
            elif ann['type'] == 'arrow':
                artist = ax.annotate(ann['label'],
                                     xy=(ann['x1'], ann['y1']),
                                     xytext=(ann['x0'], ann['y0']),
                                     fontsize=s.get('fontsize', 10),
                                     color=s.get('fontcolor', '#000000'),
                                     arrowprops=dict(arrowstyle='->',
                                                     color=s.get('fontcolor', '#cc3300'), lw=1.8),
                                     zorder=50, annotation_clip=False)
            elif ann['type'] == 'image':
                try:
                    img = mpimg.imread(ann['filepath'])
                    ib = OffsetImage(img, zoom=ann.get('zoom', 0.15))
                    ib.image.axes = ax
                    artist = AnnotationBbox(ib, (ann['x'], ann['y']),
                                            frameon=True,
                                            bboxprops=dict(edgecolor='#aaaaaa', linewidth=1.0),
                                            zorder=50, annotation_clip=False)
                    ax.add_artist(artist)
                except Exception as e:
                    print(f'Redraw image error: {e}')
                    continue
            if artist is not None:
                ann['artist'] = artist
                surviving.append(ann)
        self.annotations = surviving
