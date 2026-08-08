from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QToolBar, QPushButton,
    QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox, QSlider, QSplitter,
    QStatusBar, QAbstractItemView, QSizePolicy,
)

from engine import PriceLevelBotStrategy
from app.theme import PALETTE


def metric_card(label_text):
    frame = QFrame()
    frame.setProperty("card", "true")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(2)
    lbl = QLabel(label_text)
    lbl.setProperty("role", "metricLabel")
    val = QLabel("--")
    val.setProperty("role", "metricValue")
    lay.addWidget(lbl)
    lay.addWidget(val)
    return frame, val


class OrderbookWindow(QMainWindow):
    theme_toggled = Signal(str)
    open_charts_requested = Signal()
    open_backtester_requested = Signal()

    def __init__(self, session, worker, theme_mode="dark", parent=None):
        super().__init__(parent)
        self.session = session
        self.worker = worker
        self.theme_mode = theme_mode
        self.setWindowTitle("Order Book \u2014 Live Market")
        self.resize(1180, 760)

        self._build_toolbar()
        self._build_central()
        self.setStatusBar(QStatusBar())
        self._status_label = QLabel("Idle")
        self.statusBar().addWidget(self._status_label)

        self.worker.market_update.connect(self.on_market_update)
        self.worker.trade_occurred.connect(self.on_trade)

        self._trade_row_limit = 250
        self._running = False

    def _build_toolbar(self):
        tb = QToolBar("Controls")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.play_btn = QPushButton("\u25B6  Start")
        self.play_btn.setObjectName("accent")
        self.play_btn.clicked.connect(self.toggle_running)
        tb.addWidget(self.play_btn)

        reset_btn = QPushButton("\u21BB  Reset")
        reset_btn.clicked.connect(self.reset_session)
        tb.addWidget(reset_btn)

        tb.addSeparator()

        speed_lbl = QLabel("  Speed  ")
        tb.addWidget(speed_lbl)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(60)
        self.speed_slider.setValue(48)
        self.speed_slider.setFixedWidth(140)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        tb.addWidget(self.speed_slider)

        tb.addSeparator()

        charts_btn = QPushButton("\U0001F4C8  Charts")
        charts_btn.clicked.connect(self.open_charts_requested.emit)
        tb.addWidget(charts_btn)

        bt_btn = QPushButton("\u2699  Backtester")
        bt_btn.clicked.connect(self.open_backtester_requested.emit)
        tb.addWidget(bt_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.theme_btn = QPushButton("\u2600  Light" if self.theme_mode == "dark" else "\u263D  Dark")
        self.theme_btn.clicked.connect(self._toggle_theme)
        tb.addWidget(self.theme_btn)

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        metrics_frame = QFrame()
        grid = QGridLayout(metrics_frame)
        grid.setSpacing(10)
        specs = [
            "Mid Price", "Best Bid", "Best Ask", "Spread", "Sim Time",
            "Cash", "Position", "Avg Entry", "Realized PnL", "Unrealized PnL",
            "Equity", "Total PnL", "Fills",
        ]
        self.metric_values = {}
        for i, name in enumerate(specs):
            card, val = metric_card(name)
            self.metric_values[name] = val
            grid.addWidget(card, i // 7, i % 7)
        root.addWidget(metrics_frame)

        quotes_box = QGroupBox("My Quotes  (Price-Level Bot)")
        qlay = QHBoxLayout(quotes_box)
        self.quotes_enable = QCheckBox("Enable")
        self.quotes_enable.stateChanged.connect(self._on_quotes_toggle)
        qlay.addWidget(self.quotes_enable)

        qlay.addWidget(QLabel("Spread (ticks)"))
        self.q_spread = QSpinBox()
        self.q_spread.setRange(1, 200)
        self.q_spread.setValue(4)
        qlay.addWidget(self.q_spread)

        qlay.addWidget(QLabel("Order size"))
        self.q_size = QSpinBox()
        self.q_size.setRange(1, 1000)
        self.q_size.setValue(5)
        qlay.addWidget(self.q_size)

        qlay.addWidget(QLabel("Requote interval"))
        self.q_interval = QDoubleSpinBox()
        self.q_interval.setRange(0.05, 60.0)
        self.q_interval.setSingleStep(0.1)
        self.q_interval.setValue(1.0)
        qlay.addWidget(self.q_interval)
        qlay.addStretch(1)
        root.addWidget(quotes_box)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.ladder = QTableWidget(15, 4)
        self.ladder.setHorizontalHeaderLabels(["Bid Qty", "Bid", "Ask", "Ask Qty"])
        self.ladder.verticalHeader().setVisible(False)
        self.ladder.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ladder.setSelectionMode(QAbstractItemView.NoSelection)
        self.ladder.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ladder.setAlternatingRowColors(True)
        splitter.addWidget(self.ladder)

        self.trades_table = QTableWidget(0, 5)
        self.trades_table.setHorizontalHeaderLabels(["Time", "Price", "Qty", "Side", "Type"])
        self.trades_table.verticalHeader().setVisible(False)
        self.trades_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trades_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setAlternatingRowColors(True)
        splitter.addWidget(self.trades_table)

        splitter.setSizes([650, 450])
        root.addWidget(splitter, stretch=1)

    def _on_speed_changed(self, slider_val):
        ms = max(0, 60 - slider_val)
        self.worker.set_speed_ms(ms)

    def toggle_running(self):
        self._running = not self._running
        if self._running:
            self.play_btn.setText("\u23F8  Pause")
            self.worker.set_paused(False)
            if not self.worker.isRunning():
                self.worker.start()
            self._status_label.setText("Running")
        else:
            self.play_btn.setText("\u25B6  Start")
            self.worker.set_paused(True)
            self._status_label.setText("Paused")

    def reset_session(self):
        was_running = self._running
        self.worker.set_paused(True)
        QTimer.singleShot(120, lambda: self._do_reset(was_running))

    def _do_reset(self, resume):
        import random
        self.session.reset(seed=random.randint(1, 10_000_000), taker_seed=random.randint(1, 10_000_000))
        self.worker.resubscribe()
        self.quotes_enable.setChecked(False)
        self.trades_table.setRowCount(0)
        for r in range(self.ladder.rowCount()):
            for c in range(4):
                self.ladder.setItem(r, c, QTableWidgetItem(""))
        for v in self.metric_values.values():
            v.setText("--")
        parent = self.parent()
        if hasattr(self, "on_reset_callback") and self.on_reset_callback:
            self.on_reset_callback()
        if resume:
            self.worker.set_paused(False)
        self._status_label.setText("Reset")

    def _on_quotes_toggle(self, state):
        enabled = bool(state)
        self.worker.set_paused(True)

        def apply():
            if enabled:
                strat = PriceLevelBotStrategy(
                    spread_ticks=self.q_spread.value(),
                    order_size=self.q_size.value(),
                    tick_size=0.01,
                    requote_interval=self.q_interval.value(),
                )
                self.session.attach_strategy(strat)
            else:
                self.session.detach_strategy()
            if self._running:
                self.worker.set_paused(False)

        QTimer.singleShot(80, apply)

    def _toggle_theme(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.theme_btn.setText("\u2600  Light" if self.theme_mode == "dark" else "\u263D  Dark")
        self.theme_toggled.emit(self.theme_mode)

    def on_market_update(self, payload):
        pal = PALETTE[self.theme_mode]
        mid = payload["mid"]
        bb, ba = payload["best_bid"], payload["best_ask"]
        spread = payload["spread"]
        pnl = payload["pnl"]

        self.metric_values["Mid Price"].setText(f"{mid:.2f}" if mid is not None else "--")
        self.metric_values["Best Bid"].setText(f"{bb:.2f}" if bb is not None else "--")
        self.metric_values["Best Ask"].setText(f"{ba:.2f}" if ba is not None else "--")
        self.metric_values["Spread"].setText(f"{spread:.2f}" if spread is not None else "--")
        self.metric_values["Sim Time"].setText(f"{payload['t']:.1f}")
        self.metric_values["Cash"].setText(f"{pnl['cash']:.2f}")
        self.metric_values["Position"].setText(f"{pnl['position']:.0f}")
        self.metric_values["Avg Entry"].setText(f"{pnl['avg_entry_price']:.2f}")
        self.metric_values["Fills"].setText(f"{pnl['num_fills']}")

        for key, label in (("realized_pnl", "Realized PnL"), ("unrealized_pnl", "Unrealized PnL"),
                            ("total_pnl", "Total PnL")):
            v = pnl[key]
            self.metric_values[label].setText(f"{v:+.2f}")
            self.metric_values[label].setProperty("pnl", "up" if v >= 0 else "down")
            self.metric_values[label].style().unpolish(self.metric_values[label])
            self.metric_values[label].style().polish(self.metric_values[label])

        equity = pnl["cash"] + pnl["position"] * (mid if mid is not None else pnl["avg_entry_price"])
        self.metric_values["Equity"].setText(f"{equity:.2f}")

        book = payload["book"]
        bids, asks = book["bids"], book["asks"]
        for r in range(self.ladder.rowCount()):
            bid_qty, bid_px = ("", "")
            ask_px, ask_qty = ("", "")
            if r < len(bids):
                bid_px, bid_qty = f"{bids[r][0]:.2f}", f"{bids[r][1]:.0f}"
            if r < len(asks):
                ask_px, ask_qty = f"{asks[r][0]:.2f}", f"{asks[r][1]:.0f}"
            self._set_ladder_cell(r, 0, bid_qty, None)
            self._set_ladder_cell(r, 1, bid_px, QColor(pal["bid"]))
            self._set_ladder_cell(r, 2, ask_px, QColor(pal["ask"]))
            self._set_ladder_cell(r, 3, ask_qty, None)

    def _set_ladder_cell(self, r, c, text, color):
        item = self.ladder.item(r, c)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.ladder.setItem(r, c, item)
        item.setText(text)
        if color is not None:
            item.setForeground(color)

    def on_trade(self, fill):
        pal = PALETTE[self.theme_mode]
        self.trades_table.insertRow(0)
        side_txt = "BUY" if fill.side.name == "BUY" else "SELL"
        vals = [f"{fill.timestamp:.2f}", f"{fill.trade_price:.2f}", f"{fill.quantity:.0f}",
                side_txt, f"{fill.incoming_type.name}/{fill.resting_type.name}"]
        for c, text in enumerate(vals):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if c == 3:
                item.setForeground(QColor(pal["bid"] if side_txt == "BUY" else pal["ask"]))
            self.trades_table.setItem(0, c, item)
        if self.trades_table.rowCount() > self._trade_row_limit:
            self.trades_table.removeRow(self.trades_table.rowCount() - 1)

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.set_paused(False)
        self.worker.wait(2000)
        super().closeEvent(event)
