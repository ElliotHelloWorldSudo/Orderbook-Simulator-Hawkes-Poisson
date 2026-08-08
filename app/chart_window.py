import collections

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPicture, QPen, QBrush
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QComboBox, QPushButton, QColorDialog, QDoubleSpinBox, QToolBar,
)

from app.theme import PALETTE, CHART_BACKGROUND_PRESETS

pg.setConfigOptions(antialias=True)


class CandlestickItem(pg.GraphicsObject):

    def __init__(self):
        super().__init__()
        self.data = []
        self.picture = QPicture()
        self.bull_color = QColor("#3ddc97")
        self.bear_color = QColor("#ff6b6b")
        self.width = 0.6

    def set_colors(self, bull, bear):
        self.bull_color = QColor(bull)
        self.bear_color = QColor(bear)
        self._generate()

    def set_data(self, candles, width=None):
        self.data = candles
        if width is not None:
            self.width = width
        self._generate()
        self.informViewBoundsChanged()
        self.update()

    def _generate(self):
        self.picture = QPicture()
        painter = QPainter(self.picture)
        w = self.width / 2.0
        for (t, o, h, l, c) in self.data:
            up = c >= o
            color = self.bull_color if up else self.bear_color
            painter.setPen(QPen(color, 0))
            painter.drawLine(QPointF(t, l), QPointF(t, h))
            painter.setBrush(QBrush(color))
            body_h = max(abs(c - o), 1e-6)
            rect = QRectF(t - w, min(o, c), self.width, body_h)
            painter.drawRect(rect)
        painter.end()

    def paint(self, painter, *args):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class CrosshairMixin:

    def _setup_crosshair(self, plot_widget, fmt=("t={:.2f}", "y={:.2f}")):
        self._ch_fmt = fmt
        vb = plot_widget.getPlotItem().getViewBox()
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#8b90a6", width=1))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#8b90a6", width=1))
        plot_widget.addItem(self.v_line, ignoreBounds=True)
        plot_widget.addItem(self.h_line, ignoreBounds=True)
        self.coord_label = pg.TextItem(anchor=(0, 1), color="#f2f4fa", fill=(20, 22, 28, 180))
        plot_widget.addItem(self.coord_label)
        self.coord_label.setPos(0, 0)
        self._proxy = pg.SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60,
                                      slot=lambda evt: self._on_mouse_moved(evt, plot_widget))

    def _on_mouse_moved(self, evt, plot_widget):
        pos = evt[0]
        vb = plot_widget.getPlotItem().getViewBox()
        if plot_widget.sceneBoundingRect().contains(pos):
            mouse_pt = vb.mapSceneToView(pos)
            x, y = mouse_pt.x(), mouse_pt.y()
            self.v_line.setPos(x)
            self.h_line.setPos(y)
            t_fmt, y_fmt = self._ch_fmt
            self.coord_label.setText(f"{t_fmt.format(x)}\n{y_fmt.format(y)}")
            self.coord_label.setPos(x, y)


