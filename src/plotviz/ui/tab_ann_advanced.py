"""
Copyright (c) 2026 Paulo Cachim
ui/tab_ann_advanced.py  –  plotviz
TabAnnAdvMixin: create_annotations_tab() and create_advanced_tab()
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QScrollArea, QListWidget,
    QCheckBox, QPlainTextEdit, QGroupBox, QTabWidget, QSizePolicy,
)
from PyQt6.QtGui import QFont
from data.scientific import CurveFitter

_FONTS = ['sans-serif', 'serif', 'monospace']


class TabAnnAdvMixin:
    def create_annotations_tab(self):
        widget = QWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def irow(*widgets):
            """Pack widgets onto one horizontal row."""
            r = QHBoxLayout(); r.setSpacing(4)
            for w in widgets: r.addWidget(w)
            r.addStretch(); layout.addLayout(r)

        def lrow(label, *widgets):
            """Fixed-width label + widgets on one row."""
            r = QHBoxLayout(); r.setSpacing(4)
            lb = QLabel(label); lb.setFixedWidth(76); r.addWidget(lb)
            for w in widgets: r.addWidget(w)
            r.addStretch(); layout.addLayout(r)

        def color_btn(attr, default):
            sw = QLabel('■'); sw.setStyleSheet(f'color:{default};font-size:16px;')
            setattr(self, attr, default)
            setattr(self, attr + '_sw', sw)
            btn = QPushButton('…'); btn.setFixedWidth(24)
            btn.clicked.connect(lambda _=False, a=attr: self._pick_ann_color_attr(a))
            return sw, btn

        # ── Subplot selector ─────────────────────────────────────────────────
        ann_sp_row = QHBoxLayout(); ann_sp_row.setSpacing(6)
        ann_sp_row.addWidget(QLabel('Subplot:'))
        self.ann_sp_active = QComboBox(); self.ann_sp_active.addItem('Subplot 1')
        self.ann_sp_active.currentIndexChanged.connect(self._on_ann_subplot_changed)
        ann_sp_row.addWidget(self.ann_sp_active); ann_sp_row.addStretch()
        self._ann_sp_row_widget = QWidget()
        self._ann_sp_row_widget.setLayout(ann_sp_row)
        self._ann_sp_row_widget.setVisible(False)
        layout.addWidget(self._ann_sp_row_widget)

        # ── Show/hide annotations for current subplot ─────────────────────────
        vis_row = QHBoxLayout(); vis_row.setSpacing(6)
        self.ann_subplot_visible = QCheckBox('Show annotations on this subplot')
        self.ann_subplot_visible.setChecked(True)
        self.ann_subplot_visible.stateChanged.connect(self._on_ann_subplot_visibility_changed)
        vis_row.addWidget(self.ann_subplot_visible); vis_row.addStretch()
        layout.addLayout(vis_row)
        layout.addWidget(self._hline())

        # ── Mode buttons (2×2 grid) ───────────────────────────────────────────
        self.ann_none_btn  = QPushButton('🖱 Normal/Drag')
        self.ann_text_btn  = QPushButton('📝 Text')
        self.ann_arrow_btn = QPushButton('➡ Arrow')
        self.ann_image_btn = QPushButton('🖼 Image')
        for btn in (self.ann_none_btn, self.ann_text_btn,
                    self.ann_arrow_btn, self.ann_image_btn):
            btn.setCheckable(True)
        self.ann_none_btn.setChecked(True)
        self.ann_none_btn.clicked.connect(lambda: self.set_annotation_mode(None))
        self.ann_text_btn.clicked.connect(lambda: self.set_annotation_mode('text'))
        self.ann_arrow_btn.clicked.connect(lambda: self.set_annotation_mode('arrow'))
        self.ann_image_btn.clicked.connect(self._start_image_annotation)
        r_mode1 = QHBoxLayout(); r_mode1.setSpacing(3)
        r_mode1.addWidget(self.ann_none_btn); r_mode1.addWidget(self.ann_text_btn)
        layout.addLayout(r_mode1)
        r_mode2 = QHBoxLayout(); r_mode2.setSpacing(3)
        r_mode2.addWidget(self.ann_arrow_btn); r_mode2.addWidget(self.ann_image_btn)
        layout.addLayout(r_mode2)

        self.ann_image_zoom = QDoubleSpinBox(); self.ann_image_zoom.setRange(0.01,5.0)
        self.ann_image_zoom.setValue(0.15); self.ann_image_zoom.setSingleStep(0.01)
        lrow('Img zoom:', self.ann_image_zoom)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Style for new annotations:'))

        # Font row
        self.ann_font = QComboBox(); self.ann_font.addItems(_FONTS)
        self.ann_font.setFixedWidth(110)
        self.ann_font.currentTextChanged.connect(self._sync_ann_style)
        self.ann_fontsize = QSpinBox(); self.ann_fontsize.setRange(6,48); self.ann_fontsize.setValue(10)
        self.ann_fontsize.setFixedWidth(52)
        self.ann_fontsize.valueChanged.connect(self._sync_ann_style)
        lrow('Font:', self.ann_font, QLabel('Sz:'), self.ann_fontsize)

        # Font color
        self.ann_fontcolor = '#000000'
        fc_sw, fc_btn = color_btn('ann_fontcolor', '#000000')
        lrow('Font color:', fc_sw, fc_btn)

        # BG color + opacity
        self.ann_bgcolor = '#ffffcc'
        bg_sw, bg_btn = color_btn('ann_bgcolor', '#ffffcc')
        self.ann_bg_alpha = QDoubleSpinBox(); self.ann_bg_alpha.setRange(0,1)
        self.ann_bg_alpha.setSingleStep(0.05); self.ann_bg_alpha.setValue(0.9)
        self.ann_bg_alpha.setFixedWidth(58)
        self.ann_bg_alpha.valueChanged.connect(self._sync_ann_style)
        lrow('BG:', bg_sw, bg_btn, QLabel('α:'), self.ann_bg_alpha)

        # Edge color
        self.ann_edgecolor = '#aaaaaa'
        ec_sw, ec_btn = color_btn('ann_edgecolor', '#aaaaaa')
        lrow('Border:', ec_sw, ec_btn)

        layout.addWidget(self._hline())

        # Manual position + place button on one row
        self.ann_x_override = QLineEdit(); self.ann_x_override.setPlaceholderText('X')
        self.ann_x_override.setFixedWidth(60)
        self.ann_y_override = QLineEdit(); self.ann_y_override.setPlaceholderText('Y')
        self.ann_y_override.setFixedWidth(60)
        btn_place = QPushButton('📍 Place'); btn_place.setFixedWidth(64)
        btn_place.clicked.connect(self._place_at_override)
        lrow('Position:', self.ann_x_override, self.ann_y_override, btn_place)

        # Undo / clear on one row
        btn_undo  = QPushButton('↩ Undo last')
        btn_clear = QPushButton('🗑 Clear all')
        btn_clear.clicked.connect(lambda: self.canvas.clear_annotations())
        btn_undo.clicked.connect(lambda: self.canvas.remove_last_annotation())
        irow(btn_undo, btn_clear)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Annotations (select → Edit/Delete):'))
        self.ann_list_widget = QListWidget(); self.ann_list_widget.setMaximumHeight(110)
        layout.addWidget(self.ann_list_widget)

        btn_edit = QPushButton('✏️ Edit selected')
        btn_del  = QPushButton('🗑 Delete selected')
        btn_edit.clicked.connect(self._edit_selected_annotation)
        btn_del.clicked.connect(self._delete_selected_annotation)
        irow(btn_edit, btn_del)

        layout.addStretch()
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.tabs.addTab(widget,'Annotate')

    # ─── Advanced tab ─────────────────────────────────────────────────────────
    def create_advanced_tab(self):
        # Outer scroll wraps everything so the whole tab is scrollable
        outer_widget = QWidget()
        outer_scroll = QScrollArea(); outer_scroll.setWidgetResizable(True)
        outer_content = QWidget()
        outer_lay = QVBoxLayout(outer_content)
        outer_lay.setContentsMargins(6, 6, 6, 6); outer_lay.setSpacing(8)

        # ── Section title ──────────────────────────────────────────────────────
        title_lbl = QLabel('DATASET GENERATION')
        title_lbl.setStyleSheet('font-weight:bold; font-size:11px; color:#888; letter-spacing:1px;')
        outer_lay.addWidget(title_lbl)

        # ── Top: compact inner QTabWidget for f(x) and Data Table ─────────────
        inner_tabs = QTabWidget()
        inner_tabs.setDocumentMode(True)
        inner_tabs.setTabPosition(QTabWidget.TabPosition.North)
        inner_tabs.setMaximumWidth(420)
        inner_tabs.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # ── Inner tab 1 — Function Generator ──────────────────────────────────
        fg_content = QWidget()
        fg_lay = QVBoxLayout(fg_content); fg_lay.setSpacing(5); fg_lay.setContentsMargins(8,8,8,8)

        fg_lay.addWidget(self._sec_label('Function Generator'))

        mode_row = QHBoxLayout(); mode_row.setSpacing(4)
        mode_row.addWidget(QLabel('Input:'))
        self._adv_mode_range = QRadioButton('x range')
        self._adv_mode_col   = QRadioButton('column')
        self._adv_mode_range.setChecked(True)
        mode_row.addWidget(self._adv_mode_range); mode_row.addWidget(self._adv_mode_col)
        mode_row.addStretch(); fg_lay.addLayout(mode_row)

        self._adv_range_widget = QWidget()
        rw_lay = QVBoxLayout(self._adv_range_widget); rw_lay.setContentsMargins(0,0,0,0); rw_lay.setSpacing(3)
        xr = QHBoxLayout(); xr.setSpacing(4)
        xr.addWidget(QLabel('x:'))
        self.gen_x_min = QDoubleSpinBox(); self.gen_x_min.setRange(-1e9,1e9); self.gen_x_min.setValue(0); self.gen_x_min.setDecimals(3); self.gen_x_min.setFixedWidth(72)
        xr.addWidget(self.gen_x_min); xr.addWidget(QLabel('→'))
        self.gen_x_max = QDoubleSpinBox(); self.gen_x_max.setRange(-1e9,1e9); self.gen_x_max.setValue(10); self.gen_x_max.setDecimals(3); self.gen_x_max.setFixedWidth(72)
        xr.addWidget(self.gen_x_max); xr.addWidget(QLabel('n:'))
        self.gen_x_n = QSpinBox(); self.gen_x_n.setRange(2,100000); self.gen_x_n.setValue(200); self.gen_x_n.setFixedWidth(60)
        xr.addWidget(self.gen_x_n); xr.addStretch(); rw_lay.addLayout(xr)
        nr = QHBoxLayout(); nr.setSpacing(4); nr.addWidget(QLabel('x col:'))
        self.gen_x_name = QLineEdit('x'); self.gen_x_name.setFixedWidth(70); nr.addWidget(self.gen_x_name)
        nr.addStretch(); rw_lay.addLayout(nr)
        fg_lay.addWidget(self._adv_range_widget)

        self._adv_col_widget = QWidget()
        cw_lay = QVBoxLayout(self._adv_col_widget); cw_lay.setContentsMargins(0,0,0,0); cw_lay.setSpacing(3)
        src_row = QHBoxLayout(); src_row.setSpacing(4); src_row.addWidget(QLabel('Col:'))
        self.fn_source_combo = QComboBox(); self.fn_source_combo.setMinimumWidth(90); src_row.addWidget(self.fn_source_combo)
        src_row.addWidget(QLabel('as:'))
        self.fn_var_name = QLineEdit('x'); self.fn_var_name.setFixedWidth(40); src_row.addWidget(self.fn_var_name)
        src_row.addStretch(); cw_lay.addLayout(src_row)
        fg_lay.addWidget(self._adv_col_widget); self._adv_col_widget.setVisible(False)

        fg_lay.addWidget(QLabel('expr (np, sin, cos, exp, log, pi …):'))
        self.gen_expr = QLineEdit('sin(x)'); fg_lay.addWidget(self.gen_expr)
        self.fn_expr = self.gen_expr
        out_row = QHBoxLayout(); out_row.setSpacing(4); out_row.addWidget(QLabel('y col:'))
        self.gen_y_name = QLineEdit('y'); self.gen_y_name.setFixedWidth(70); out_row.addWidget(self.gen_y_name)
        self.fn_out_name = self.gen_y_name; out_row.addStretch(); fg_lay.addLayout(out_row)

        btn_gen = QPushButton('▶  Generate / Apply')
        btn_gen.clicked.connect(self._adv_generate_or_apply); fg_lay.addWidget(btn_gen)
        self.gen_status = QLabel(''); self.gen_status.setStyleSheet('color:#555;font-size:11px;')
        self.fn_status = self.gen_status; fg_lay.addWidget(self.gen_status)

        def _on_mode_toggle():
            use_range = self._adv_mode_range.isChecked()
            self._adv_range_widget.setVisible(use_range)
            self._adv_col_widget.setVisible(not use_range)
        self._adv_mode_range.toggled.connect(_on_mode_toggle)
        fg_lay.addStretch()
        inner_tabs.addTab(fg_content, '𝑓(x)')

        # ── Inner tab 2 — Manual Data Table ───────────────────────────────────
        dt_widget = QWidget()
        dt_lay = QVBoxLayout(dt_widget); dt_lay.setSpacing(5); dt_lay.setContentsMargins(8,8,8,8)

        tc = QHBoxLayout(); tc.setSpacing(3)
        tc.addWidget(QLabel('Cols:'))
        self.table_cols_spin = QSpinBox(); self.table_cols_spin.setRange(1,20); self.table_cols_spin.setValue(2); self.table_cols_spin.setFixedWidth(46); tc.addWidget(self.table_cols_spin)
        tc.addWidget(QLabel('Rows:'))
        self.table_rows_spin = QSpinBox(); self.table_rows_spin.setRange(1,10000); self.table_rows_spin.setValue(5); self.table_rows_spin.setFixedWidth(55); tc.addWidget(self.table_rows_spin)
        btn_new_table = QPushButton('New'); btn_new_table.setFixedWidth(46); btn_new_table.clicked.connect(self._new_data_table); tc.addWidget(btn_new_table)
        tc.addStretch(); dt_lay.addLayout(tc)

        self.data_table = QTableWidget(5, 2)
        self.data_table.setHorizontalHeaderLabels(['col_1', 'col_2'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.horizontalHeader().sectionDoubleClicked.connect(self._rename_table_col)
        dt_lay.addWidget(self.data_table, stretch=1)

        tr = QHBoxLayout(); tr.setSpacing(3)
        for label, slot in [('＋R', self._table_add_row), ('－R', self._table_del_row),
                             ('＋C', self._table_add_col), ('－C', self._table_del_col)]:
            b = QPushButton(label); b.setFixedWidth(34); b.clicked.connect(slot); tr.addWidget(b)
        btn_clr   = QPushButton('🗑'); btn_clr.setFixedWidth(34);   btn_clr.clicked.connect(self._table_clear);     tr.addWidget(btn_clr)
        btn_paste = QPushButton('📋'); btn_paste.setFixedWidth(34); btn_paste.clicked.connect(self._table_paste_csv); tr.addWidget(btn_paste)
        tr.addStretch(); dt_lay.addLayout(tr)

        load_row = QHBoxLayout(); load_row.setSpacing(4)
        btn_load_table = QPushButton('📥 Load'); btn_load_table.clicked.connect(self._load_table_data)
        btn_copy_csv   = QPushButton('📤 CSV');  btn_copy_csv.clicked.connect(self._table_copy_csv)
        load_row.addWidget(btn_load_table); load_row.addWidget(btn_copy_csv); load_row.addStretch()
        dt_lay.addLayout(load_row)
        self.table_status = QLabel(''); self.table_status.setStyleSheet('color:#555;font-size:11px;')
        dt_lay.addWidget(self.table_status)
        inner_tabs.addTab(dt_widget, '📋 Table')

        # Size inner tabs to their content (no forced stretch)
        inner_tabs.adjustSize()
        outer_lay.addWidget(inner_tabs)

        # ── Separator ─────────────────────────────────────────────────────────
        outer_lay.addWidget(self._hline())

        # ── Curve Fit — below the tabs, full-width ────────────────────────────
        outer_lay.addWidget(self._sec_label('Curve Fit (Line / Scatter)'))

        fr = QHBoxLayout(); fr.addWidget(QLabel('Model:'))
        self.fit_combo = QComboBox(); self.fit_combo.addItem('None')
        self.fit_combo.addItems(CurveFitter.MODELS.keys())
        fr.addWidget(self.fit_combo); fr.addStretch(); outer_lay.addLayout(fr)

        btn_fit = QPushButton('▶  Apply Fit')
        btn_fit.clicked.connect(self.apply_fit); outer_lay.addWidget(btn_fit)

        ci_row = QHBoxLayout(); ci_row.setSpacing(6); ci_row.addWidget(QLabel('Conf. band:'))
        self.fit_ci_combo = QComboBox()
        self.fit_ci_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_ci_combo.currentIndexChanged.connect(self._on_ci_changed)
        ci_row.addWidget(self.fit_ci_combo); ci_row.addStretch(); outer_lay.addLayout(ci_row)

        pi_row = QHBoxLayout(); pi_row.setSpacing(6); pi_row.addWidget(QLabel('Pred. band:'))
        self.fit_pi_combo = QComboBox()
        self.fit_pi_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_pi_combo.currentIndexChanged.connect(self._on_ci_changed)
        pi_row.addWidget(self.fit_pi_combo); pi_row.addStretch(); outer_lay.addLayout(pi_row)

        self.fit_ci_alpha_spin = QDoubleSpinBox()
        self.fit_ci_alpha_spin.setRange(0.05, 1.0); self.fit_ci_alpha_spin.setSingleStep(0.05); self.fit_ci_alpha_spin.setValue(0.25)
        self.fit_ci_alpha_spin.valueChanged.connect(self.update_preview)
        ci_alpha_row = QHBoxLayout(); ci_alpha_row.setSpacing(6)
        ci_alpha_row.addWidget(QLabel('Band opacity:')); ci_alpha_row.addWidget(self.fit_ci_alpha_spin)
        ci_alpha_row.addStretch(); outer_lay.addLayout(ci_alpha_row)

        res_box = QGroupBox('Fit Results')
        res_lay = QVBoxLayout(res_box); res_lay.setSpacing(2); res_lay.setContentsMargins(4,4,4,4)
        self.fit_results_text = QPlainTextEdit()
        self.fit_results_text.setReadOnly(True)
        self.fit_results_text.setMinimumHeight(220)
        self.fit_results_text.setFont(QFont('Courier New' if __import__('sys').platform == 'win32' else 'Menlo' if __import__('sys').platform == 'darwin' else 'monospace', 9))
        self.fit_results_text.setPlainText('Run a fit to see results.')
        # Keep backwards-compat aliases
        self.fit_eq_label = QLabel(''); self.fit_eq_label.setVisible(False)
        self.fit_r2_label = QLabel(''); self.fit_r2_label.setVisible(False)
        res_lay.addWidget(self.fit_results_text)
        outer_lay.addWidget(res_box)

        outer_lay.addStretch()
        outer_scroll.setWidget(outer_content)
        mlay = QVBoxLayout(outer_widget); mlay.setContentsMargins(0,0,0,0); mlay.addWidget(outer_scroll)
        self.tabs.addTab(outer_widget, 'Advanced')


