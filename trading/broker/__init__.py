"""The broker layer — the system's "phone line" to the outside world.

The rest of the system only ever talks to the abstract `Broker` interface in
`base.py`, never to Alpaca directly. That means Alpaca can later be swapped
for Interactive Brokers by writing one new file here, without touching the
agents, strategies, or dashboard.
"""

from trading.broker.base import AccountSnapshot, Broker, OrderTicket, Position
from trading.broker.alpaca_broker import AlpacaBroker
from trading.config import Settings, get_settings


def get_broker(settings: Settings | None = None) -> Broker:
    """Return the configured broker (currently always Alpaca paper).

    When Interactive Brokers support is added, this factory is the single
    place that decides which implementation to hand out.
    """
    return AlpacaBroker(settings or get_settings())


__all__ = [
    "AccountSnapshot",
    "AlpacaBroker",
    "Broker",
    "OrderTicket",
    "Position",
    "get_broker",
]
