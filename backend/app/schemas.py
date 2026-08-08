from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .models import RoleName, OrderSide, OrderStatus


# ---------- Auth ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    password: str
    role: RoleName = RoleName.PORTFOLIO_MANAGER


class UserOut(BaseModel):
    id: str
    username: str
    role: RoleName
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Ticker / Security ----------

class TickerCreate(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None


class TickerOut(BaseModel):
    id: str
    symbol: str
    name: str
    exchange: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Order ----------

class OrderCreate(BaseModel):
    """BRD 6.1 step 3: Portfolio Manager creates a new order."""
    ticker_symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    broker: Optional[str] = "SIMULATED"


class FillOut(BaseModel):
    id: str
    order_id: str
    quantity: float
    price: float
    broker_fill_ref: Optional[str]
    executed_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    client_order_id: str
    ticker_id: str
    owner_id: str
    side: OrderSide
    quantity: float

    status: OrderStatus
    compliance_checked_at: Optional[datetime]
    compliance_notes: Optional[str]

    broker: Optional[str]
    broker_order_ref: Optional[str]
    sent_to_broker_by: Optional[str]

    filled_quantity: float
    avg_fill_price: Optional[float]

    post_trade_sent_by: Optional[str]
    post_trade_sent_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime
    fills: List[FillOut] = []

    class Config:
        from_attributes = True


class OrderCancel(BaseModel):
    reason: Optional[str] = None


class RecordFill(BaseModel):
    """
    BRD 6.2 step 4: Trader receives and reviews fills from brokers.
    Manual entry point standing in for a real broker fill feed (FIX
    execution report / webhook) — see services/broker_stub.py.
    """
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    broker_fill_ref: Optional[str] = None
