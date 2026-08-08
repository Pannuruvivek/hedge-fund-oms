"""
Core ORM models for the Hedge Fund Order Management System, built against
BRD sections 3-7 (Scope, Stakeholders, Requirements, Workflows).

Entities:
- User / RoleName   -> RBAC per BRD 5.1.3 (Permissions & Privileges)
- Ticker            -> "security", BRD 9 Glossary
- Order             -> BRD 5.1.1 order lifecycle + 6.x workflows
- Fill              -> BRD 9 Glossary ("confirmation of executed orders from brokers")
- AuditLog          -> BRD 5.2 Non-Functional Requirements ("Audit Trail")
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Enum, Boolean
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class RoleName(str, enum.Enum):
    """
    BRD 4 (Stakeholders) + 5.1.3 (Permissions & Privileges) define three
    business roles. ADMIN is added on top for user/system administration
    (BRD 5.2 requires RBAC generally but doesn't define who administers it).
    """
    ADMIN = "ADMIN"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"  # BRD 4/5.1.2: create orders, run compliance, send to trading
    TRADER = "TRADER"                        # BRD 4/5.1.2: send to broker, review fills
    OPERATIONS = "OPERATIONS"                # BRD 4/5.1.2: view executed orders, send to post-trade


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    """
    BRD 5.1.1 Order Lifecycle, exactly as specified:
      New -> OK/Fail (pre-trade compliance) -> Trade New -> Executing -> Executed -> Done
    CANCELLED is an addition beyond the BRD (a PM/Trader escape hatch before
    execution) — flagged in the README as an extension, not a BRD requirement.
    """
    NEW = "NEW"                # 1. Order created by Portfolio Manager
    OK = "OK"                  # 2a. Passed pre-trade compliance check
    FAIL = "FAIL"              # 2b. Failed pre-trade compliance check
    TRADE_NEW = "TRADE_NEW"    # 3. Order sent to trading
    EXECUTING = "EXECUTING"    # 4. Order being executed by broker
    EXECUTED = "EXECUTED"      # 5. Order successfully executed
    DONE = "DONE"              # 6. Order sent to post-trade
    CANCELLED = "CANCELLED"    # extension: cancelled before reaching a broker


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleName), nullable=False, default=RoleName.PORTFOLIO_MANAGER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="owner", foreign_keys="Order.owner_id")


class Ticker(Base):
    """A security, per BRD Glossary: 'Ticker: Unique identifier for securities.'"""
    __tablename__ = "tickers"

    id = Column(String, primary_key=True, default=gen_id)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    exchange = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="ticker")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_id)
    client_order_id = Column(String, unique=True, index=True, default=gen_id)

    ticker_id = Column(String, ForeignKey("tickers.id"), nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)  # the Portfolio Manager who created it

    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)

    status = Column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)

    # BRD 5.1.2: pre-trade compliance check results (PM-triggered)
    compliance_checked_at = Column(DateTime, nullable=True)
    compliance_notes = Column(String, nullable=True)

    # Trading desk / broker fields (BRD 6.2 Trader Workflow)
    broker = Column(String, nullable=True)
    broker_order_ref = Column(String, nullable=True)
    sent_to_broker_by = Column(String, ForeignKey("users.id"), nullable=True)  # the Trader

    filled_quantity = Column(Float, default=0.0)
    avg_fill_price = Column(Float, nullable=True)

    # Post-trade (BRD 6.3 Operations User Workflow)
    post_trade_sent_by = Column(String, ForeignKey("users.id"), nullable=True)  # the Operations user
    post_trade_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ticker = relationship("Ticker", back_populates="orders")
    owner = relationship("User", back_populates="orders", foreign_keys=[owner_id])
    fills = relationship("Fill", back_populates="order", cascade="all, delete-orphan")


class AuditLog(Base):
    """
    Append-only record of security- and trade-relevant actions.
    BRD 5.2: "Audit Trail: Track all actions and status changes for
    compliance purposes."
    """
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=gen_id)
    actor_username = Column(String, nullable=False)
    actor_role = Column(Enum(RoleName), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Fill(Base):
    """BRD Glossary: 'Fill: Confirmation of executed orders from brokers.'"""
    __tablename__ = "fills"

    id = Column(String, primary_key=True, default=gen_id)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)

    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    broker_fill_ref = Column(String, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="fills")
