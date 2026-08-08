import itertools
import math
import heapq
from enum import Enum
from dataclasses import dataclass
from typing import Any
import collections
from sortedcontainers import SortedDict
import time
import numpy

class Side(Enum):
    BUY = 1
    SELL = 2

class Type(Enum):
    SYSTEM = 1
    USER = 2

class OrderKind(Enum):
    LIMIT = 1
    MARKET = 2
class Event_update(Enum):
    TRADE = 1
    ORDERBOOK_UPD = 2
    ORDER_ACK = 3
    ORDER_CANCEL = 4
@dataclass
class Event:
    type: Event_update
    timestamp: float
    payload: Any = None

class EventBus:
    def __init__(self):
       self.subs = collections.defaultdict(list)
    def subscribe(self, event_type, callback):
        self.subs[event_type].append(callback)
    def publish(self, event_type, timestamp, payload = None):
        evt = Event(event_type, timestamp, payload)
        for cb in self.subs[event_type]:
            cb(evt)
class Order:
    def __init__(self, price, quantity, side, type, kind=OrderKind.LIMIT):
        self.price = price
        self.quantity = quantity
        self.side = side
        self.type = type
        self.kind = kind


class Fills:
    def __init__(self, trade_id, trade_price, timestamp, quantity, side, incoming_type, resting_type):
        self.timestamp = timestamp
        self.trade_price = trade_price
        self.quantity = quantity
        self.side = side
        self.incoming_type = incoming_type
        self.resting_type = resting_type
        self.trade_id = trade_id

