import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.session import LiveSession, SimWorker
from app.orderbook_window import OrderbookWindow
from app.chart_window import ChartWindow
from app.backtester_window import BacktestWindow
from app.theme import apply_theme


def resource_path(relative):

    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class AppController:

    def __init__(self, app):
        self.app = app
        self.theme_mode = "dark"

        self.session = LiveSession(seed=42, taker_seed=43)
        self.worker = SimWorker(self.session)

        self.ob_window = OrderbookWindow(self.session, self.worker, theme_mode=self.theme_mode)
        self.ob_window.on_reset_callback = self._on_session_reset
        self.ob_window.theme_toggled.connect(self.set_theme)
        self.ob_window.open_charts_requested.connect(self.show_charts)
        self.ob_window.open_backtester_requested.connect(self.show_backtester)

        self.chart_window = None
        self.backtest_window = None

        apply_theme(self.app, self.theme_mode)

    def start(self):
        self.ob_window.show()

    def show_charts(self):
        if self.chart_window is None:
            self.chart_window = ChartWindow(self.worker, theme_mode=self.theme_mode)
        self.chart_window.show()
        self.chart_window.raise_()
        self.chart_window.activateWindow()

    def show_backtester(self):
        if self.backtest_window is None:
            self.backtest_window = BacktestWindow(theme_mode=self.theme_mode)
        self.backtest_window.show()
        self.backtest_window.raise_()
        self.backtest_window.activateWindow()

    def set_theme(self, mode):
        self.theme_mode = mode
        apply_theme(self.app, mode)
        self.ob_window.theme_mode = mode
        if self.chart_window is not None:
            self.chart_window.set_theme(mode)
        if self.backtest_window is not None:
            self.backtest_window.set_theme(mode)

    def _on_session_reset(self):
        if self.chart_window is not None:
            self.chart_window.clear()


def main():

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Order Book Simulator")
    app.setOrganizationName("OrderBookSim")

    icon_path = resource_path(os.path.join("..", "packaging", "icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    controller = AppController(app)
    controller.start()

    exit_code = app.exec()
    controller.worker.stop()
    controller.worker.set_paused(False)
    controller.worker.wait(2000)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
