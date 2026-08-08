from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ticker, User, RoleName
from ..schemas import TickerCreate, TickerOut
from ..auth import get_current_user, require_roles
from .. import audit

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("", response_model=list[TickerOut])
def list_tickers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Ticker).filter(Ticker.is_active == True).all()  # noqa: E712


@router.post("", response_model=TickerOut)
def create_ticker(payload: TickerCreate, db: Session = Depends(get_db),
                   # BRD 5.1.2: Portfolio Manager can "create a new security, if needed".
                   # ADMIN retained for general system administration.
                   user: User = Depends(require_roles(RoleName.PORTFOLIO_MANAGER, RoleName.ADMIN))):
    if db.query(Ticker).filter(Ticker.symbol == payload.symbol.upper()).first():
        raise HTTPException(status_code=400, detail="Ticker already exists")
    ticker = Ticker(symbol=payload.symbol.upper(), name=payload.name, exchange=payload.exchange)
    db.add(ticker)
    db.flush()
    audit.record(db, user, "TICKER_CREATE", entity_type="Ticker", entity_id=ticker.id, detail=ticker.symbol)
    db.commit()
    db.refresh(ticker)
    return ticker


@router.delete("/{ticker_id}")
def deactivate_ticker(ticker_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(RoleName.ADMIN))):
    ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")
    ticker.is_active = False
    audit.record(db, user, "TICKER_DEACTIVATE", entity_type="Ticker", entity_id=ticker.id, detail=ticker.symbol)
    db.commit()
    return {"detail": "Ticker deactivated"}
