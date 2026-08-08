"""
One-off convenience script: creates one demo user per BRD role (Portfolio
Manager, Trader, Operations, plus Admin) and a few demo securities, so you
can walk through the full BRD 6.1-6.3 workflow immediately. Safe to re-run —
skips anything that already exists.

Usage:
    python -m app.seed
"""
from .database import SessionLocal, Base, engine
from .models import User, Ticker, RoleName
from .auth import hash_password

DEMO_USERS = [
    ("admin", "admin123", RoleName.ADMIN),
    ("pm1", "pm12345", RoleName.PORTFOLIO_MANAGER),
    ("trader1", "trader123", RoleName.TRADER),
    ("ops1", "ops12345", RoleName.OPERATIONS),
]

DEMO_TICKERS = [
    ("AAPL", "Apple Inc.", "NASDAQ"),
    ("MSFT", "Microsoft Corp.", "NASDAQ"),
    ("TSLA", "Tesla Inc.", "NASDAQ"),
    ("SPY", "SPDR S&P 500 ETF Trust", "NYSEARCA"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for username, password, role in DEMO_USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(username=username, hashed_password=hash_password(password), role=role))
                print(f"Created user -> username: {username}  password: {password}  role: {role.value}")
            else:
                print(f"User {username} already exists, skipping.")

        for symbol, name, exchange in DEMO_TICKERS:
            if not db.query(Ticker).filter(Ticker.symbol == symbol).first():
                db.add(Ticker(symbol=symbol, name=name, exchange=exchange))
                print(f"Created security {symbol}")

        db.commit()
        print("\nSeed complete. Walk the full workflow as: pm1 -> trader1 -> ops1 (all passwords above).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
