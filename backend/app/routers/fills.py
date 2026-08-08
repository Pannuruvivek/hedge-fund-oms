from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Fill, Order, User, RoleName, OrderStatus
from ..schemas import FillOut
from ..auth import get_current_user

router = APIRouter(prefix="/fills", tags=["fills"])

TRADER_VISIBLE_STATUSES = [OrderStatus.TRADE_NEW, OrderStatus.EXECUTING, OrderStatus.EXECUTED, OrderStatus.DONE]
OPS_VISIBLE_STATUSES = [OrderStatus.EXECUTED, OrderStatus.DONE]


@router.get("", response_model=list[FillOut])
def list_fills(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Fill).join(Order, Fill.order_id == Order.id)
    if user.role == RoleName.PORTFOLIO_MANAGER:
        query = query.filter(Order.owner_id == user.id)
    elif user.role == RoleName.TRADER:
        query = query.filter(Order.status.in_(TRADER_VISIBLE_STATUSES))
    elif user.role == RoleName.OPERATIONS:
        query = query.filter(Order.status.in_(OPS_VISIBLE_STATUSES))
    # ADMIN sees all
    return query.order_by(Fill.executed_at.desc()).all()


@router.get("/order/{order_id}", response_model=list[FillOut])
def list_fills_for_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    permitted = (
        user.role == RoleName.ADMIN
        or (user.role == RoleName.PORTFOLIO_MANAGER and order.owner_id == user.id)
        or (user.role == RoleName.TRADER and order.status in TRADER_VISIBLE_STATUSES)
        or (user.role == RoleName.OPERATIONS and order.status in OPS_VISIBLE_STATUSES)
    )
    if not permitted:
        raise HTTPException(status_code=403, detail="Not permitted to view fills for this order")
    return db.query(Fill).filter(Fill.order_id == order_id).order_by(Fill.executed_at.desc()).all()
