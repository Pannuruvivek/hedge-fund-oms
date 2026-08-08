"""
Order lifecycle endpoints, implementing BRD 5.1.1 / 6.1-6.3 exactly:

  PM:  create (NEW) -> compliance check (OK/FAIL) -> send to trading (TRADE_NEW)
  Trader: send to broker (EXECUTING) -> record fill(s) -> (EXECUTED)
  Operations: send to post-trade (DONE)

Each transition is its own endpoint, gated to the role the BRD assigns that
step to (5.1.3 Permissions & Privileges), and each transition is audit-logged
(5.2 Audit Trail).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Ticker, Fill, User, RoleName, OrderStatus
from ..schemas import OrderCreate, OrderOut, OrderCancel, RecordFill
from ..auth import get_current_user, require_roles
from ..services.broker_stub import get_broker_adapter
from ..services.compliance_stub import get_compliance_engine
from .. import audit

router = APIRouter(prefix="/orders", tags=["orders"])


def _visible_orders_query(db: Session, user: User):
    """
    Role-scoped visibility:
      ADMIN              -> everything
      PORTFOLIO_MANAGER   -> only orders they created (BRD 6.1: PM manages their own orders)
      TRADER              -> everything from TRADE_NEW onward (BRD 6.2: trading desk queue + history)
      OPERATIONS          -> everything from EXECUTED onward (BRD 6.3: post-trade queue + history)
    """
    query = db.query(Order)
    if user.role == RoleName.ADMIN:
        return query
    if user.role == RoleName.PORTFOLIO_MANAGER:
        return query.filter(Order.owner_id == user.id)
    if user.role == RoleName.TRADER:
        return query.filter(Order.status.in_([
            OrderStatus.TRADE_NEW, OrderStatus.EXECUTING, OrderStatus.EXECUTED, OrderStatus.DONE,
        ]))
    if user.role == RoleName.OPERATIONS:
        return query.filter(Order.status.in_([OrderStatus.EXECUTED, OrderStatus.DONE]))
    return query.filter(False)


def _get_order_or_404(db: Session, order_id: str) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _assert_can_view(order: Order, user: User):
    if user.role == RoleName.ADMIN:
        return
    if user.role == RoleName.PORTFOLIO_MANAGER and order.owner_id == user.id:
        return
    if user.role == RoleName.TRADER and order.status in (
        OrderStatus.TRADE_NEW, OrderStatus.EXECUTING, OrderStatus.EXECUTED, OrderStatus.DONE,
    ):
        return
    if user.role == RoleName.OPERATIONS and order.status in (OrderStatus.EXECUTED, OrderStatus.DONE):
        return
    raise HTTPException(status_code=403, detail="Not permitted to view this order")


# ---------- 1. Portfolio Manager: create order (BRD 6.1 steps 1-3) ----------

@router.post("", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(RoleName.PORTFOLIO_MANAGER, RoleName.ADMIN))):
    ticker = db.query(Ticker).filter(Ticker.symbol == payload.ticker_symbol.upper(),
                                      Ticker.is_active == True).first()  # noqa: E712
    if not ticker:
        raise HTTPException(status_code=404, detail="Unknown or inactive security. Create it first.")

    order = Order(
        ticker_id=ticker.id,
        owner_id=user.id,
        side=payload.side,
        quantity=payload.quantity,
        broker=payload.broker,
        status=OrderStatus.NEW,
    )
    db.add(order)
    db.flush()
    audit.record(db, user, "ORDER_CREATE", entity_type="Order", entity_id=order.id,
                 detail=f"{payload.side.value} {payload.quantity} {ticker.symbol}")
    db.commit()
    db.refresh(order)
    return order


# ---------- 2. Portfolio Manager: pre-trade compliance check (BRD 6.1 step 4) ----------

@router.post("/{order_id}/compliance-check", response_model=OrderOut)
def run_compliance_check(order_id: str, db: Session = Depends(get_db),
                          user: User = Depends(require_roles(RoleName.PORTFOLIO_MANAGER, RoleName.ADMIN))):
    order = _get_order_or_404(db, order_id)
    if user.role == RoleName.PORTFOLIO_MANAGER and order.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not permitted to act on this order")
    if order.status != OrderStatus.NEW:
        raise HTTPException(status_code=400, detail=f"Compliance check requires status NEW, got {order.status.value}")

    result = get_compliance_engine().check(symbol=order.ticker.symbol, side=order.side.value, quantity=order.quantity)
    order.status = OrderStatus.OK if result.passed else OrderStatus.FAIL
    order.compliance_checked_at = datetime.utcnow()
    order.compliance_notes = result.notes

    audit.record(db, user, "COMPLIANCE_CHECK", entity_type="Order", entity_id=order.id,
                 detail=f"result={order.status.value}: {result.notes}")
    db.commit()
    db.refresh(order)
    return order


# ---------- 3. Portfolio Manager: send to trading (BRD 6.1 step 6) ----------

@router.post("/{order_id}/send-to-trading", response_model=OrderOut)
def send_to_trading(order_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(RoleName.PORTFOLIO_MANAGER, RoleName.ADMIN))):
    order = _get_order_or_404(db, order_id)
    if user.role == RoleName.PORTFOLIO_MANAGER and order.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not permitted to act on this order")
    if order.status != OrderStatus.OK:
        raise HTTPException(status_code=400, detail=f"Order must have passed compliance (status OK) to send to trading, got {order.status.value}")

    order.status = OrderStatus.TRADE_NEW
    audit.record(db, user, "SEND_TO_TRADING", entity_type="Order", entity_id=order.id)
    db.commit()
    db.refresh(order)
    return order


# ---------- 4. Trader: send to broker for execution (BRD 6.2 steps 2-3) ----------

@router.post("/{order_id}/send-to-broker", response_model=OrderOut)
def send_to_broker(order_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(RoleName.TRADER, RoleName.ADMIN))):
    order = _get_order_or_404(db, order_id)
    if order.status != OrderStatus.TRADE_NEW:
        raise HTTPException(status_code=400, detail=f"Order must be in TRADE_NEW to send to broker, got {order.status.value}")

    adapter = get_broker_adapter(order.broker)
    ack = adapter.submit_order(
        symbol=order.ticker.symbol, side=order.side.value, order_type="MARKET",
        quantity=order.quantity, limit_price=None,
    )
    if not ack.accepted:
        raise HTTPException(status_code=502, detail=f"Broker rejected order: {ack.reason}")

    order.broker_order_ref = ack.broker_order_ref
    order.sent_to_broker_by = user.id
    order.status = OrderStatus.EXECUTING

    audit.record(db, user, "SEND_TO_BROKER", entity_type="Order", entity_id=order.id,
                 detail=f"broker_ref={ack.broker_order_ref}")
    db.commit()
    db.refresh(order)
    return order


# ---------- 5. Trader: record / simulate fills (BRD 6.2 step 4-5) ----------

def _apply_fill(db: Session, order: Order, quantity: float, price: float, broker_fill_ref: str | None):
    fill = Fill(order_id=order.id, quantity=quantity, price=price, broker_fill_ref=broker_fill_ref)
    db.add(fill)

    prior_notional = (order.avg_fill_price or 0) * order.filled_quantity
    order.filled_quantity += quantity
    order.avg_fill_price = (prior_notional + quantity * price) / order.filled_quantity if order.filled_quantity else None

    if order.filled_quantity >= order.quantity:
        order.status = OrderStatus.EXECUTED


@router.post("/{order_id}/fills", response_model=OrderOut)
def record_fill(order_id: str, payload: RecordFill, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(RoleName.TRADER, RoleName.ADMIN))):
    """Manually record a fill message from a broker. Standing in for a real broker fill feed."""
    order = _get_order_or_404(db, order_id)
    if order.status != OrderStatus.EXECUTING:
        raise HTTPException(status_code=400, detail=f"Order must be EXECUTING to record a fill, got {order.status.value}")
    if order.filled_quantity + payload.quantity > order.quantity:
        raise HTTPException(status_code=400, detail="Fill quantity would exceed order quantity")

    _apply_fill(db, order, payload.quantity, payload.price, payload.broker_fill_ref)
    audit.record(db, user, "FILL_RECORDED", entity_type="Order", entity_id=order.id,
                 detail=f"qty={payload.quantity} px={payload.price} -> status={order.status.value}")
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/simulate-fill", response_model=OrderOut)
def simulate_fill(order_id: str, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(RoleName.TRADER, RoleName.ADMIN))):
    """
    Convenience for local dev/demo: pulls a fill from the simulated broker
    adapter for the remaining quantity instead of typing numbers in by hand.
    """
    order = _get_order_or_404(db, order_id)
    if order.status != OrderStatus.EXECUTING:
        raise HTTPException(status_code=400, detail=f"Order must be EXECUTING to simulate a fill, got {order.status.value}")

    remaining = order.quantity - order.filled_quantity
    adapter = get_broker_adapter(order.broker)
    for f in adapter.poll_fills(order.broker_order_ref, remaining_quantity=remaining):
        _apply_fill(db, order, f.quantity, f.price, f.broker_fill_ref)

    audit.record(db, user, "FILL_RECORDED", entity_type="Order", entity_id=order.id,
                 detail=f"simulated -> status={order.status.value}")
    db.commit()
    db.refresh(order)
    return order


# ---------- 6. Operations: send to post-trade (BRD 6.3 step 3) ----------

@router.post("/{order_id}/send-to-post-trade", response_model=OrderOut)
def send_to_post_trade(order_id: str, db: Session = Depends(get_db),
                        user: User = Depends(require_roles(RoleName.OPERATIONS, RoleName.ADMIN))):
    order = _get_order_or_404(db, order_id)
    if order.status != OrderStatus.EXECUTED:
        raise HTTPException(status_code=400, detail=f"Order must be EXECUTED to send to post-trade, got {order.status.value}")

    order.status = OrderStatus.DONE
    order.post_trade_sent_by = user.id
    order.post_trade_sent_at = datetime.utcnow()

    audit.record(db, user, "SEND_TO_POST_TRADE", entity_type="Order", entity_id=order.id)
    db.commit()
    db.refresh(order)
    return order


# ---------- Cancellation (extension beyond the BRD) ----------

@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: str, payload: OrderCancel, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(RoleName.PORTFOLIO_MANAGER, RoleName.ADMIN))):
    order = _get_order_or_404(db, order_id)
    if user.role == RoleName.PORTFOLIO_MANAGER and order.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not permitted to act on this order")
    if order.status not in (OrderStatus.NEW, OrderStatus.OK, OrderStatus.FAIL, OrderStatus.TRADE_NEW):
        raise HTTPException(status_code=400, detail=f"Cannot cancel an order once it has reached a broker (status {order.status.value})")

    order.status = OrderStatus.CANCELLED
    audit.record(db, user, "ORDER_CANCEL", entity_type="Order", entity_id=order.id, detail=payload.reason)
    db.commit()
    db.refresh(order)
    return order


# ---------- Reads ----------

@router.get("", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _visible_orders_query(db, user).order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = _get_order_or_404(db, order_id)
    _assert_can_view(order, user)
    return order