class OrderBook:
    def __init__(self, event_bus = None, clock = None):
        self.buy_side = SortedDict()
        self.sell_side = SortedDict()
        self.order_by_id = {}
        self.all_ObyId = {}
        self.order_id_generator = itertools.count(1)
        self.trade_id_generator = itertools.count(1)
        self.trade_deque = collections.deque()
        self.bus = event_bus
        self.clock = clock
    def best_bid(self):
        return None if len(self.buy_side) == 0 else self.buy_side.peekitem(-1)[0]

    def best_ask(self):
        return None if len(self.sell_side) == 0 else self.sell_side.peekitem(0)[0]
    def depth_snapshot(self, levels =10):
        bids = list(self.buy_side.items())[-levels:][::-1]
        asks = list(self.sell_side.items())[:levels]
        return {
            "bids": [(price, sum(o.quantity for o in lvl)) for price, lvl in bids],
            "asks": [(price, sum(o.quantity for o in lvl)) for price, lvl in asks],
        }
    def add_lo(self, order):
        order.id = next(self.order_id_generator)
        self.all_ObyId[order.id] = order
        self.order_by_id[order.id] = order
        if order.side == Side.BUY:
            if self.best_ask() is not None and order.price >= self.best_ask():
                self.match_eng(order)
            if order.quantity > 0:
                if order.price in self.buy_side:
                    self.buy_side[order.price].append(order)
                else:
                    exist_deq = collections.deque()
                    exist_deq.append(order)
                    self.buy_side[order.price] = exist_deq
        else:
            if self.best_bid() is not None and order.price <= self.best_bid():
                self.match_eng(order)
            if order.quantity > 0:
                if order.price in self.sell_side:
                    self.sell_side[order.price].append(order)
                else:
                    exist_deq = collections.deque()
                    exist_deq.append(order)
                    self.sell_side[order.price] = exist_deq
        order.timestamp = self.clock.now() if self.clock is not None else time.perf_counter() * 1000
        if self.bus is not None:
            self.bus.publish(Event_update.ORDER_ACK, order.timestamp, order)
    def add_mo(self, order):
        order.id = next(self.order_id_generator)
        order.kind = OrderKind.MARKET
        self.all_ObyId[order.id] = order
        self.order_by_id[order.id] = order

        if order.side == Side.BUY:
            order.price = float('inf')
            if self.best_ask() is not None:
                self.match_eng(order)
        else:
            order.price = float('-inf')
            if self.best_bid() is not None:
                self.match_eng(order)

        order.timestamp = self.clock.now() if self.clock is not None else time.perf_counter() * 1000

        if order.quantity > 0:
            self.order_by_id.pop(order.id, None)

        if self.bus is not None:
            self.bus.publish(Event_update.ORDER_ACK, order.timestamp, order)

        return order

    def cancel_lo(self, order_id):
        if order_id not in self.order_by_id:
            return False
        order = self.order_by_id[order_id]
        if order.side == Side.BUY:
            self.buy_side[order.price].remove(order)
            if len(self.buy_side[order.price]) == 0:
                del self.buy_side[order.price]
        else:
            self.sell_side[order.price].remove(order)
            if len(self.sell_side[order.price]) == 0:
                del self.sell_side[order.price]
        del self.order_by_id[order_id]

        now = self.clock.now() if self.clock is not None else time.perf_counter() * 1000
        if self.bus is not None:
            self.bus.publish(Event_update.ORDER_CANCEL, now, order)
            self.bus.publish(Event_update.ORDERBOOK_UPD, now, self.depth_snapshot())
        return True

    def match_eng(self, order):
        now = self.clock.now() if self.clock is not None else time.perf_counter() * 1000
        if order.side == Side.BUY:
            resting = self.sell_side[self.best_ask()][0]
            if resting.quantity >= order.quantity:
                resting.quantity -= order.quantity
                fill = Fills(next(self.trade_id_generator), self.best_ask(), now, order.quantity, Side.BUY,
                          order.type, resting.type)
                self.trade_deque.append(fill)
                if self.bus is not None:
                    self.bus.publish(Event_update.TRADE, fill.timestamp, fill)
                order.quantity = 0
                del self.order_by_id[order.id]
                if resting.quantity == 0:
                    del self.order_by_id[resting.id]
                    self.sell_side[self.best_ask()].remove(resting)
                    if len(self.sell_side[self.best_ask()]) == 0:
                        del self.sell_side[self.best_ask()]
                if self.bus is not None:
                    self.bus.publish(Event_update.ORDERBOOK_UPD, now, self.depth_snapshot())
            else:
                order.quantity -= resting.quantity
                fill = Fills(next(self.trade_id_generator), self.best_ask(), now, resting.quantity, Side.BUY,
                                          order.type, resting.type)
                self.trade_deque.append(fill)
                if self.bus is not None:
                    self.bus.publish(Event_update.TRADE, fill.timestamp, fill)
                del self.order_by_id[resting.id]
                self.sell_side[self.best_ask()].remove(resting)
                if len(self.sell_side[self.best_ask()]) == 0:
                    del self.sell_side[self.best_ask()]
                if self.best_ask() is not None and order.price >= self.best_ask():
                    self.match_eng(order)
                else:
                    if self.bus is not None:
                        self.bus.publish(Event_update.ORDERBOOK_UPD, now, self.depth_snapshot())
        else:
            resting = self.buy_side[self.best_bid()][0]
            if resting.quantity >= order.quantity:
                resting.quantity -= order.quantity
                fill = Fills(next(self.trade_id_generator), self.best_bid(), now, order.quantity, Side.SELL,
                                          order.type, resting.type)
                self.trade_deque.append(fill)
                if self.bus is not None:
                    self.bus.publish(Event_update.TRADE, fill.timestamp, fill)
                order.quantity = 0
                del self.order_by_id[order.id]
                if resting.quantity == 0:
                    del self.order_by_id[resting.id]
                    self.buy_side[self.best_bid()].remove(resting)
                    if len(self.buy_side[self.best_bid()]) == 0:
                        del self.buy_side[self.best_bid()]
                if self.bus is not None:
                    self.bus.publish(Event_update.ORDERBOOK_UPD, now, self.depth_snapshot())
            else:
                order.quantity -= resting.quantity
                fill = Fills(next(self.trade_id_generator), self.best_bid(), now, resting.quantity, Side.SELL,
                                          order.type, resting.type)
                self.trade_deque.append(fill)
                if self.bus is not None:
                    self.bus.publish(Event_update.TRADE, fill.timestamp, fill)
                del self.order_by_id[resting.id]
                self.buy_side[self.best_bid()].remove(resting)
                if len(self.buy_side[self.best_bid()]) == 0:
                    del self.buy_side[self.best_bid()]
                if self.best_bid() is not None and order.price <= self.best_bid():
                    self.match_eng(order)
                else:
                    if self.bus is not None:
                        self.bus.publish(Event_update.ORDERBOOK_UPD, now, self.depth_snapshot())

