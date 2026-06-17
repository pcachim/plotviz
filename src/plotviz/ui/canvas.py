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

from core.geometry import point_segment_distance


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
        self._drag_part = 'both'   # arrows: 'tail' | 'tip' | 'both'

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
                if self._drag_part == 'tip':
                    # Move only the tip (re-aim the arrow); tail stays put.
                    ann['x1'], ann['y1'] = nx, ny
                elif self._drag_part == 'tail':
                    # Move only the tail; tip stays put.
                    ann['x0'], ann['y0'] = nx, ny
                else:
                    # Rigid translation of the whole arrow. nx/ny is the new
                    # tail position (grab offset removed).
                    dx = nx - ann['x0']
                    dy = ny - ann['y0']
                    ann['x0'] += dx
                    ann['y0'] += dy
                    ann['x1'] += dx
                    ann['y1'] += dy
                # Update the existing artist in place — set the text/tail anchor
                # (xytext) and the arrow tip (xy). Mutating rather than
                # recreating keeps the font/size untouched and avoids artist
                # accumulation during the drag.
                art = ann['artist']
                art.set_position((ann['x0'], ann['y0']))
                art.xy = (ann['x1'], ann['y1'])
            elif ann['type'] == 'image':
                ann['x'], ann['y'] = nx, ny
                try:
                    ann['artist'].xybox = (nx, ny)
                    ann['artist'].xy    = (nx, ny)
                except Exception:
                    pass
            self.draw_idle()

    # ── Tab-navigation constants ──────────────────────────────────────────────
    # Outer tabs: 0=Chart  1=Style  2=Plots  3=Advanced
    _OUTER_STYLE  = 1
    _OUTER_PLOTS  = 2
    # plots_inner_tabs add order: Data→Layout→Series→Axes→Annotations
    _INNER_DATA        = 0
    _INNER_LAYOUT      = 1
    _INNER_SERIES      = 2
    _INNER_AXES        = 3
    _INNER_ANNOTATIONS = 4

    def _goto_tab(self, outer: int, inner: int | None = None) -> None:
        """Navigate to *outer* tab and optionally to *inner* plots sub-tab."""
        mw = self.main_window
        if mw is None:
            return
        try:
            mw.tabs.setCurrentIndex(outer)
            if inner is not None and hasattr(mw, 'plots_inner_tabs'):
                mw.plots_inner_tabs.setCurrentIndex(inner)
        except Exception:
            pass

    def _select_subplot(self, ax_idx: int) -> None:
        """Switch every subplot selector to *ax_idx* and refresh tab state.

        No-op when there is only one subplot so single-chart users see no
        change in behaviour.
        """
        mw = self.main_window
        if mw is None:
            return
        n = getattr(mw, 'subplot_rows', 1) * getattr(mw, 'subplot_cols', 1)
        if n <= 1:
            return
        try:
            mw._on_global_sp_changed(ax_idx)
        except Exception:
            pass

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
            if self._try_grab_annotation(ax, ax_idx, x, y, event):
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
                # Annotation drag / select / double-click-to-edit
                if self._try_grab_annotation(ax, ax_idx, x, y, event):
                    return
                # Series hit → Series tab
                label = self._find_series_at(ax, x, y, event)
                if label and mw:
                    mw.select_series_by_label(label)
                    self._select_subplot(ax_idx)
                    self._goto_tab(self._OUTER_PLOTS, self._INNER_SERIES)
                    return
                # No artist hit — show coordinates and go to Layout tab
                sp_label = self._subplot_label(ax)
                self._show_status(
                    f'{sp_label}  ·  x = {self._fmt(x)},  y = {self._fmt(y)}'
                )
                self._select_subplot(ax_idx)
                self._goto_tab(self._OUTER_PLOTS, self._INNER_LAYOUT)

        elif zone == 'axes':
            # Axis decoration area — find which subplot and go to Axes tab
            px, py = event.x, event.y
            ax_idx = 0
            best_d = float('inf')
            for i, ax in enumerate(self.axes_list):
                b = ax.bbox
                cx = max(b.x0, min(px, b.x1))
                cy = max(b.y0, min(py, b.y1))
                d = (px - cx) ** 2 + (py - cy) ** 2
                if d < best_d:
                    best_d, ax_idx = d, i
            sp_label = self._subplot_label(self.axes_list[ax_idx])
            self._show_status(f'Axes — {sp_label}')
            self._select_subplot(ax_idx)
            self._goto_tab(self._OUTER_PLOTS, self._INNER_AXES)

        else:  # 'style' — figure margins / title area
            self._show_status('Figure — Style area')
            self._goto_tab(self._OUTER_STYLE)

    def on_release(self, event):
        if self._drag_ann is not None:
            self._drag_ann = None
            self._notify()

    def _axes_index(self, ax):
        try:
            return self.axes_list.index(ax)
        except ValueError:
            return 0

    def _arrow_grab_part(self, ax, x, y, ann, end_tol=0.06):
        """Decide which part of an arrow a click grabs.

        Returns 'tail' or 'tip' when the click is within *end_tol* of that
        endpoint, otherwise 'both' (translate the whole arrow).
        """
        xlim = ax.get_xlim(); ylim = ax.get_ylim()
        itx = 1.0 / max(abs(xlim[1] - xlim[0]) * end_tol, 1e-15)
        ity = 1.0 / max(abs(ylim[1] - ylim[0]) * end_tol, 1e-15)
        dt = ((x - ann['x0']) * itx) ** 2 + ((y - ann['y0']) * ity) ** 2
        dp = ((x - ann['x1']) * itx) ** 2 + ((y - ann['y1']) * ity) ** 2
        if dt < 1.0 or dp < 1.0:
            return 'tail' if dt <= dp else 'tip'
        return 'both'

    def _try_grab_annotation(self, ax, ax_idx, x, y, event):
        """Hit-test annotations at (x, y); on a hit, either open the edit form
        (double-click) or begin a drag, and mirror the selection into the list.

        Returns True if an annotation was hit (caller should stop), else False.
        """
        hit = self._find_annotation_at(ax, x, y)
        if hit is None:
            return False
        mw = self.main_window

        # Double-click → open the edit dialog for this annotation.
        if getattr(event, 'dblclick', False):
            self._drag_ann = None   # cancel any drag started by the first click
            self._select_subplot(ax_idx)
            self._goto_tab(self._OUTER_PLOTS, self._INNER_ANNOTATIONS)
            if mw is not None and hasattr(mw, 'select_annotation_in_list'):
                mw.select_annotation_in_list(hit)
            if mw is not None and hasattr(mw, 'edit_annotation'):
                mw.edit_annotation(hit)
            return True

        self._drag_ann = hit
        self._deactivate_toolbar()
        if hit['type'] == 'arrow':
            self._drag_part = self._arrow_grab_part(ax, x, y, hit)
            if self._drag_part == 'tip':
                self._drag_offx = x - hit['x1']
                self._drag_offy = y - hit['y1']
            else:  # 'tail' or 'both' anchor at the tail
                self._drag_offx = x - hit['x0']
                self._drag_offy = y - hit['y0']
            self._show_status({'tip': 'Arrow tip', 'tail': 'Arrow tail',
                               'both': 'Arrow annotation'}[self._drag_part])
        elif hit['type'] == 'text':
            self._drag_part = 'both'
            self._drag_offx = x - hit['x']
            self._drag_offy = y - hit['y']
            lbl = hit.get('label', '')
            self._show_status(f'Annotation: "{lbl}"' if lbl else 'Text annotation')
        elif hit['type'] == 'image':
            self._drag_part = 'both'
            self._drag_offx = x - hit['x']
            self._drag_offy = y - hit['y']
            self._show_status('Image annotation')

        self._select_subplot(ax_idx)
        self._goto_tab(self._OUTER_PLOTS, self._INNER_ANNOTATIONS)
        if mw is not None and hasattr(mw, 'select_annotation_in_list'):
            mw.select_annotation_in_list(hit)
        return True

    def _find_annotation_at(self, ax, x, y, tol_frac=0.05):
        """Find the closest annotation within tol_frac of axis range."""
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        tx = abs(xlim[1] - xlim[0]) * tol_frac
        ty = abs(ylim[1] - ylim[0]) * tol_frac
        itx, ity = 1.0 / max(tx, 1e-15), 1.0 / max(ty, 1e-15)
        best, best_d = None, float('inf')
        for ann in self.annotations:
            if ann['axes_index'] != self._axes_index(ax): continue
            if ann['type'] == 'arrow':
                # Grabbable anywhere along the shaft: distance (in tolerance-
                # normalised space) from the click to the tail→tip segment.
                d = point_segment_distance(
                    x * itx, y * ity,
                    ann['x0'] * itx, ann['y0'] * ity,
                    ann['x1'] * itx, ann['y1'] * ity) ** 2
            else:
                cx, cy = ann['x'], ann['y']
                dx = (x - cx) * itx
                dy = (y - cy) * ity
                d  = dx * dx + dy * dy
            if d < 1.0 and d < best_d:
                best, best_d = ann, d
        return best

    def _find_series_at(self, ax, x, y, event, px_threshold=20):
        """Return the label of the plotted series closest to the click, or None.

        Detects Line2D, PathCollection (scatter/bubble) and Rectangle (bar/barh).
        Artists whose label starts with '_' are matplotlib-internal and skipped.
        """
        import numpy as np
        from matplotlib.lines import Line2D
        from matplotlib.collections import PathCollection
        from matplotlib.patches import Rectangle

        best_label = None
        best_px    = float('inf')

        if event.x is None or event.y is None:
            return None

        ex = event.x
        ey = event.y

        for artist in ax.get_children():
            lbl = artist.get_label()
            lbl = lbl.get_text() if hasattr(lbl, 'get_text') else str(lbl) if lbl is not None else ''
            if not lbl or lbl.startswith('_'):
                continue

            # --- Line2D (line, step, stem, errorbar spine) ------------------
            if isinstance(artist, Line2D):
                try:
                    xd = np.asarray(artist.get_xdata(), dtype=float)
                    yd = np.asarray(artist.get_ydata(), dtype=float)
                    if len(xd) == 0:
                        continue
                    pts = ax.transData.transform(np.column_stack([xd, yd]))
                    px_dists = np.hypot(pts[:, 0] - ex, pts[:, 1] - ey)
                    min_d = float(np.nanmin(px_dists))
                    if min_d < px_threshold and min_d < best_px:
                        best_px, best_label = min_d, lbl
                except Exception:
                    pass

            # --- PathCollection (scatter / bubble) --------------------------
            elif isinstance(artist, PathCollection):
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

            # --- Rectangle (bar / barh) -------------------------------------
            elif isinstance(artist, Rectangle):
                try:
                    if artist.contains_point(ax.transData.transform((x, y))):
                        bx = artist.get_x() + artist.get_width() / 2
                        by = artist.get_y() + artist.get_height() / 2
                        pt = ax.transData.transform((bx, by))
                        d = float(np.hypot(pt[0] - ex, pt[1] - ey))
                        if d < best_px:
                            best_px, best_label = d, lbl
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
        self.draw_idle()
        self._notify()

    def _place_arrow_annotation(self, ax, ax_idx, x0, y0, x1, y1, label=None):
        # Prompt for an optional label (parity with text annotations); an empty
        # entry or Cancel still creates a plain arrow with no text.
        if label is None:
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self.main_window, 'Arrow label',
                                             'Label (optional):')
            label = text.strip() if ok else ''
        s = self.ann_style
        abp = None if s.get('bg_alpha', 0.0) == 0 else dict(
            boxstyle='round,pad=0.3',
            facecolor=s.get('bg_color', '#ffffcc'),
            edgecolor=s.get('edge_color', '#aaaaaa'),
            alpha=s.get('bg_alpha', 0.0))
        artist = ax.annotate(label, xy=(x1, y1), xytext=(x0, y0),
                             fontsize=s.get('fontsize', 10),
                             color=s.get('fontcolor', '#cc3300'),
                             fontfamily=s.get('fontfamily', 'sans-serif'),
                             bbox=abp,
                             arrowprops=dict(arrowstyle='->',
                                             color=s.get('fontcolor', '#cc3300'), lw=1.8),
                             zorder=50, annotation_clip=False)
        self.annotations.append({'type':'arrow','axes_index':ax_idx,
                                  'x0':x0,'y0':y0,'x1':x1,'y1':y1,
                                  'label':label,'style':dict(s),'artist':artist})
        self.draw_idle()
        self._notify()

    def _place_image_annotation(self, ax, ax_idx, x, y, filepath, zoom=0.15):
        try:
            img = mpimg.imread(filepath)
            ib = OffsetImage(img, zoom=zoom)
            ib.image.axes = ax
            ab = AnnotationBbox(ib, (x, y), frameon=True,
                                bboxprops=dict(edgecolor='#aaaaaa', linewidth=1.0),
                                zorder=50, annotation_clip=False)
            ax.add_artist(ab)
            self.annotations.append({'type':'image','axes_index':ax_idx,
                                      'x':x,'y':y,'filepath':filepath,
                                      'zoom':zoom,'artist':ab})
            self.draw_idle()
            self._notify()
        except Exception as e:
            print(f'Image annotation error: {e}')

    # ─── Annotation management ────────────────────────────────────────────────
    def remove_last_annotation(self):
        if self.annotations:
            try: self.annotations.pop()['artist'].remove()
            except Exception: pass
            self.draw_idle()
            self._notify()

    def remove_annotation_at(self, idx):
        if 0 <= idx < len(self.annotations):
            try: self.annotations[idx]['artist'].remove()
            except Exception: pass
            self.annotations.pop(idx)
            self.draw_idle()
            self._notify()

    def clear_annotations(self):
        for ann in self.annotations:
            try: ann['artist'].remove()
            except Exception: pass
        self.annotations.clear()
        self.draw_idle()
        self._notify()

    def _notify(self):
        if self.main_window:
            try: self.main_window.refresh_annotation_list()
            except Exception: pass

    # ─── Status bar helper ────────────────────────────────────────────────────
    def _show_status(self, msg: str, timeout: int = 4000) -> None:
        """Write *msg* to the main window's status bar (bottom of app)."""
        mw = self.main_window
        if mw is None:
            return
        try:
            mw.statusBar().showMessage(msg, timeout)
        except Exception:
            pass

    @staticmethod
    def _fmt(v) -> str:
        """Format a data-space coordinate concisely (4 significant figures)."""
        try:
            f = float(v)
            if f == 0:
                return '0'
            return f'{f:.4g}'
        except Exception:
            return str(v)

    def _subplot_label(self, ax) -> str:
        """Return a human-readable label for *ax*: its title if set, otherwise
        'Subplot N' (1-indexed), or just 'Subplot' for a single-panel chart."""
        idx = self._axes_index(ax)
        title = ''
        try:
            title = ax.get_title().strip()
        except Exception:
            pass
        if title:
            return title
        if len(self.axes_list) > 1:
            return f'Subplot {idx + 1}'
        return 'Subplot'

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
                abp = None if s.get('bg_alpha', 0.0) == 0 else dict(
                    boxstyle='round,pad=0.3',
                    facecolor=s.get('bg_color', '#ffffcc'),
                    edgecolor=s.get('edge_color', '#aaaaaa'),
                    alpha=s.get('bg_alpha', 0.0))
                artist = ax.annotate(ann['label'],
                                     xy=(ann['x1'], ann['y1']),
                                     xytext=(ann['x0'], ann['y0']),
                                     fontsize=s.get('fontsize', 10),
                                     color=s.get('fontcolor', '#cc3300'),
                                     fontfamily=s.get('fontfamily', 'sans-serif'),
                                     bbox=abp,
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

    def draw_annotations_on(self, axes_list):
        """Replay the current annotations onto an arbitrary list of axes.

        Used by the export path, which builds a fresh Figure and therefore
        needs the annotations re-created on its own axes.  Unlike
        redraw_annotations(), this does NOT touch the live artists stored in
        self.annotations — it only draws onto the supplied axes_list.
        """
        mw = getattr(self, 'main_window', None)
        for ann in self.annotations:
            ax_idx = ann['axes_index']
            if ax_idx >= len(axes_list):
                continue
            # Honour per-subplot visibility toggle
            if mw and not mw.subplot_ann_visible.get(ax_idx, True):
                continue
            ax = axes_list[ax_idx]
            s  = ann.get('style', self.ann_style)
            if ann['type'] == 'text':
                bp = None if s.get('bg_alpha', 0.9) == 0 else dict(
                    boxstyle='round,pad=0.3',
                    facecolor=s.get('bg_color', '#ffffcc'),
                    edgecolor=s.get('edge_color', '#aaaaaa'),
                    alpha=s.get('bg_alpha', 0.9))
                ax.annotate(ann['label'],
                            xy=(ann['x'], ann['y']),
                            xytext=(ann['x'], ann['y']),
                            fontsize=s.get('fontsize', 10),
                            color=s.get('fontcolor', '#000000'),
                            fontfamily=s.get('fontfamily', 'sans-serif'),
                            bbox=bp, zorder=50, annotation_clip=False)
            elif ann['type'] == 'arrow':
                abp = None if s.get('bg_alpha', 0.0) == 0 else dict(
                    boxstyle='round,pad=0.3',
                    facecolor=s.get('bg_color', '#ffffcc'),
                    edgecolor=s.get('edge_color', '#aaaaaa'),
                    alpha=s.get('bg_alpha', 0.0))
                ax.annotate(ann['label'],
                            xy=(ann['x1'], ann['y1']),
                            xytext=(ann['x0'], ann['y0']),
                            fontsize=s.get('fontsize', 10),
                            color=s.get('fontcolor', '#cc3300'),
                            fontfamily=s.get('fontfamily', 'sans-serif'),
                            bbox=abp,
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
                    print(f'Export image annotation error: {e}')
                    continue
