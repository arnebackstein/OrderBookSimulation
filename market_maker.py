import time
import random
import statistics
from typing import Tuple, List, Dict
from market_participants import MarketParticipant


class MarketMaker(MarketParticipant):
    def __init__(
        self,
        name: str,
        base_spread: float = 1.0,
        inventory_limit: int = 100,
        num_levels: int = 3,
        size_range: Tuple[int, int] = (5, 15),
        volatility_window: int = 10,
        inventory_risk_factor: float = 0.05,
        volatility_sensitivity: float = 0.5,
    ):
        """
        :param name: Participant's name/id
        :param base_spread: Minimum spread (in price units) around mid-price
        :param inventory_limit: Max net inventory before adjusting quotes more aggressively
        :param num_levels: How many bid/ask levels to place on each side
        :param size_range: (min_size, max_size) for random order sizes
        :param volatility_window: How many mid-prices to store for volatility calculation
        :param inventory_risk_factor: Adjust quotes more if inventory is close to limit
        :param volatility_sensitivity: How much to widen/tighten spread based on volatility
        """
        super().__init__(name)

        self.base_spread = base_spread
        self.inventory_limit = inventory_limit
        self.num_levels = num_levels
        self.size_range = size_range
        self.volatility_window = volatility_window
        self.inventory_risk_factor = inventory_risk_factor
        self.volatility_sensitivity = volatility_sensitivity

        self.inventory = 0
        self.price_history: List[float] = []

    def act(self, order_book) -> None:
        """
        Called once every second. Cancels old orders, calculates new quotes, and places new orders.
        """

        self.cancel_all_orders(order_book)

        mid_price = order_book.get_mid_price()
        if mid_price is None:
            return

        self.update_price_history(mid_price)

        current_vol = self.calculate_volatility()
        adjusted_spread = self.calculate_spread(current_vol)

        self.place_quotes(order_book, mid_price, adjusted_spread)

        self.last_mid_price = mid_price

    def cancel_all_orders(self, order_book):
        """
        Cancel all active orders this market maker currently has in the order book.
        """
        for order_id in list(self.active_orders.keys()):
            order_book.cancel_order(order_id)
            self.active_orders.pop(order_id, None)

    def update_price_history(self, mid_price: float):
        """
        Keep a rolling window of mid-prices to estimate volatility.
        """
        self.price_history.append(mid_price)
        if len(self.price_history) > self.volatility_window:
            self.price_history.pop(0)

    def calculate_volatility(self) -> float:
        """
        Basic volatility measure: standard deviation of mid-prices in the recent window.
        Returns 0 if not enough data.
        """
        if len(self.price_history) < 2:
            return 0.0
        return statistics.pstdev(self.price_history)

    def calculate_spread(self, current_vol: float) -> float:
        """
        Spread widens with volatility and if inventory is near the limit.
        - base_spread is the minimum
        - volatility adds extra
        - inventory adds extra
        """
        vol_component = self.volatility_sensitivity * current_vol

        inv_factor = abs(self.inventory) / self.inventory_limit
        inv_component = inv_factor * self.inventory_risk_factor * self.base_spread

        return self.base_spread + vol_component + inv_component

    def place_quotes(self, order_book, mid_price: float, spread: float):
        """
        Place multiple levels of buy (bid) and sell (ask) orders around the mid_price.
        """
        half_spread = spread / 2.0

        for level in range(self.num_levels):

            offset = half_spread + (level * (spread / self.num_levels))

            bid_price = round(mid_price - offset, 2)
            ask_price = round(mid_price + offset, 2)

            size = random.randint(*self.size_range)

            if self.inventory > 0:
                bid_price -= (self.inventory / self.inventory_limit) * 0.1
            elif self.inventory < 0:
                ask_price += (abs(self.inventory) / self.inventory_limit) * 0.1

            success, bid_id = order_book.add_order_api(
                side="BUY",
                price=bid_price,
                quantity=size,
                order_type="LIMIT",
                participant_name=self.name,
            )
            if success and bid_id is not None:
                self.active_orders[bid_id] = order_book.order_map[bid_id]

            success, ask_id = order_book.add_order_api(
                side="SELL",
                price=ask_price,
                quantity=size,
                order_type="LIMIT",
                participant_name=self.name,
            )
            if success and ask_id is not None:
                self.active_orders[ask_id] = order_book.order_map[ask_id]

    def update_inventory(self, filled_quantity: int, side: str):
        """
        If the MarketMaker's orders are filled, we should update inventory.
        - For a filled BUY, inventory increases.
        - For a filled SELL, inventory decreases.
        """
        if side == "BUY":
            self.inventory += filled_quantity
        elif side == "SELL":
            self.inventory -= filled_quantity