class LineChartPanel(QWidget, CrosshairMixin):
    def __init__(self, theme_mode="dark", parent=None):
        super().__init__(parent)
        self.theme_mode = theme_mode
        self.buf_t = collections.deque(maxlen=8000)
        self.buf_y = collections.deque(maxlen=8000)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("bottom", "Simulated time")
        self.plot.setLabel("left", "Mid price")
        self.curve = self.plot.plot([], [], pen=pg.mkPen(PALETTE[theme_mode]["accent"], width=2))
        layout.addWidget(self.plot)
        self._setup_crosshair(self.plot, fmt=("t={:.2f}", "px={:.2f}"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._redraw)
        self.timer.start(66)

        self.apply_background(None)

    def push(self, t, y):
        if y is None:
            return
        self.buf_t.append(t)
        self.buf_y.append(y)

    def _redraw(self):
        if self.buf_t:
            self.curve.setData(list(self.buf_t), list(self.buf_y))

    def clear(self):
        self.buf_t.clear()
        self.buf_y.clear()
        self.curve.setData([], [])

    def apply_background(self, color_hex):
        bg = color_hex if color_hex else PALETTE[self.theme_mode]["chart_bg"]
        self.plot.setBackground(bg)

    def set_line_color(self, color_hex):
        self.curve.setPen(pg.mkPen(color_hex, width=2))


class CandlestickPanel(QWidget, CrosshairMixin):
    def __init__(self, theme_mode="dark", bucket_seconds=2.0, parent=None):
        super().__init__(parent)
        self.theme_mode = theme_mode
        self.bucket_seconds = bucket_seconds
        self._bucket_start = None
        self._o = self._h = self._l = self._c = None
        self.candles = collections.deque(maxlen=1500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("bottom", "Simulated time")
        self.plot.setLabel("left", "Trade price")
        self.item = CandlestickItem()
        pal = PALETTE[theme_mode]
        self.item.set_colors(pal["candle_bull"], pal["candle_bear"])
        self.plot.addItem(self.item)
        layout.addWidget(self.plot)
        self._setup_crosshair(self.plot, fmt=("t={:.2f}", "px={:.2f}"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._redraw)
        self.timer.start(150)

        self.apply_background(None)
        self._dirty = False

    def set_bucket_seconds(self, seconds):
        self.bucket_seconds = max(0.05, seconds)

    def push_trade(self, t, price):
        bucket = int(t // self.bucket_seconds)
        if self._bucket_start is None or bucket != self._bucket_start:
            if self._bucket_start is not None:
                mid_t = self._bucket_start * self.bucket_seconds + self.bucket_seconds / 2.0
                self.candles.append((mid_t, self._o, self._h, self._l, self._c))
            self._bucket_start = bucket
            self._o = self._h = self._l = self._c = price
        else:
            self._h = max(self._h, price)
            self._l = min(self._l, price)
            self._c = price
        self._dirty = True

    def _redraw(self):
        if not self._dirty:
            return
        self._dirty = False
        preview = list(self.candles)
        if self._bucket_start is not None and self._o is not None:
            mid_t = self._bucket_start * self.bucket_seconds + self.bucket_seconds / 2.0
            preview.append((mid_t, self._o, self._h, self._l, self._c))
        self.item.set_data(preview, width=self.bucket_seconds * 0.7)

    def clear(self):
        self.candles.clear()
        self._bucket_start = None
        self._o = self._h = self._l = self._c = None
        self.item.set_data([])

    def apply_background(self, color_hex):
        bg = color_hex if color_hex else PALETTE[self.theme_mode]["chart_bg"]
        self.plot.setBackground(bg)


class ChartWindow(QMainWindow):
    def __init__(self, worker, theme_mode="dark", parent=None):
        super().__init__(parent)
        self.worker = worker
        self.theme_mode = theme_mode
        self.setWindowTitle("Charts \u2014 Live Market")
        self.resize(1000, 680)

        self._build_toolbar()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.line_panel = LineChartPanel(theme_mode=theme_mode)
        self.candle_panel = CandlestickPanel(theme_mode=theme_mode)
        self.tabs.addTab(self.line_panel, "Line \u2014 Mid Price")
        self.tabs.addTab(self.candle_panel, "Candlestick \u2014 Trades")

        self.worker.market_update.connect(self._on_market_update)
        self.worker.trade_occurred.connect(self._on_trade)

    def _build_toolbar(self):
        tb = QToolBar("Chart controls")
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addWidget(QLabel("  Background  "))
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(list(CHART_BACKGROUND_PRESETS.keys()))
        self.bg_combo.currentTextChanged.connect(self._on_bg_preset)
        tb.addWidget(self.bg_combo)

        custom_btn = QPushButton("Custom color\u2026")
        custom_btn.clicked.connect(self._pick_custom_bg)
        tb.addWidget(custom_btn)

        tb.addSeparator()
        tb.addWidget(QLabel("  Candle bucket (sim time)  "))
        self.bucket_spin = QDoubleSpinBox()
        self.bucket_spin.setRange(0.1, 120.0)
        self.bucket_spin.setSingleStep(0.5)
        self.bucket_spin.setValue(2.0)
        self.bucket_spin.valueChanged.connect(self.candle_panel_set_bucket)
        tb.addWidget(self.bucket_spin)

    def candle_panel_set_bucket(self, val):
        self.candle_panel.set_bucket_seconds(val)

    def _on_bg_preset(self, name):
        color = CHART_BACKGROUND_PRESETS.get(name)
        self.line_panel.apply_background(color)
        self.candle_panel.apply_background(color)

    def _pick_custom_bg(self):
        color = QColorDialog.getColor(QColor(PALETTE[self.theme_mode]["chart_bg"]), self,
                                       "Choose chart background")
        if color.isValid():
            self.bg_combo.setCurrentIndex(0)
            self.line_panel.apply_background(color.name())
            self.candle_panel.apply_background(color.name())

    def _on_market_update(self, payload):
        if payload["mid"] is not None:
            self.line_panel.push(payload["t"], payload["mid"])

    def _on_trade(self, fill):
        self.candle_panel.push_trade(fill.timestamp, fill.trade_price)

    def clear(self):
        self.line_panel.clear()
        self.candle_panel.clear()

    def set_theme(self, theme_mode):
        self.theme_mode = theme_mode
        self.line_panel.theme_mode = theme_mode
        self.candle_panel.theme_mode = theme_mode
        pal = PALETTE[theme_mode]
        self.line_panel.set_line_color(pal["accent"])
        self.candle_panel.item.set_colors(pal["candle_bull"], pal["candle_bear"])
        if self.bg_combo.currentIndex() == 0:
            self._on_bg_preset(self.bg_combo.currentText())