action = ["buy_add", "sell_add", "buy_can", "sell_can"]


class sim_engine:
    def __init__(self, orderbook, buy_add = None, sell_add = None, buy_can = None, sell_can = None,
                 price_offset_p = 0.3, size_mean = 3.0, size_sigma = 1.0,
                 cancel_epsilon = 1.0, tick_size = 0.01, fallback_price = 100.0, seed = None, clock = None):
        self.buy_add = buy_add if buy_add is not None else [0.0075, 0.01, 0.01]
        self.sell_add = sell_add if sell_add is not None else [0.0075, 0.01, 0.01]
        self.buy_can = buy_can if buy_can is not None else [0.0325, 0.05, 0.001]
        self.sell_can = sell_can if sell_can is not None else [0.0325, 0.05, 0.001]

        self.price_offset_p = price_offset_p
        self.size_mean = size_mean
        self.size_sigma = size_sigma
        self.cancel_epsilon = cancel_epsilon
        self.tick_size = tick_size
        self.fallback_price = fallback_price
        self.clock = clock
        self.buy_state = 0.0
        self.sell_state = 0.0
        self.cancelbuy_state = 0.0
        self.cancelsell_state = 0.0
        self.t_last = 0.0
        self.book = orderbook
        self.rng = numpy.random.default_rng(seed)

        self.dispatch = {
            "buy_add": self.fire_buy_add,
            "sell_add": self.fire_sell_add,
            "buy_can": self.fire_buy_can,
            "sell_can": self.fire_sell_can,
        }

    def current_state(self, t_now):
        eve_time = t_now - self.t_last
        buy_int = self.buy_add[2] + self.buy_state * math.exp(-self.buy_add[1] * eve_time)
        buycan_int = self.buy_can[2] + self.cancelbuy_state * math.exp(-self.buy_can[1] * eve_time)
        sell_int = self.sell_add[2] + self.sell_state * math.exp(-self.sell_add[1] * eve_time)
        sellcan_int = self.sell_can[2] + self.cancelsell_state * math.exp(-self.sell_can[1] * eve_time)
        return buy_int, sell_int, buycan_int, sellcan_int

    def max_int(self, t_now):
        return sum(self.current_state(t_now))

    def prop_time(self, t_now):
        ceiling = self.max_int(t_now)
        u = self.rng.exponential(1.0 / ceiling)
        return u + t_now, ceiling

    def thinning(self, t_now):
        current = t_now
        while True:
            candidate, ceiling = self.prop_time(current)
            true_ints = self.current_state(candidate)
            tru_total = sum(true_ints)
            r = self.rng.uniform(0.0, ceiling)
            if tru_total > r:
                return self.accept(candidate, true_ints)
            else:
                current = candidate

    def accept(self, candidate, tru_ints):
        tru_prob = numpy.array(tru_ints) / sum(tru_ints)
        idx = self.rng.choice(4, p=tru_prob)
        fired_type = action[idx]
        self.dispatch[fired_type](candidate)
        return candidate, fired_type

    def update_state(self, candidate, fired_state_attr, alpha):
        elapsed = candidate - self.t_last
        self.buy_state *= math.exp(-self.buy_add[1] * elapsed)
        self.sell_state *= math.exp(-self.sell_add[1] * elapsed)
        self.cancelsell_state *= math.exp(-self.sell_can[1] * elapsed)
        self.cancelbuy_state *= math.exp(-self.buy_can[1] * elapsed)
        setattr(self, fired_state_attr, getattr(self, fired_state_attr) + alpha)
        self.t_last = candidate

    def price_sample(self, side):
        best = self.book.best_bid() if side == Side.BUY else self.book.best_ask()
        if best is None:
            best = self.fallback_price
        ticks_away = self.rng.geometric(p=self.price_offset_p) - 1
        direction = -1 if side == Side.BUY else 1
        return round(best + direction * ticks_away * self.tick_size, 2)

    def size_sample(self):
        return max(1, int(self.rng.lognormal(mean=self.size_mean, sigma=self.size_sigma)))

    def pick_cancel_target(self, side):
        book_side = self.book.buy_side if side == Side.BUY else self.book.sell_side
        if len(book_side) == 0:
            return None
        orders = [o for deq in book_side.values() for o in deq]
        touch = self.book.best_bid() if side == Side.BUY else self.book.best_ask()
        distances = [abs(round((o.price - touch) / self.tick_size)) for o in orders]
        weights = numpy.array([d + self.cancel_epsilon for d in distances], dtype=float)
        probs = weights / weights.sum()
        idx = self.rng.choice(len(orders), p=probs)
        return orders[idx]

    def fire_buy_add(self, candidate):
        self.update_state(candidate, "buy_state", self.buy_add[0])
        price = self.price_sample(Side.BUY)
        size = self.size_sample()
        self.book.add_lo(Order(price, size, Side.BUY, Type.SYSTEM))

    def fire_sell_add(self, candidate):
        self.update_state(candidate, "sell_state", self.sell_add[0])
        price = self.price_sample(Side.SELL)
        size = self.size_sample()
        self.book.add_lo(Order(price, size, Side.SELL, Type.SYSTEM))

    def fire_buy_can(self, candidate):
        target = self.pick_cancel_target(Side.BUY)
        if target is None:
            return
        self.update_state(candidate, "cancelbuy_state", self.buy_can[0])
        self.book.cancel_lo(target.id)

    def fire_sell_can(self, candidate):
        target = self.pick_cancel_target(Side.SELL)
        if target is None:
            return
        self.update_state(candidate, "cancelsell_state", self.sell_can[0])
        self.book.cancel_lo(target.id)
