"""
Tests covering the BRD order lifecycle end-to-end:
  PM creates -> compliance check -> send to trading
  -> Trader sends to broker -> records fill -> EXECUTED
  -> Operations sends to post-trade -> DONE

Run with: pytest (from the backend/ directory)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def register_and_login(username, role, password="pass1234"):
    client.post("/auth/register", json={"username": username, "password": password, "role": role})
    resp = client.post("/auth/login", data={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def actors():
    """First user registered becomes ADMIN regardless of requested role, so
    register an admin first, then the three business roles."""
    admin = register_and_login("admin0", "ADMIN")
    pm = register_and_login("pm0", "PORTFOLIO_MANAGER")
    trader = register_and_login("trader0", "TRADER")
    ops = register_and_login("ops0", "OPERATIONS")
    return {"admin": admin, "pm": pm, "trader": trader, "ops": ops}


def make_security(headers, symbol="AAPL"):
    resp = client.post("/tickers", json={"symbol": symbol, "name": symbol, "exchange": "NASDAQ"}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


def test_full_lifecycle_happy_path(actors):
    make_security(actors["pm"], "AAPL")

    order = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 100},
                         headers=actors["pm"]).json()
    assert order["status"] == "NEW"

    order = client.post(f"/orders/{order['id']}/compliance-check", headers=actors["pm"]).json()
    assert order["status"] == "OK"

    order = client.post(f"/orders/{order['id']}/send-to-trading", headers=actors["pm"]).json()
    assert order["status"] == "TRADE_NEW"

    order = client.post(f"/orders/{order['id']}/send-to-broker", headers=actors["trader"]).json()
    assert order["status"] == "EXECUTING"
    assert order["broker_order_ref"]

    order = client.post(f"/orders/{order['id']}/fills",
                         json={"quantity": 100, "price": 150.25}, headers=actors["trader"]).json()
    assert order["status"] == "EXECUTED"
    assert order["filled_quantity"] == 100

    order = client.post(f"/orders/{order['id']}/send-to-post-trade", headers=actors["ops"]).json()
    assert order["status"] == "DONE"


def test_compliance_check_fails_over_size_limit(actors):
    make_security(actors["pm"], "AAPL")
    order = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 999_999},
                         headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/compliance-check", headers=actors["pm"]).json()
    assert order["status"] == "FAIL"
    assert "exceeds max order size" in order["compliance_notes"]


def test_compliance_check_fails_for_restricted_symbol(actors):
    make_security(actors["pm"], "XYZ")
    order = client.post("/orders", json={"ticker_symbol": "XYZ", "side": "BUY", "quantity": 10},
                         headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/compliance-check", headers=actors["pm"]).json()
    assert order["status"] == "FAIL"
    assert "restricted list" in order["compliance_notes"]


def test_trader_cannot_create_orders(actors):
    make_security(actors["pm"], "AAPL")
    resp = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 10},
                        headers=actors["trader"])
    assert resp.status_code == 403


def test_cannot_skip_lifecycle_steps(actors):
    make_security(actors["pm"], "AAPL")
    order = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 10},
                         headers=actors["pm"]).json()

    # Can't send to trading before compliance check
    resp = client.post(f"/orders/{order['id']}/send-to-trading", headers=actors["pm"])
    assert resp.status_code == 400

    # Can't send to broker before it's even at trading desk
    resp = client.post(f"/orders/{order['id']}/send-to-broker", headers=actors["trader"])
    assert resp.status_code == 400

    # Operations can't act on it either
    resp = client.post(f"/orders/{order['id']}/send-to-post-trade", headers=actors["ops"])
    assert resp.status_code == 400


def test_pm_only_sees_own_orders(actors):
    make_security(actors["pm"], "AAPL")
    client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 10}, headers=actors["pm"])

    other_pm = register_and_login("pm_other", "PORTFOLIO_MANAGER")
    resp = client.get("/orders", headers=other_pm)
    assert resp.json() == []


def test_trader_only_sees_orders_at_trading_desk_or_later(actors):
    make_security(actors["pm"], "AAPL")
    client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 10}, headers=actors["pm"])

    # Order is still NEW, hasn't reached trading desk
    resp = client.get("/orders", headers=actors["trader"])
    assert resp.json() == []


def test_partial_fill_keeps_order_executing(actors):
    make_security(actors["pm"], "AAPL")
    order = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 100},
                         headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/compliance-check", headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/send-to-trading", headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/send-to-broker", headers=actors["trader"]).json()

    order = client.post(f"/orders/{order['id']}/fills", json={"quantity": 40, "price": 100.0},
                         headers=actors["trader"]).json()
    assert order["status"] == "EXECUTING"
    assert order["filled_quantity"] == 40

    order = client.post(f"/orders/{order['id']}/fills", json={"quantity": 60, "price": 101.0},
                         headers=actors["trader"]).json()
    assert order["status"] == "EXECUTED"
    assert order["filled_quantity"] == 100
    assert round(order["avg_fill_price"], 2) == round((40 * 100.0 + 60 * 101.0) / 100, 2)


def test_ops_cannot_act_before_executed(actors):
    make_security(actors["pm"], "AAPL")
    order = client.post("/orders", json={"ticker_symbol": "AAPL", "side": "BUY", "quantity": 10},
                         headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/compliance-check", headers=actors["pm"]).json()
    order = client.post(f"/orders/{order['id']}/send-to-trading", headers=actors["pm"]).json()

    resp = client.post(f"/orders/{order['id']}/send-to-post-trade", headers=actors["ops"])
    assert resp.status_code == 400
