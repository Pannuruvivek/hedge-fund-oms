"""
Broker integration layer.

This defines a standard BrokerAdapter interface (per BRD constraint: "Integration
with external systems must follow predefined standards") so real broker
connections (FIX, REST, proprietary SDKs) can be added later without touching
order-management logic. SimulatedBrokerAdapter is a stub used for local
development and testing — it does not talk to any external network.
"""
from __future__ import annotations
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BrokerAck:
    accepted: bool
    broker_order_ref: str | None
    reason: str | None = None


@dataclass
class BrokerFill:
    quantity: float
    price: float
    broker_fill_ref: str


class BrokerAdapter(ABC):
    """Standard interface every broker integration must implement."""

    @abstractmethod
    def submit_order(self, *, symbol: str, side: str, order_type: str,
                      quantity: float, limit_price: float | None) -> BrokerAck:
        ...

    @abstractmethod
    def cancel_order(self, broker_order_ref: str) -> bool:
        ...

    @abstractmethod
    def poll_fills(self, broker_order_ref: str, remaining_quantity: float) -> list[BrokerFill]:
        ...


class SimulatedBrokerAdapter(BrokerAdapter):
    """
    In-memory simulated broker for local dev / demos.
    Always accepts orders and immediately fills them at a synthetic price
    (limit price if provided, otherwise a random walk around 100).
    """

    def submit_order(self, *, symbol: str, side: str, order_type: str,
                      quantity: float, limit_price: float | None) -> BrokerAck:
        return BrokerAck(accepted=True, broker_order_ref=f"SIM-{uuid.uuid4().hex[:10]}")

    def cancel_order(self, broker_order_ref: str) -> bool:
        return True

    def poll_fills(self, broker_order_ref: str, remaining_quantity: float) -> list[BrokerFill]:
        price = round(random.uniform(95, 105), 2)
        return [BrokerFill(
            quantity=remaining_quantity,
            price=price,
            broker_fill_ref=f"FILL-{uuid.uuid4().hex[:10]}",
        )]


def get_broker_adapter(name: str | None) -> BrokerAdapter:
    """
    Broker registry. Add real adapters here, e.g.:
        if name == "INTERACTIVE_BROKERS": return IBAdapter()
    """
    return SimulatedBrokerAdapter()