class Mode_type(Enum):
    generative = 1
    replay = 2
class Clock:
    def __init__(self, mode_type):
        self.t = 0.0
        self.schedule = []
        self.tie_break = itertools.count(0)
        self.mode_flag = mode_type
        self.generator_fn = None
        self.replay_log = []
        self.replay_idx = 0
    def now(self):
        return self.t
    def set_generator(self, fn):
        self.generator_fn = fn
    def load_replay_log(self, entries):
        self.replay_log = sorted(entries, key=lambda e: e[0])
        self.replay_idx = 0
    def fire_scheduled_if_due(self, cutoff_time):
        fired = False
        while self.schedule and self.schedule[0][0] <= cutoff_time:
            fire_time, _, callback = heapq.heappop(self.schedule)
            self.t = max(self.t, fire_time)
            callback(self.t)
            fired = True
        return fired
    def next_scheduled_time(self):
        return self.schedule[0][0] if self.schedule else None
    def advance_generative(self):
        next_sched = self.next_scheduled_time()

        if next_sched is not None and next_sched <= self.t:
            self.fire_scheduled_if_due(self.t)
            return("scheduled", next_sched)
        if self.generator_fn is None:
            if next_sched is None:
                return None
            self.fire_scheduled_if_due(next_sched)
            return("scheduled", next_sched)
        candidate_time, payload = self.generator_fn(self.t)
        self.t = candidate_time
        return("market", payload)
    def advance_replay(self):
        next_sched = self.next_scheduled_time()

        if self.replay_idx >= len(self.replay_log):
            if next_sched is None:
                return None
            self.fire_scheduled_if_due(next_sched)
            return("scheduled", next_sched)
        entry_time, apply_fn, payload = self.replay_log[self.replay_idx]
        if next_sched is not None and next_sched < entry_time:
            self.fire_scheduled_if_due(next_sched)
            return("scheduled", next_sched)

        self.t = entry_time
        apply_fn(entry_time, payload)
        self.replay_idx +=1
        return("market", payload)

    def advance(self):
        if self.mode_flag == Mode_type.generative:
            return self.advance_generative()
        return self.advance_replay()

    def has_more(self):
        if self.schedule:
            return True
        if self.mode_flag == Mode_type.generative:
            return self.generator_fn is not None
        return self.replay_idx < len(self.replay_log)

class ActionKind(Enum):
    PLACE_LIMIT = 1
    PLACE_MARKET = 2
    CANCEL = 3


@dataclass
class StrategyAction:
    kind: ActionKind
    side: Side = None
    price: float = None
    quantity: float = None
    order_id: int = None


