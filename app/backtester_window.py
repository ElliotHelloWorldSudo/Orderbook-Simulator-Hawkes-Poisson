import pyqtgraph as pg
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QStackedWidget,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QAbstractItemView, QFrame, QGridLayout,
)

from engine import (
    EventBus, Clock, Mode_type, OrderBook, sim_engine, TakerFlowGenerator,
    PnLTracker, Type, Backtester, PriceLevelBotStrategy, AvellanedaStoikovStrategy,
    HeatEquationMarketMaker,
)
from app.theme import PALETTE
from app.orderbook_window import metric_card


class BacktestWorker(QThread):
    progress = Signal(int, int)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, strategy_factory, seed, taker_seed, mark_interval,
                 max_steps, max_time, max_abs_position, parent=None):
        super().__init__(parent)
        self.strategy_factory = strategy_factory
        self.seed = seed
        self.taker_seed = taker_seed
        self.mark_interval = mark_interval
        self.max_steps = max_steps
        self.max_time = max_time
        self.max_abs_position = max_abs_position
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            bus = EventBus()
            clock = Clock(Mode_type.generative)
            book = OrderBook(event_bus=bus, clock=clock)
            market = sim_engine(book, clock=clock, seed=self.seed)
            clock.set_generator(market.thinning)
            taker = TakerFlowGenerator(book, clock, seed=self.taker_seed)
            taker.start()
            pnl = PnLTracker(bus, track_type=Type.USER)
            strategy = self.strategy_factory()

            bt = Backtester(book, clock, bus, strategy, pnl_tracker=pnl,
                             mark_interval=self.mark_interval,
                             max_steps=self.max_steps, max_time=self.max_time,
                             max_abs_position=self.max_abs_position)

            strategy.on_start()
            progress_every = max(1, (self.max_steps or 2000) // 100)
            while bt.clock.has_more():
                if self._stop:
                    break
                if self.max_steps is not None and bt.result.num_steps >= self.max_steps:
                    break
                if self.max_time is not None and bt.clock.now() >= self.max_time:
                    break
                if not bt.step():
                    break
                if bt.result.num_steps % progress_every == 0:
                    self.progress.emit(bt.result.num_steps, self.max_steps or -1)

            mid = strategy.mid_price()
            if mid is not None:
                pnl.mark_to_market(mid, clock.now())
            bt.result.final_stats = pnl.summary()
            bt.result.final_stats["num_steps"] = bt.result.num_steps
            bt.result.final_stats["num_trades"] = len(bt.result.trades)
            self.progress.emit(bt.result.num_steps, self.max_steps or -1)
            self.finished_ok.emit(bt.result)
        except Exception as exc:
            self.failed.emit(str(exc))


class _PriceLevelParams(QWidget):
    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        self.spread_ticks = QSpinBox(); self.spread_ticks.setRange(1, 200); self.spread_ticks.setValue(4)
        self.order_size = QSpinBox(); self.order_size.setRange(1, 1000); self.order_size.setValue(5)
        self.tick_size = QDoubleSpinBox(); self.tick_size.setDecimals(4); self.tick_size.setRange(0.0001, 10.0)
        self.tick_size.setValue(0.01)
        self.requote = QDoubleSpinBox(); self.requote.setRange(0.05, 60.0); self.requote.setValue(1.0)
        form.addRow("Spread (ticks)", self.spread_ticks)
        form.addRow("Order size", self.order_size)
        form.addRow("Tick size", self.tick_size)
        form.addRow("Requote interval", self.requote)

    def build(self):
        return lambda: PriceLevelBotStrategy(
            spread_ticks=self.spread_ticks.value(), order_size=self.order_size.value(),
            tick_size=self.tick_size.value(), requote_interval=self.requote.value())


class _AvellanedaParams(QWidget):
    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        self.gamma = QDoubleSpinBox(); self.gamma.setRange(0.01, 50.0); self.gamma.setValue(1.5)
        self.k = QDoubleSpinBox(); self.k.setRange(0.1, 10000.0); self.k.setValue(100.0)
        self.horizon = QDoubleSpinBox(); self.horizon.setRange(1.0, 100000.0); self.horizon.setValue(200.0)
        self.order_size = QSpinBox(); self.order_size.setRange(1, 1000); self.order_size.setValue(5)
        self.tick_size = QDoubleSpinBox(); self.tick_size.setDecimals(4); self.tick_size.setRange(0.0001, 10.0)
        self.tick_size.setValue(0.01)
        self.requote = QDoubleSpinBox(); self.requote.setRange(0.05, 60.0); self.requote.setValue(1.0)
        self.vol_window = QSpinBox(); self.vol_window.setRange(2, 5000); self.vol_window.setValue(50)
        self.horizon_mode = QComboBox(); self.horizon_mode.addItems(["fixed", "rolling"])
        form.addRow("Gamma (risk aversion)", self.gamma)
        form.addRow("k (order-book liquidity)", self.k)
        form.addRow("Horizon", self.horizon)
        form.addRow("Order size", self.order_size)
        form.addRow("Tick size", self.tick_size)
        form.addRow("Requote interval", self.requote)
        form.addRow("Vol window", self.vol_window)
        form.addRow("Horizon mode", self.horizon_mode)

    def build(self):
        return lambda: AvellanedaStoikovStrategy(
            gamma=self.gamma.value(), k=self.k.value(), horizon=self.horizon.value(),
            order_size=self.order_size.value(), tick_size=self.tick_size.value(),
            requote_interval=self.requote.value(), vol_window=self.vol_window.value(),
            horizon_mode=self.horizon_mode.currentText())


class _HeatEqParams(QWidget):
    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        self.grid_half_width = QSpinBox(); self.grid_half_width.setRange(5, 500); self.grid_half_width.setValue(40)
        self.diffusion = QDoubleSpinBox(); self.diffusion.setRange(0.001, 5.0); self.diffusion.setValue(0.4)
        self.dt = QDoubleSpinBox(); self.dt.setRange(0.01, 10.0); self.dt.setValue(1.0)
        self.nudge_weight = QDoubleSpinBox(); self.nudge_weight.setRange(0.0, 1.0); self.nudge_weight.setValue(0.35)
        self.base_spread_ticks = QDoubleSpinBox(); self.base_spread_ticks.setRange(0.1, 200.0); self.base_spread_ticks.setValue(3.0)
        self.inventory_skew = QDoubleSpinBox(); self.inventory_skew.setDecimals(4); self.inventory_skew.setRange(0.0, 5.0)
        self.inventory_skew.setValue(0.05)
        self.order_size = QSpinBox(); self.order_size.setRange(1, 1000); self.order_size.setValue(5)
        self.tick_size = QDoubleSpinBox(); self.tick_size.setDecimals(4); self.tick_size.setRange(0.0001, 10.0)
        self.tick_size.setValue(0.01)
        self.requote = QDoubleSpinBox(); self.requote.setRange(0.05, 60.0); self.requote.setValue(1.0)
        form.addRow("Grid half-width", self.grid_half_width)
        form.addRow("Diffusion", self.diffusion)
        form.addRow("dt", self.dt)
        form.addRow("Nudge weight", self.nudge_weight)
        form.addRow("Base spread (ticks)", self.base_spread_ticks)
        form.addRow("Inventory skew", self.inventory_skew)
        form.addRow("Order size", self.order_size)
        form.addRow("Tick size", self.tick_size)
        form.addRow("Requote interval", self.requote)

    def build(self):
        return lambda: HeatEquationMarketMaker(
            grid_half_width=self.grid_half_width.value(), diffusion=self.diffusion.value(),
            dt=self.dt.value(), nudge_weight=self.nudge_weight.value(),
            base_spread_ticks=self.base_spread_ticks.value(), inventory_skew=self.inventory_skew.value(),
            order_size=self.order_size.value(), tick_size=self.tick_size.value(),
            requote_interval=self.requote.value())


class BacktestWindow(QMainWindow):
    def __init__(self, theme_mode="dark", parent=None):
        super().__init__(parent)
        self.theme_mode = theme_mode
        self.setWindowTitle("Backtester")
        self.resize(1080, 720)
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        left = QWidget()
        left.setFixedWidth(340)
        llay = QVBoxLayout(left)

        strat_box = QGroupBox("Strategy")
        slay = QVBoxLayout(strat_box)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Price-Level Bot", "Avellaneda-Stoikov", "Heat-Equation MM"])
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        slay.addWidget(self.strategy_combo)
        self.param_stack = QStackedWidget()
        self.p_price_level = _PriceLevelParams()
        self.p_avellaneda = _AvellanedaParams()
        self.p_heat = _HeatEqParams()
        self.param_stack.addWidget(self.p_price_level)
        self.param_stack.addWidget(self.p_avellaneda)
        self.param_stack.addWidget(self.p_heat)
        slay.addWidget(self.param_stack)
        llay.addWidget(strat_box)

        run_box = QGroupBox("Run settings")
        rform = QFormLayout(run_box)
        self.seed_spin = QSpinBox(); self.seed_spin.setRange(0, 999_999); self.seed_spin.setValue(7)
        self.taker_seed_spin = QSpinBox(); self.taker_seed_spin.setRange(0, 999_999); self.taker_seed_spin.setValue(11)
        self.max_steps_spin = QSpinBox(); self.max_steps_spin.setRange(10, 2_000_000); self.max_steps_spin.setValue(4000)
        self.mark_interval_spin = QDoubleSpinBox(); self.mark_interval_spin.setRange(0.1, 1000.0)
        self.mark_interval_spin.setValue(1.0)
        self.max_abs_pos_spin = QSpinBox(); self.max_abs_pos_spin.setRange(0, 1_000_000); self.max_abs_pos_spin.setValue(0)
        self.max_abs_pos_spin.setSpecialValueText("Unlimited")
        rform.addRow("Random seed", self.seed_spin)
        rform.addRow("Taker-flow seed", self.taker_seed_spin)
        rform.addRow("Max steps", self.max_steps_spin)
        rform.addRow("Mark interval", self.mark_interval_spin)
        rform.addRow("Max |position|", self.max_abs_pos_spin)
        llay.addWidget(run_box)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("\u25B6  Run backtest")
        self.run_btn.setObjectName("accent")
        self.run_btn.clicked.connect(self._on_run)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.stop_btn)
        llay.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        llay.addWidget(self.progress)
        self.progress_label = QLabel("Not started")
        llay.addWidget(self.progress_label)
        llay.addStretch(1)
        root.addWidget(left)

        # ---------------- right: results ----------------
        right = QWidget()
        rlay = QVBoxLayout(right)

        stats_frame = QFrame()
        grid = QGridLayout(stats_frame)
        grid.setSpacing(10)
        specs = ["Cash", "Position", "Avg Entry", "Realized PnL", "Unrealized PnL",
                 "Total PnL", "Num Fills", "Num Trades", "Num Steps"]
        self.stat_values = {}
        for i, name in enumerate(specs):
            card, val = metric_card(name)
            self.stat_values[name] = val
            grid.addWidget(card, i // 5, i % 5)
        rlay.addWidget(stats_frame)

        splitter = QSplitter(Qt.Vertical)
        self.equity_plot = pg.PlotWidget()
        self.equity_plot.showGrid(x=True, y=True, alpha=0.15)
        self.equity_plot.setLabel("bottom", "Simulated time")
        self.equity_plot.setLabel("left", "Equity")
        self.equity_curve = self.equity_plot.plot([], [], pen=pg.mkPen(PALETTE[self.theme_mode]["accent"], width=2))
        splitter.addWidget(self.equity_plot)

        self.trades_table = QTableWidget(0, 5)
        self.trades_table.setHorizontalHeaderLabels(["Time", "Price", "Qty", "Side", "Type"])
        self.trades_table.verticalHeader().setVisible(False)
        self.trades_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setAlternatingRowColors(True)
        splitter.addWidget(self.trades_table)
        splitter.setSizes([420, 260])

        rlay.addWidget(splitter, stretch=1)
        root.addWidget(right, stretch=1)

        self._on_strategy_changed(0)

    def _on_strategy_changed(self, idx):
        self.param_stack.setCurrentIndex(idx)

    def _on_run(self):
        idx = self.strategy_combo.currentIndex()
        factory = [self.p_price_level.build(), self.p_avellaneda.build(), self.p_heat.build()][idx]

        max_abs = self.max_abs_pos_spin.value()
        max_abs = None if max_abs == 0 else max_abs

        self.worker = BacktestWorker(
            strategy_factory=factory,
            seed=self.seed_spin.value(),
            taker_seed=self.taker_seed_spin.value(),
            mark_interval=self.mark_interval_spin.value(),
            max_steps=self.max_steps_spin.value(),
            max_time=None,
            max_abs_position=max_abs,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setValue(0)
        self.progress_label.setText("Running\u2026")
        self.worker.start()

    def _on_stop(self):
        if self.worker is not None:
            self.worker.stop()
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("Stopping\u2026")

    def _on_progress(self, steps_done, max_steps):
        if max_steps and max_steps > 0:
            pct = min(100, int(100 * steps_done / max_steps))
            self.progress.setValue(pct)
        self.progress_label.setText(f"{steps_done} steps simulated\u2026")

    def _on_failed(self, message):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText(f"Error: {message}")

    def _on_finished(self, result):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)
        self.progress_label.setText("Done")

        stats = result.final_stats
        self.stat_values["Cash"].setText(f"{stats['cash']:.2f}")
        self.stat_values["Position"].setText(f"{stats['position']:.0f}")
        self.stat_values["Avg Entry"].setText(f"{stats['avg_entry_price']:.2f}")
        for key, label in (("realized_pnl", "Realized PnL"), ("unrealized_pnl", "Unrealized PnL"),
                            ("total_pnl", "Total PnL")):
            v = stats[key]
            self.stat_values[label].setText(f"{v:+.2f}")
            self.stat_values[label].setProperty("pnl", "up" if v >= 0 else "down")
            self.stat_values[label].style().unpolish(self.stat_values[label])
            self.stat_values[label].style().polish(self.stat_values[label])
        self.stat_values["Num Fills"].setText(str(stats["num_fills"]))
        self.stat_values["Num Trades"].setText(str(stats["num_trades"]))
        self.stat_values["Num Steps"].setText(str(stats["num_steps"]))

        if result.equity_curve:
            xs = [p[0] for p in result.equity_curve]
            ys = [p[1] for p in result.equity_curve]
            self.equity_curve.setData(xs, ys)

        self.trades_table.setRowCount(0)
        pal = PALETTE[self.theme_mode]
        for fill in result.trades[-300:][::-1]:
            r = self.trades_table.rowCount()
            self.trades_table.insertRow(r)
            side_txt = fill.side.name
            vals = [f"{fill.timestamp:.2f}", f"{fill.trade_price:.2f}", f"{fill.quantity:.0f}",
                    side_txt, f"{fill.incoming_type.name}/{fill.resting_type.name}"]
            for c, text in enumerate(vals):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 3:
                    item.setForeground(QColor(pal["bid"] if side_txt == "BUY" else pal["ask"]))
                self.trades_table.setItem(r, c, item)

    def set_theme(self, theme_mode):
        self.theme_mode = theme_mode
        self.equity_curve.setPen(pg.mkPen(PALETTE[theme_mode]["accent"], width=2))
        self.equity_plot.setBackground(PALETTE[theme_mode]["chart_bg"])

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)
