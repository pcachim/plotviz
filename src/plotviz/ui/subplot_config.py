"""
Copyright (c) 2026 Paulo Cachim
ui/subplot_config.py  –  plotviz
SubplotConfigMixin: _open_subplot_config_dialog() — mosaic/preset layout dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QDialogButtonBox, QComboBox, QWidget, QGridLayout, QMessageBox,
    QRadioButton, QButtonGroup, QGroupBox, QFrame,
)
from PyQt6.QtCore import Qt


class SubplotConfigMixin:
    def _open_subplot_config_dialog(self):
        """Open a visual subplot layout picker with a custom mosaic editor."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                     QLabel, QDialogButtonBox, QPushButton, QWidget,
                                     QCheckBox, QTabWidget, QSpinBox, QSizePolicy,
                                     QScrollArea, QFrame)

        # (label, rows, cols, mosaic_or_None)
        LAYOUTS = [
            ('Single',       1, 1, None),
            ('1 × 2',        1, 2, None),
            ('1 × 3',        1, 3, None),
            ('2 × 1',        2, 1, None),
            ('2 × 2',        2, 2, None),
            ('2 × 3',        2, 3, None),
            ('3 × 1',        3, 1, None),
            ('3 × 2',        3, 2, None),
            ('3 × 3',        3, 3, None),
            ('1 top\n2 down',   2, 2, [['A','A'],['B','C']]),
            ('2 top\n1 down',   2, 2, [['A','B'],['C','C']]),
            ('1 left\n2 right', 2, 2, [['A','B'],['A','C']]),
            ('2 left\n1 right', 2, 2, [['A','C'],['B','C']]),
            ('1 top\n3 down',   2, 3, [['A','A','A'],['B','C','D']]),
            ('3 top\n1 down',   2, 3, [['A','B','C'],['D','D','D']]),
            ('2×2 mosaic\n1+1+2', 2, 2, [['A','B'],['C','C']]),
            ('3 rows\n1 wide top', 3, 2, [['A','A'],['B','C'],['D','E']]),
            ('3 rows\n1 wide bot', 3, 2, [['A','B'],['C','D'],['E','E']]),
        ]

        # ── Colour palette for custom editor cells ────────────────────────────
        CELL_COLOURS = ['#c8d8f0','#f0c8d8','#d8f0c8','#f0eac8',
                        '#e8c8f0','#c8f0ee','#f5d7b5','#d8d8d8']

        dlg = QDialog(self)
        dlg.setWindowTitle('Subplot Layout')
        dlg.setMinimumWidth(620)
        dlg.setMinimumHeight(520)
        dlg_lay = QVBoxLayout(dlg)

        inner_tabs = QTabWidget()
        dlg_lay.addWidget(inner_tabs)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1 — Presets gallery
        # ══════════════════════════════════════════════════════════════════════
        presets_w = QWidget()
        presets_lay = QVBoxLayout(presets_w)

        def _make_preview(rows, cols, mosaic, size=(88,60)):
            w = QWidget()
            w.setFixedSize(*size)
            g = QGridLayout(w)
            g.setSpacing(2)
            g.setContentsMargins(3,3,3,3)
            style = 'background:#cce;border:1px solid #77a;font-size:8px;border-radius:2px;'
            if mosaic is None:
                for r in range(rows):
                    for c in range(cols):
                        lbl = QLabel(str(r*cols+c+1))
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setStyleSheet(style)
                        g.addWidget(lbl, r, c)
            else:
                seen = {}
                for ri, row in enumerate(mosaic):
                    for ci, cell in enumerate(row):
                        if cell not in seen: seen[cell] = [ri, ci, ri, ci]
                        else:
                            seen[cell][2] = max(seen[cell][2], ri)
                            seen[cell][3] = max(seen[cell][3], ci)
                for idx_c, (cell, (r0,c0,r1,c1)) in enumerate(seen.items()):
                    lbl = QLabel(str(idx_c+1))
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet(style)
                    g.addWidget(lbl, r0, c0, r1-r0+1, c1-c0+1)
            return w

        selected_preset = [0]
        card_group = []   # list of (preview_btn, label_btn) pairs

        per_row = 5
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)

        SELECTED_BORDER = '2px solid #3378ff'
        NORMAL_BORDER   = '1px solid #aaa'
        SELECTED_BG     = '#e8f0ff'
        NORMAL_BG       = 'transparent'

        def _select_preset(i):
            selected_preset[0] = i
            for j, (pb, lb) in enumerate(card_group):
                sel = (j == i)
                border = SELECTED_BORDER if sel else NORMAL_BORDER
                bg     = SELECTED_BG     if sel else NORMAL_BG
                pb.setStyleSheet(
                    f'QPushButton{{background:{bg};border:{border};border-radius:4px;padding:2px;}}'
                    f'QPushButton:hover{{background:#ddeeff;}}')
                lb.setStyleSheet(
                    f'QPushButton{{background:{bg};border:{border};border-radius:4px;'
                    f'font-size:10px;padding:2px;}}'
                    f'QPushButton:hover{{background:#ddeeff;}}')

        for i, (name, rows, cols, mosaic) in enumerate(LAYOUTS):
            cell = QWidget()
            cly = QVBoxLayout(cell)
            cly.setSpacing(2)
            cly.setContentsMargins(0,0,0,0)
            cly.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            # Clickable preview container
            prev_widget = _make_preview(rows, cols, mosaic)
            prev_btn = QPushButton()
            prev_btn.setFixedSize(96, 68)
            prev_btn.setFlat(True)
            inner = QVBoxLayout(prev_btn)
            inner.setContentsMargins(4,4,4,4)
            inner.addWidget(prev_widget)
            prev_btn.clicked.connect(lambda _, idx=i: _select_preset(idx))

            # Label button below
            lbl_btn = QPushButton(name)
            lbl_btn.setFixedHeight(36)
            lbl_btn.clicked.connect(lambda _, idx=i: _select_preset(idx))

            card_group.append((prev_btn, lbl_btn))
            cly.addWidget(prev_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            cly.addWidget(lbl_btn)
            grid.addWidget(cell, i // per_row, i % per_row)

        _select_preset(0)
        scroll_presets = QScrollArea()
        scroll_presets.setWidgetResizable(True)
        scroll_presets.setWidget(grid_w)
        presets_lay.addWidget(scroll_presets)
        inner_tabs.addTab(presets_w, '🗂 Presets')

        # ══════════════════════════════════════════════════════════════════════
        # TAB 2 — Custom mosaic editor
        # ══════════════════════════════════════════════════════════════════════
        custom_w = QWidget()
        custom_lay = QVBoxLayout(custom_w)

        # Grid size controls
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel('Rows:'))
        custom_rows = QSpinBox()
        custom_rows.setRange(1, 8)
        custom_rows.setValue(2)
        custom_rows.setFixedWidth(52)
        size_row.addWidget(custom_rows)
        size_row.addWidget(QLabel('Cols:'))
        custom_cols = QSpinBox()
        custom_cols.setRange(1, 8)
        custom_cols.setValue(2)
        custom_cols.setFixedWidth(52)
        size_row.addWidget(custom_cols)
        btn_rebuild = QPushButton('↺ Rebuild grid')
        btn_rebuild.setFixedWidth(110)
        size_row.addWidget(btn_rebuild)
        size_row.addStretch()
        custom_lay.addLayout(size_row)

        custom_lay.addWidget(QLabel(
            'Click cells to assign them to a subplot panel (drag to paint). '
            'Cells with the same colour/letter form one panel.'))

        # State for the custom editor
        custom_state = {
            'rows': 2, 'cols': 2,
            'grid': [['A','B'],['C','D']],   # current letter assignments
            'painting': False,
            'paint_letter': 'A',
        }

        # All available letters (panels)
        ALL_LETTERS = [chr(ord('A')+i) for i in range(26)]

        # Panel palette selector
        palette_row = QHBoxLayout()
        palette_row.setSpacing(4)
        palette_row.addWidget(QLabel('Active panel:'))
        palette_btns = {}

        def _letter_colour(letter):
            idx = ord(letter) - ord('A')
            return CELL_COLOURS[idx % len(CELL_COLOURS)]

        for letter in ALL_LETTERS[:8]:
            pb = QPushButton(letter)
            pb.setFixedSize(30, 28)
            pb.setCheckable(True)
            pb.setStyleSheet(f'background:{_letter_colour(letter)};border-radius:4px;font-weight:bold;')
            palette_btns[letter] = pb
            def _sel_letter(checked, l=letter):
                custom_state['paint_letter'] = l
                for ll, bb in palette_btns.items():
                    bb.setChecked(ll == l)
            pb.clicked.connect(_sel_letter)
            palette_row.addWidget(pb)
        palette_btns['A'].setChecked(True)
        palette_row.addStretch()
        custom_lay.addLayout(palette_row)

        # The cell grid container
        grid_frame = QFrame()
        grid_frame.setFrameShape(QFrame.Shape.StyledPanel)
        grid_frame_lay = QGridLayout(grid_frame)
        grid_frame_lay.setSpacing(3)
        grid_frame_lay.setContentsMargins(6,6,6,6)
        custom_lay.addWidget(grid_frame)

        cell_btns = {}   # (r,c) → QPushButton

        # Live preview container — a QWidget with a QGridLayout that mirrors the mosaic
        preview_container = QWidget()
        preview_container.setFixedSize(180, 120)
        preview_grid_lay = QGridLayout(preview_container)
        preview_grid_lay.setSpacing(3)
        preview_grid_lay.setContentsMargins(4,4,4,4)
        preview_cells = {}  # (r,c) → QLabel

        def _update_preview_widget():
            """Rebuild the small preview to mirror current grid state."""
            for lbl in preview_cells.values():
                preview_grid_lay.removeWidget(lbl)
                lbl.deleteLater()
            preview_cells.clear()
            rows = custom_state['rows']
            cols = custom_state['cols']
            grid = custom_state['grid']
            # Compute spans by finding each letter's bounding box
            spans = {}
            for ri, row in enumerate(grid):
                for ci, letter in enumerate(row):
                    if letter not in spans:
                        spans[letter] = [ri, ci, ri, ci]
                    else:
                        spans[letter][2] = max(spans[letter][2], ri)
                        spans[letter][3] = max(spans[letter][3], ci)
            # Number panels in order of first appearance
            order = list(dict.fromkeys(letter for row in grid for letter in row))
            for num, letter in enumerate(order, 1):
                r0, c0, r1, c1 = spans[letter]
                lbl = QLabel(str(num))
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    f'background:{_letter_colour(letter)};border:1px solid #777;'
                    f'border-radius:3px;font-size:11px;font-weight:bold;')
                preview_grid_lay.addWidget(lbl, r0, c0, r1-r0+1, c1-c0+1)
                preview_cells[letter] = lbl

        def _refresh_grid_ui():
            # Clear existing paint buttons
            for btn in cell_btns.values():
                grid_frame_lay.removeWidget(btn)
                btn.deleteLater()
            cell_btns.clear()
            rows = custom_state['rows']
            cols = custom_state['cols']
            grid = custom_state['grid']
            for r in range(rows):
                for c in range(cols):
                    letter = grid[r][c]
                    btn = QPushButton(letter)
                    btn.setFixedSize(60, 44)
                    btn.setStyleSheet(
                        f'background:{_letter_colour(letter)};border-radius:4px;'
                        f'font-size:14px;font-weight:bold;border:1px solid #888;')
                    def _paint(checked=False, rr=r, cc=c):
                        custom_state['grid'][rr][cc] = custom_state['paint_letter']
                        _refresh_grid_ui()
                    btn.clicked.connect(_paint)
                    grid_frame_lay.addWidget(btn, r, c)
                    cell_btns[(r,c)] = btn
            _update_preview_widget()

        def _rebuild_grid():
            rows = custom_rows.value()
            cols = custom_cols.value()
            old = custom_state['grid']
            new_grid = []
            for r in range(rows):
                row_data = []
                for c in range(cols):
                    if r < len(old) and c < len(old[r]):
                        row_data.append(old[r][c])
                    else:
                        used = {cell for row in new_grid for cell in row}
                        for l in ALL_LETTERS:
                            if l not in used:
                                row_data.append(l)
                                break
                        else:
                            row_data.append('A')
                new_grid.append(row_data)
            custom_state['rows'] = rows
            custom_state['cols'] = cols
            custom_state['grid'] = new_grid
            _refresh_grid_ui()

        btn_rebuild.clicked.connect(_rebuild_grid)
        _refresh_grid_ui()   # initial render

        # Live preview
        prev_row = QHBoxLayout()
        prev_row.addWidget(QLabel('Preview:'))
        prev_row.addWidget(preview_container)
        prev_row.addStretch()
        custom_lay.addLayout(prev_row)
        custom_lay.addStretch()

        inner_tabs.addTab(custom_w, '✏️ Custom mosaic')

        # ── Shared options ────────────────────────────────────────────────────
        share_row = QHBoxLayout()
        share_x = QCheckBox('Share X axis')
        share_x.setChecked(self.sp_sharex.isChecked())
        share_y = QCheckBox('Share Y axis')
        share_y.setChecked(self.sp_sharey.isChecked())
        share_row.addWidget(share_x)
        share_row.addWidget(share_y)
        share_row.addStretch()
        dlg_lay.addLayout(share_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dlg_lay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.sp_sharex.setChecked(share_x.isChecked())
        self.sp_sharey.setChecked(share_y.isChecked())

        # Determine which tab was active → presets or custom
        if inner_tabs.currentIndex() == 0:
            # Preset selected
            _, rows, cols, mosaic = LAYOUTS[selected_preset[0]]
        else:
            # Custom mosaic
            rows = custom_state['rows']
            cols = custom_state['cols']
            raw_grid = custom_state['grid']
            # Validate: every cell must have same letter = forms a contiguous block
            # (matplotlib mosaic just needs the list-of-lists, contiguity checked at render)
            mosaic = raw_grid

        self._subplot_mosaic = mosaic

        if mosaic is None:
            self.sp_rows.setValue(rows)
            self.sp_cols.setValue(cols)
        else:
            cells = list(dict.fromkeys(c for row in mosaic for c in row))
            n = len(cells)
            self.sp_rows.blockSignals(True)
            self.sp_cols.blockSignals(True)
            self.sp_rows.setValue(rows)
            self.sp_cols.setValue(cols)
            self.sp_rows.blockSignals(False)
            self.sp_cols.blockSignals(False)
            self.subplot_rows = rows
            self.subplot_cols = cols
            self.on_subplot_layout_changed(n_override=n)
            self.update_preview()