class StrategyBase:

    def __init__(self, name="strategy"):
        self.name = name
        self.book = None
        self.pnl = None
        self.my_order_ids = set()
        self._quote_state = {}
        self._quote_ids = {}
        self._pending_slots = collections.deque()

    def attach(self, book, pnl_tracker):
        self.book = book
        self.pnl = pnl_tracker

    def on_start(self):
        pass

    def on_tick(self, t):
        return []

    def on_order_ack(self, order):
        if order.quantity > 0:
            self.my_order_ids.add(order.id)
        if self._pending_slots:
            slot = self._pending_slots.popleft()
            if order.quantity > 0:
                self._quote_ids[slot] = order.id
            else:
                self._quote_ids.pop(slot, None)
                self._quote_state.pop(slot, None)

    def on_fill(self, fill):
        pass

    def cancel_all_action(self):
        acts = [StrategyAction(ActionKind.CANCEL, order_id=oid) for oid in self.my_order_ids]
        self.my_order_ids = set()
        self._quote_state = {}
        self._quote_ids = {}
        return acts

    def quote_two_sided(self, bid_price, ask_price, bid_size, ask_size):
        actions = []
        for slot, side, price, size in (("bid", Side.BUY, bid_price, bid_size),
                                         ("ask", Side.SELL, ask_price, ask_size)):
            desired = (price, size)
            if self._quote_state.get(slot) == desired:
                continue
            old_id = self._quote_ids.get(slot)
            if old_id is not None:
                actions.append(StrategyAction(ActionKind.CANCEL, order_id=old_id))
                self.my_order_ids.discard(old_id)
                self._quote_ids.pop(slot, None)
            actions.append(StrategyAction(ActionKind.PLACE_LIMIT, side, price, size))
            self._pending_slots.append(slot)
            self._quote_state[slot] = desired
        return actions

    def mid_price(self, fallback=None):
        bb, ba = self.book.best_bid(), self.book.best_ask()
        if bb is None and ba is None:
            return fallback
        if bb is None:
            return ba
        if ba is None:
            return bb
        return (bb + ba) / 2.0


class PnLTracker:

    def __init__(self, event_bus, track_type=Type.USER, starting_cash=0.0):
        self.bus = event_bus
        self.track_type = track_type
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.realized_pnl = 0.0
        self.mark_price = None
        self.fills = []
        self.equity_history = []
        if self.bus is not None:
            self.bus.subscribe(Event_update.TRADE, self._on_trade)

    def _on_trade(self, event):
        fill = event.payload
        is_incoming_ours = fill.incoming_type == self.track_type
        is_resting_ours = fill.resting_type == self.track_type
        if not (is_incoming_ours or is_resting_ours):
            return
        if is_incoming_ours:
            signed_qty = fill.quantity if fill.side == Side.BUY else -fill.quantity
            self._apply_fill(signed_qty, fill.trade_price)
        if is_resting_ours:
            signed_qty = -fill.quantity if fill.side == Side.BUY else fill.quantity
            self._apply_fill(signed_qty, fill.trade_price)
        self.fills.append(fill)

    def _apply_fill(self, signed_qty, price):
        self.cash -= signed_qty * price
        same_direction = self.position == 0 or (self.position > 0) == (signed_qty > 0)
        if same_direction:
            new_pos = self.position + signed_qty
            if new_pos != 0:
                self.avg_entry_price = (self.avg_entry_price * self.position + price * signed_qty) / new_pos
            self.position = new_pos
        else:
            closing_qty = min(abs(signed_qty), abs(self.position))
            direction = 1 if self.position > 0 else -1
            self.realized_pnl += closing_qty * (price - self.avg_entry_price) * direction
            self.position += signed_qty
            if self.position == 0:
                self.avg_entry_price = 0.0
            elif (self.position > 0) != (direction > 0):
                self.avg_entry_price = price

    def unrealized_pnl(self, mark_price=None):
        mp = mark_price if mark_price is not None else self.mark_price
        if mp is None or self.position == 0:
            return 0.0
        return self.position * (mp - self.avg_entry_price)

    def equity(self, mark_price=None):
        mp = mark_price if mark_price is not None else self.mark_price
        if mp is None:
            mp = self.avg_entry_price
        return self.cash + self.position * mp

    def mark_to_market(self, mark_price, t=None):
        self.mark_price = mark_price
        eq = self.equity(mark_price)
        self.equity_history.append((t, eq, self.position, self.cash))
        return eq

    def summary(self):
        mp = self.mark_price if self.mark_price is not None else self.avg_entry_price
        return {
            "cash": self.cash,
            "position": self.position,
            "avg_entry_price": self.avg_entry_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl(mp),
            "total_pnl": self.equity(mp) - self.starting_cash,
            "num_fills": len(self.fills),
        }


