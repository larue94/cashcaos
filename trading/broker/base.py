"""Abstract broker interface.

Any broker (Alpaca today, Interactive Brokers tomorrow) must implement this
interface. The rest of the system imports only these classes, so swapping
brokers never requires changes outside the broker/ folder.

All money amounts are in US dollars.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AccountSnapshot:
    """A point-in-time picture of the trading account."""

    account_id: str
    is_paper: bool          # True = simulated money. Must always be True here.
    currency: str
    cash: float             # uninvested cash
    equity: float           # total account value (cash + positions)
    buying_power: float     # how much the broker would let us buy
    blocked: bool           # broker has frozen trading on the account
    as_of: datetime


@dataclass
class Position:
    """One holding in the account."""

    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float          # profit/loss in dollars since entry
    unrealized_pl_pct: float      # same, as a fraction (0.05 = +5%)


@dataclass
class OrderTicket:
    """A trade instruction, expressed broker-agnostically.

    Only plain long stock orders are supported: no shorting, no margin, no
    options. `limit_price` of None means a market order.
    """

    symbol: str
    side: str                     # "buy" or "sell"
    quantity: float
    limit_price: float | None = None
    time_in_force: str = "day"    # order expires at end of day if unfilled


class Broker(ABC):
    """What every broker implementation must be able to do."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable broker name, e.g. 'Alpaca (paper)'."""

    @abstractmethod
    def get_account(self) -> AccountSnapshot:
        """Fetch current account balances and status."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Fetch all current holdings."""

    @abstractmethod
    def is_market_open(self) -> bool:
        """True if the US stock market is open right now."""

    @abstractmethod
    def submit_order(self, ticket: OrderTicket) -> str:
        """Send an order to the broker; returns the broker's order id.

        NOTE: nothing in this system calls submit_order without an explicit
        human approval recorded first (enforced from Phase 5 onward).
        """
