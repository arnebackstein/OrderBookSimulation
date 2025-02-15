from abc import ABC, abstractmethod
import time
import random
import numpy as np
from typing import Optional, Tuple, List, Dict
from order_book import Order


class MarketParticipant(ABC):
    def __init__(self, name: str):
        self.name = name
        self.active_orders: Dict[int, Order] = {}
        self.last_mid_price = None

    @abstractmethod
    def act(self, order_book) -> None:
        """Define participant's trading behavior"""
        pass