class BacktestResult:
    def __init__(self):
        self.equity_curve = []
        self.trades = []
        self.num_steps = 0
        self.final_stats = {}


class Backtester:

    def __init__(self, book, clock, bus, strategy, pnl_tracker=None,
                 mark_interval=1.0, max_steps=None, max_time=None,
                 max_abs_position=None):
        self.book = book
        self.clock = clock
        self.bus = bus
        self.strategy = strategy
        self.pnl = pnl_tracker if pnl_tracker is not None else PnLTracker(bus, track_type=Type.USER)
        self.strategy.attach(book, self.pnl)
        self.mark_interval = mark_interval
        self.max_steps = max_steps
        self.max_time = max_time
        self.max_abs_position = max_abs_position
        self.result = BacktestResult()
        self._last_mark_t = 0.0
        self._trade_ids_seen = set()
        self.bus.subscribe(Event_update.TRADE, self._on_trade)

    def _on_trade(self, event):
        fill = event.payload
        if fill.trade_id in self._trade_ids_seen:
            return
        self._trade_ids_seen.add(fill.trade_id)
        if fill.incoming_type == Type.USER or fill.resting_type == Type.USER:
            self.result.trades.append(fill)
            self.strategy.on_fill(fill)

    def _execute_actions(self, actions):
        for act in actions:
            if act.kind == ActionKind.PLACE_LIMIT:
                if self.max_abs_position is not None:
                    projected = self.pnl.position + (act.quantity if act.side == Side.BUY else -act.quantity)
                    if abs(projected) > self.max_abs_position:
                        continue
                o = Order(act.price, act.quantity, act.side, Type.USER, OrderKind.LIMIT)
                self.book.add_lo(o)
                self.strategy.on_order_ack(o)
            elif act.kind == ActionKind.PLACE_MARKET:
                o = Order(None, act.quantity, act.side, Type.USER, OrderKind.MARKET)
                self.book.add_mo(o)
                self.strategy.on_order_ack(o)
            elif act.kind == ActionKind.CANCEL:
                if act.order_id is not None:
                    self.book.cancel_lo(act.order_id)

    def step(self):
        advanced = self.clock.advance()
        if advanced is None:
            return False
        t = self.clock.now()
        actions = self.strategy.on_tick(t)
        if actions:
            self._execute_actions(actions)
        if t - self._last_mark_t >= self.mark_interval or not self.result.equity_curve:
            mid = self.strategy.mid_price()
            if mid is not None:
                self.pnl.mark_to_market(mid, t)
                self.result.equity_curve.append((t, self.pnl.equity(mid), self.pnl.position, self.pnl.cash))
            self._last_mark_t = t
        self.result.num_steps += 1
        return True

    def run(self):
        self.strategy.on_start()
        while self.clock.has_more():
            if self.max_steps is not None and self.result.num_steps >= self.max_steps:
                break
            if self.max_time is not None and self.clock.now() >= self.max_time:
                break
            if not self.step():
                break
        mid = self.strategy.mid_price()
        if mid is not None:
            self.pnl.mark_to_market(mid, self.clock.now())
        self.result.final_stats = self.pnl.summary()
        self.result.final_stats["num_steps"] = self.result.num_steps
        self.result.final_stats["num_trades"] = len(self.result.trades)
        return self.result

