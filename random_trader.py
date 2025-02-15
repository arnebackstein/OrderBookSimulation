import time
import random
import numpy as np
from typing import Optional, Dict
from market_participants import MarketParticipant
from order_book import Order


class RandomTrader(MarketParticipant):
    def __init__(
        self,
        name: str,
        mean_time_between_trades: float = 5.0,
        market_order_probability: float = 0.3,
        max_order_size: int = 50,
        price_range_bps: int = 20,
    ):
        super().__init__(name)
        self.mean_time_between_trades = mean_time_between_trades
        self.market_order_probability = market_order_probability
        self.max_order_size = max_order_size
        self.price_range_bps = price_range_bps
        self.last_trade_time = time.time()

    def generate_order_size(self) -> int:
        """
        Generate realistic order sizes using a power law distribution.
        This creates many small orders and few large orders.
        """

        alpha = 2.5

        size = int(np.random.power(alpha) * self.max_order_size)
        return max(1, size)

    def should_trade(self) -> bool:
        """
        Determine if it's time to place a new trade using a Poisson process
        """
        current_time = time.time()
        time_since_last = current_time - self.last_trade_time

        trade_probability = 1 - np.exp(-time_since_last / self.mean_time_between_trades)
        return random.random() < trade_probability

    def generate_limit_price(self, mid_price: float, side: str) -> float:
        """
        Generate a limit price near the mid price.
        Uses a beta distribution to cluster prices near the best bid/ask.
        """

        if side == "BUY":
            a, b = 2.0, 5.0
        else:
            a, b = 5.0, 2.0

        deviation_bps = random.betavariate(a, b) * self.price_range_bps

        adjustment = (deviation_bps / 10000) * mid_price

        if side == "BUY":
            price = mid_price - adjustment
        else:
            price = mid_price + adjustment

        return round(price, 2)

    def act(self, order_book) -> None:
        """
        Potentially place a new order based on market conditions
        """
        if not self.should_trade():
            return

        mid_price = order_book.get_mid_price()
        if mid_price is None:
            return

        side = random.choice(["BUY", "SELL"])

        size = self.generate_order_size()

        is_market_order = random.random() < self.market_order_probability

        if is_market_order:

            order_book.add_order_api(
                side=side,
                price=0,
                quantity=size,
                order_type="MARKET",
                participant_name=self.name,
            )
        else:

            limit_price = self.generate_limit_price(mid_price, side)
            success, order_id = order_book.add_order_api(
                side=side,
                price=limit_price,
                quantity=size,
                order_type="LIMIT",
                participant_name=self.name,
            )

            if success and order_id is not None and order_id in order_book.order_map:
                self.active_orders[order_id] = order_book.order_map[order_id]

        self.last_trade_time = time.time()
