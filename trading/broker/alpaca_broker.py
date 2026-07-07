"""Alpaca implementation of the broker interface — paper trading only.

Safety property: the Alpaca client below is constructed with paper=True,
hard-coded. Even if live-account keys were pasted into .env, requests would
still go to Alpaca's paper endpoint, not the live one.
"""

from datetime import datetime, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

from trading.broker.base import AccountSnapshot, Broker, OrderTicket, Position
from trading.config import Settings


class AlpacaBroker(Broker):
    def __init__(self, settings: Settings):
        missing = settings.missing_alpaca_keys()
        if missing:
            raise RuntimeError(
                "Alpaca keys are missing: " + ", ".join(missing)
                + ". Copy trading/.env.example to trading/.env and fill them in "
                "(see trading/README.md, 'Setting up', Step 2)."
            )
        self._client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=True,  # hard-coded on purpose; see module docstring
        )

    def name(self) -> str:
        return "Alpaca (paper)"

    def get_account(self) -> AccountSnapshot:
        acct = self._client.get_account()
        return AccountSnapshot(
            account_id=str(acct.account_number),
            is_paper=True,
            currency=str(acct.currency),
            cash=float(acct.cash),
            equity=float(acct.equity),
            buying_power=float(acct.buying_power),
            blocked=bool(acct.trading_blocked or acct.account_blocked),
            as_of=datetime.now(timezone.utc),
        )

    def get_positions(self) -> list[Position]:
        positions = []
        for p in self._client.get_all_positions():
            positions.append(
                Position(
                    symbol=str(p.symbol),
                    quantity=float(p.qty),
                    avg_entry_price=float(p.avg_entry_price),
                    current_price=float(p.current_price or 0),
                    market_value=float(p.market_value or 0),
                    unrealized_pl=float(p.unrealized_pl or 0),
                    unrealized_pl_pct=float(p.unrealized_plpc or 0),
                )
            )
        return positions

    def is_market_open(self) -> bool:
        return bool(self._client.get_clock().is_open)

    def submit_order(self, ticket: OrderTicket) -> str:
        if ticket.side not in ("buy", "sell"):
            raise ValueError(f"Order side must be 'buy' or 'sell', got {ticket.side!r}")
        side = OrderSide.BUY if ticket.side == "buy" else OrderSide.SELL
        tif = TimeInForce.DAY if ticket.time_in_force == "day" else TimeInForce.GTC
        if ticket.limit_price is None:
            request = MarketOrderRequest(
                symbol=ticket.symbol, qty=ticket.quantity, side=side, time_in_force=tif
            )
        else:
            request = LimitOrderRequest(
                symbol=ticket.symbol,
                qty=ticket.quantity,
                side=side,
                time_in_force=tif,
                limit_price=ticket.limit_price,
            )
        order = self._client.submit_order(request)
        return str(order.id)