class PriceLevelBotStrategy(StrategyBase):

    def __init__(self, spread_ticks=4, order_size=5, tick_size=0.01,
                 requote_interval=1.0, name="price_level_bot"):
        super().__init__(name)
        self.spread_ticks = spread_ticks
        self.order_size = order_size
        self.tick_size = tick_size
        self.requote_interval = requote_interval
        self._last_quote_t = -math.inf

    def on_tick(self, t):
        if t - self._last_quote_t < self.requote_interval:
            return []
        mid = self.mid_price()
        if mid is None:
            return []
        self._last_quote_t = t
        half = (self.spread_ticks / 2.0) * self.tick_size
        bid_px = round(mid - half, 2)
        ask_px = round(mid + half, 2)
        return self.quote_two_sided(bid_px, ask_px, self.order_size, self.order_size)


class AvellanedaStoikovStrategy(StrategyBase):
    def __init__(self, gamma=1.5, k=100.0, horizon=200.0, order_size=5,
                 tick_size=0.01, requote_interval=1.0, vol_window=50,
                 horizon_mode="fixed", session_length=None,
                 name="avellaneda_stoikov"):
        super().__init__(name)
        self.gamma = gamma
        self.k = k
        self.horizon = horizon
        self.order_size = order_size
        self.tick_size = tick_size
        self.requote_interval = requote_interval
        assert horizon_mode in ("fixed", "rolling")
        self.horizon_mode = horizon_mode
        self.session_length = session_length if session_length is not None else horizon
        self._last_quote_t = -math.inf
        self._mid_history = collections.deque(maxlen=vol_window)
        self._t0 = None
        self._session_start = None

    def _sigma(self):
        if len(self._mid_history) < 2:
            return 0.0
        rets = numpy.diff(numpy.array(self._mid_history))
        if len(rets) == 0:
            return 0.0
        return float(numpy.std(rets)) if len(rets) > 1 else 0.0

    def _time_left(self, t):
        if self.horizon_mode == "fixed":
            return max(self.horizon - (t - self._t0), 0.0)
        elapsed_in_session = t - self._session_start
        if elapsed_in_session >= self.session_length:
            sessions_passed = math.floor(elapsed_in_session / self.session_length)
            self._session_start += sessions_passed * self.session_length
            elapsed_in_session = t - self._session_start
        return max(self.horizon - elapsed_in_session, 0.0)

    def on_tick(self, t):
        mid = self.mid_price()
        if mid is None:
            return []
        self._mid_history.append(mid)
        if self._t0 is None:
            self._t0 = t
            self._session_start = t
        if t - self._last_quote_t < self.requote_interval:
            return []
        self._last_quote_t = t

        sigma = self._sigma()
        time_left = self._time_left(t)
        q = self.pnl.position if self.pnl is not None else 0.0

        reservation = mid - q * self.gamma * (sigma ** 2) * time_left
        spread = self.gamma * (sigma ** 2) * time_left + (2.0 / self.gamma) * math.log(1.0 + self.gamma / self.k)
        spread = max(spread, self.tick_size)

        bid_px = round(reservation - spread / 2.0, 2)
        ask_px = round(reservation + spread / 2.0, 2)
        best_bid, best_ask = self.book.best_bid(), self.book.best_ask()
        if best_ask is not None:
            bid_px = min(bid_px, best_ask - self.tick_size)
        if best_bid is not None:
            ask_px = max(ask_px, best_bid + self.tick_size)
        if bid_px >= ask_px:
            ask_px = bid_px + self.tick_size

        return self.quote_two_sided(bid_px, ask_px, self.order_size, self.order_size)


