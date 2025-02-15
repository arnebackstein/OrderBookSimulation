import heapq
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, NamedTuple


@dataclass
class Order:
    order_id: int
    side: str
    price: float
    quantity: int
    order_type: str
    timestamp: float
    participant_name: str

    def __lt__(self, other):

        return self.timestamp < other.timestamp

    def __repr__(self):
        return f"Order({self.order_id}, {self.side}, {self.price}, {self.quantity}, {self.order_type}, {self.participant_name})"


class Trade(NamedTuple):
    timestamp: float
    price: float
    quantity: int
    side: str


class OrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []
        self.order_map = {}
        self.trades: List[Trade] = []
        self.next_order_id = 1
        self.last_trade_price = 100.0

    def add_order_api(
        self,
        side: str,
        price: float,
        quantity: int,
        order_type: str,
        participant_name: str,
    ) -> Tuple[bool, Optional[int]]:
        """Universal API for adding orders to the book"""
        order_id = self.next_order_id
        self.next_order_id += 1

        order = Order(
            order_id=order_id,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            timestamp=time.time(),
            participant_name=participant_name,
        )

        success = self.add_order(order)
        return success, order_id if success else None

    def add_order(self, order: Order) -> bool:
        if order.order_type == "MARKET":
            success = self._handle_market_order(order)
            if not success:
                return False
        else:
            if order.side == "BUY":
                heapq.heappush(self.bids, (-order.price, order.timestamp, order))
            else:
                heapq.heappush(self.asks, (order.price, order.timestamp, order))
            self.order_map[order.order_id] = order
            self.match_orders()
        return True

    def _handle_market_order(self, market_order: Order) -> bool:
        """Handle market order execution."""
        if market_order.side == "BUY":
            if not self.asks:
                return False
            while market_order.quantity > 0 and self.asks:
                best_ask = self.asks[0][2]
                trade_quantity = min(market_order.quantity, best_ask.quantity)
                trade_price = best_ask.price
                self.trades.append(Trade(time.time(), trade_price, trade_quantity, "BUY"))
                self.last_trade_price = trade_price

                best_ask.quantity -= trade_quantity
                market_order.quantity -= trade_quantity

                if best_ask.quantity == 0:
                    heapq.heappop(self.asks)
            return True
        else:
            if not self.bids:
                return False
            while market_order.quantity > 0 and self.bids:
                best_bid = self.bids[0][2]
                trade_quantity = min(market_order.quantity, best_bid.quantity)
                trade_price = best_bid.price
                self.trades.append(Trade(time.time(), trade_price, trade_quantity, "SELL"))
                self.last_trade_price = trade_price

                best_bid.quantity -= trade_quantity
                market_order.quantity -= trade_quantity

                if best_bid.quantity == 0:
                    heapq.heappop(self.bids)
            return True

    def match_orders(self):
        """Match buy and sell orders based on price priority."""
        while self.bids and self.asks:
            best_bid = self.bids[0][2]
            best_ask = self.asks[0][2]

            if best_bid.price >= best_ask.price:
                trade_quantity = min(best_bid.quantity, best_ask.quantity)
                trade_price = best_ask.price
                trade_side = "BUY" if best_bid.timestamp > best_ask.timestamp else "SELL"
                self.trades.append(Trade(time.time(), trade_price, trade_quantity, trade_side))
                self.last_trade_price = trade_price

                best_bid.quantity -= trade_quantity
                best_ask.quantity -= trade_quantity

                if best_bid.quantity == 0:
                    heapq.heappop(self.bids)
                if best_ask.quantity == 0:
                    heapq.heappop(self.asks)
            else:
                break

    def get_order_book(self) -> Tuple[List[Tuple[float, int]], List[Tuple[float, int]]]:
        """Return current order book state as (bids, asks)"""
        bids = sorted([(-p, o.quantity) for p, _, o in self.bids], reverse=True)
        asks = sorted([(p, o.quantity) for p, _, o in self.asks])
        return bids, asks

    def get_mid_price(self) -> float:
        """Get current mid price or last trade price if book is empty"""
        bids, asks = self.get_order_book()
        if bids and asks:
            return (bids[0][0] + asks[0][0]) / 2
        return self.last_trade_price

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order"""
        if order_id not in self.order_map:
            return False

        order = self.order_map[order_id]

        del self.order_map[order_id]

        if order.side == "BUY":
            self.bids = [(p, t, o) for p, t, o in self.bids if o.order_id != order_id]
            heapq.heapify(self.bids)
        else:
            self.asks = [(p, t, o) for p, t, o in self.asks if o.order_id != order_id]
            heapq.heapify(self.asks)

        return True
