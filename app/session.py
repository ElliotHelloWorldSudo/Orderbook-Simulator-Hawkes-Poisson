import time

from PySide6.QtCore import QThread, Signal

from engine import (
    Side, Type, OrderKind, Event_update, Order, OrderBook, sim_engine,
    TakerFlowGenerator, Clock, Mode_type, EventBus, PnLTracker,
    ActionKind, StrategyBase,
)


def execute_actions(book, pnl, strategy, actions, max_abs_position=None):

    for act in actions:
        if act.kind == ActionKind.PLACE_LIMIT:
            if max_abs_position is not None:
                projected = pnl.position + (act.quantity if act.side == Side.BUY else -act.quantity)
                if abs(projected) > max_abs_position:
                    continue
            o = Order(act.price, act.quantity, act.side, Type.USER, OrderKind.LIMIT)
            book.add_lo(o)
            strategy.on_order_ack(o)
        elif act.kind == ActionKind.PLACE_MARKET:
            o = Order(None, act.quantity, act.side, Type.USER, OrderKind.MARKET)
            book.add_mo(o)
            strategy.on_order_ack(o)
        elif act.kind == ActionKind.CANCEL:
            if act.order_id is not None:
                book.cancel_lo(act.order_id)


class LiveSession:

    def __init__(self, seed=42, taker_seed=43, fallback_price=100.0, tick_size=0.01):
        self.bus = EventBus()
        self.clock = Clock(Mode_type.generative)
        self.book = OrderBook(event_bus=self.bus, clock=self.clock)
        self.market = sim_engine(self.book, clock=self.clock, seed=seed,
                                  fallback_price=fallback_price, tick_size=tick_size)
        self.clock.set_generator(self.market.thinning)
        self.taker_flow = TakerFlowGenerator(self.book, self.clock, seed=taker_seed)
        self.taker_flow.start()
        self.pnl = PnLTracker(self.bus, track_type=Type.USER)
        self.strategy = None
        self._trade_ids_seen = set()

    def attach_strategy(self, strategy: StrategyBase):
        strategy.attach(self.book, self.pnl)
        strategy.on_start()
        self.strategy = strategy

    def detach_strategy(self):
        if self.strategy is None:
            return
        actions = self.strategy.cancel_all_action()
        execute_actions(self.book, self.pnl, self.strategy, actions)
        self.strategy = None

    def reset(self, seed=None, taker_seed=None, fallback_price=100.0, tick_size=0.01):
        self.bus = EventBus()
        self.clock = Clock(Mode_type.generative)
        self.book = OrderBook(event_bus=self.bus, clock=self.clock)
        self.market = sim_engine(self.book, clock=self.clock, seed=seed,
                                  fallback_price=fallback_price, tick_size=tick_size)
        self.clock.set_generator(self.market.thinning)
        self.taker_flow = TakerFlowGenerator(self.book, self.clock, seed=taker_seed)
        self.taker_flow.start()
        self.pnl = PnLTracker(self.bus, track_type=Type.USER)
        self.strategy = None
        self._trade_ids_seen = set()

    def new_trades(self):
        out = []
        for fill in self.book.trade_deque:
            if fill.trade_id not in self._trade_ids_seen:
                self._trade_ids_seen.add(fill.trade_id)
                out.append(fill)
        return out


class SimWorker(QThread):

    market_update = Signal(dict)
    trade_occurred = Signal(object)

    def __init__(self, session: LiveSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._stop = False
        self._paused = False
        self.speed_ms = 12
        self._events_since_emit = 0
        self._emit_every = 1

        self.session.bus.subscribe(Event_update.TRADE, self._on_trade)

    def resubscribe(self):
        self.session.bus.subscribe(Event_update.TRADE, self._on_trade)

    def _on_trade(self, event):
        self.trade_occurred.emit(event.payload)

    def set_speed_ms(self, ms: int):
        self.speed_ms = max(0, ms)

    def set_paused(self, paused: bool):
        self._paused = paused

    def stop(self):
        self._stop = True

    def run(self):
        session = self.session
        while not self._stop:
            if self._paused:
                self.msleep(60)
                continue
            advanced = session.clock.advance()
            if advanced is None:
                self.msleep(30)
                continue

            t = session.clock.now()

            if session.strategy is not None:
                try:
                    actions = session.strategy.on_tick(t)
                    if actions:
                        execute_actions(session.book, session.pnl, session.strategy, actions)
                except Exception:
                    pass

            best_bid, best_ask = session.book.best_bid(), session.book.best_ask()
            mid = None
            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2.0
            elif best_bid is not None:
                mid = best_bid
            elif best_ask is not None:
                mid = best_ask

            if mid is not None:
                session.pnl.mark_to_market(mid, t)

            self._events_since_emit += 1
            if self._events_since_emit >= self._emit_every:
                self._events_since_emit = 0
                payload = {
                    "t": t,
                    "mid": mid,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None,
                    "book": session.book.depth_snapshot(levels=15),
                    "pnl": session.pnl.summary(),
                }
                self.market_update.emit(payload)

            if self.speed_ms:
                self.msleep(self.speed_ms)