class HeatEquationMarketMaker(StrategyBase):
    def __init__(self, grid_half_width=40, diffusion=0.4, dt=1.0,
                 nudge_weight=0.35, base_spread_ticks=3, inventory_skew=0.05,
                 order_size=5, tick_size=0.01, requote_interval=1.0,
                 name="heat_equation_mm"):
        super().__init__(name)
        self.grid_half_width = grid_half_width
        self.grid_n = 2 * grid_half_width + 1
        self.diffusion = diffusion
        self.dt = dt
        self.nudge_weight = nudge_weight
        self.base_spread_ticks = base_spread_ticks
        self.inventory_skew = inventory_skew
        self.order_size = order_size
        self.tick_size = tick_size
        self.requote_interval = requote_interval
        self._last_quote_t = -math.inf
        self.center_price = None
        self.density = None

    def _init_density(self, mid):
        self.center_price = mid
        self.density = numpy.zeros(self.grid_n)
        self.density[self.grid_n // 2] = 1.0

    def _reindex_if_needed(self, mid):
        offset_ticks = int(round((mid - self.center_price) / self.tick_size))
        if abs(offset_ticks) > self.grid_half_width // 2:
            shifted = numpy.roll(self.density, -offset_ticks)
            if offset_ticks > 0:
                shifted[-offset_ticks:] = 0.0
            elif offset_ticks < 0:
                shifted[:-offset_ticks] = 0.0
            total = shifted.sum()
            self.density = shifted / total if total > 0 else self.density
            self.center_price = self.center_price + offset_ticks * self.tick_size

    def _nudge(self, mid):
        idx = int(round((mid - self.center_price) / self.tick_size)) + self.grid_n // 2
        idx = min(max(idx, 0), self.grid_n - 1)
        bump = numpy.zeros(self.grid_n)
        bump[idx] = 1.0
        self.density = (1 - self.nudge_weight) * self.density + self.nudge_weight * bump

    def _diffuse(self):
        u = self.density
        lap = numpy.zeros_like(u)
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        lap[0] = u[1] - u[0]
        lap[-1] = u[-2] - u[-1]
        u_new = u + self.diffusion * self.dt * lap
        u_new = numpy.clip(u_new, 0.0, None)
        total = u_new.sum()
        self.density = u_new / total if total > 0 else u_new

    def _fair_value_and_spread(self):
        idx = numpy.arange(self.grid_n)
        offsets = (idx - self.grid_n // 2) * self.tick_size
        fv = self.center_price + float(numpy.sum(self.density * offsets))
        variance = float(numpy.sum(self.density * (offsets - (fv - self.center_price)) ** 2))
        local_vol = math.sqrt(max(variance, 0.0))
        return fv, local_vol

    def on_tick(self, t):
        mid = self.mid_price()
        if mid is None:
            return []
        if self.density is None:
            self._init_density(mid)
        else:
            self._reindex_if_needed(mid)
            self._nudge(mid)
            self._diffuse()

        if t - self._last_quote_t < self.requote_interval:
            return []
        self._last_quote_t = t

        fair_value, local_vol = self._fair_value_and_spread()
        q = self.pnl.position if self.pnl is not None else 0.0
        skew = -self.inventory_skew * q * self.tick_size
        half_spread = max(self.base_spread_ticks * self.tick_size / 2.0, local_vol)

        bid_px = round(fair_value + skew - half_spread, 2)
        ask_px = round(fair_value + skew + half_spread, 2)
        best_bid, best_ask = self.book.best_bid(), self.book.best_ask()
        if best_ask is not None:
            bid_px = min(bid_px, best_ask - self.tick_size)
        if best_bid is not None:
            ask_px = max(ask_px, best_bid + self.tick_size)
        if bid_px >= ask_px:
            ask_px = bid_px + self.tick_size

        return self.quote_two_sided(bid_px, ask_px, self.order_size, self.order_size)

class TakerFlowGenerator:
    def __init__(self, book, clock, rate=0.02, size_mean=2.0, size_sigma=0.6,
                 side_bias=0.5, seed=None):
        self.book = book
        self.clock = clock
        self.rate = rate
        self.size_mean = size_mean
        self.size_sigma = size_sigma
        self.side_bias = side_bias
        self.rng = numpy.random.default_rng(seed)

    def start(self):
        self._schedule_next(self.clock.now())

    def _schedule_next(self, t_now):
        dt = self.rng.exponential(1.0 / self.rate)
        fire_time = t_now + dt
        heapq.heappush(self.clock.schedule, (fire_time, next(self.clock.tie_break), self._fire))

    def _fire(self, t_now):
        side = Side.BUY if self.rng.uniform() < self.side_bias else Side.SELL
        size = max(1, int(self.rng.lognormal(mean=self.size_mean, sigma=self.size_sigma)))
        has_liquidity = (side == Side.BUY and self.book.best_ask() is not None) or \
                        (side == Side.SELL and self.book.best_bid() is not None)
        if has_liquidity:
            self.book.add_mo(Order(None, size, side, Type.SYSTEM, OrderKind.MARKET))
        self._schedule_next(t_now)
