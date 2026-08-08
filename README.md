# Hedge Fund Order Management System (OMS)

A working implementation of the BRD's order lifecycle using a FastAPI backend, React (Vite) frontend, role-based access control (RBAC), a pre-trade compliance stub, and a standardized broker integration interface.

## Project Information

**Developed by:** Vivek  
**Project Guide:** Pradeep

---

## BRD Coverage Map

| BRD Section | Status | Implementation |
|---|---|---|
| **5.1.1 Order Lifecycle** (New → OK/Fail → Trade New → Executing → Executed → Done) | ✅ Implemented | `models.OrderStatus`, `routers/orders.py` |
| **5.1.2 PM** — create order, search/create security, run compliance, send to trading | ✅ | `routers/orders.py`, `routers/tickers.py` |
| **5.1.2 Trader** — view trading-desk orders, send to broker, review fills | ✅ | `routers/orders.py`, `routers/fills.py` |
| **5.1.2 Operations** — view executed orders, send to post-trade | ✅ | `routers/orders.py` |
| **5.1.3 Permissions & Privileges** | ✅ | `auth.require_roles` on mutating endpoints |
| **5.2 RBAC** | ✅ | `models.RoleName` — ADMIN, PORTFOLIO_MANAGER, TRADER, OPERATIONS |
| **5.2 Audit Trail** | ✅ | `models.AuditLog`, `audit.py`, `GET /audit` (ADMIN only) |
| **5.2 Scalability / Performance** | ⚠️ Partial | SQLite by default; Postgres can be configured through `OMS_DATABASE_URL`; no load testing/caching |
| **8. Regulatory compliance** | ⚠️ Partial | RBAC and audit trail exist; no encryption-at-rest, retention policy, or real compliance engine |
| **8. External-system integration** | ✅ Pattern / ⚠️ No real integration | `services/broker_stub.py` defines `BrokerAdapter`; only the simulated adapter is implemented |
| **9. Glossary** | ✅ | OMS, Ticker, Fill, and RBAC are reflected in the model and field naming |

---

## What's Implemented

### Order Lifecycle

The system implements the BRD lifecycle:

```text
NEW
 ↓
OK / FAIL
 ↓
TRADE_NEW
 ↓
EXECUTING
 ↓
EXECUTED
 ↓
DONE
```

### Portfolio Manager

The Portfolio Manager can:

- Create BUY/SELL orders against a security
- Create new securities when needed
- Run a pre-trade compliance check
- Send approved orders to the Trading desk
- View orders created by the Portfolio Manager

### Trader

The Trader can:

- View the Trading Desk queue
- Send approved orders to a broker
- Review fills
- Record fills manually
- Simulate broker fills
- Complete order execution

### Operations

Operations can:

- View executed orders
- Review completed executions
- Send executed orders to post-trade
- Complete the order lifecycle

### Role-Based Access Control

RBAC is enforced server-side on state-changing endpoints.

Examples:

- A Trader cannot create Portfolio Manager orders
- A Portfolio Manager cannot send an order to the broker
- Operations cannot run Portfolio Manager compliance actions
- Only authorized roles can perform lifecycle transitions

### Pre-Trade Compliance Stub

`services/compliance_stub.py` provides a standardized compliance interface.

The demo compliance engine checks:

- Restricted symbols
- Maximum order size

It returns a pass/fail result with a reason.

The interface is designed so a real compliance/risk engine can replace the stub without changing the core order-management logic.

### Broker Integration Stub

`services/broker_stub.py` defines a standard `BrokerAdapter` interface for:

- Submit
- Cancel
- Poll fills

The project currently uses a simulated broker adapter for demonstrations.

### Audit Trail

Important actions are recorded with:

- Actor
- Role
- Action
- Entity
- Timestamp

Audit records include login, registration, order transitions, and security changes.

### Fills

A Fill represents confirmation of an executed order.

A fill records:

- Order
- Quantity
- Execution price
- Broker fill reference
- Execution timestamp

### UI

The React UI is role-aware:

- **Portfolio Manager:** order entry, own orders, compliance, send-to-trading
- **Trader:** trading desk, send-to-broker, fill actions
- **Operations:** post-trade queue
- **Admin:** administrative access and audit view

### Tests

`backend/tests/test_orders.py` covers:

- Complete order lifecycle
- RBAC behavior
- Compliance rules

---

## Deliberate Simplifications / Extensions

### CANCELLED Status

`CANCELLED` is an extension beyond the BRD.

It allows a Portfolio Manager or Trader to cancel an order before it reaches a broker.

### Admin Role

The BRD defines three business roles:

- Portfolio Manager
- Trader
- Operations

The project adds an `ADMIN` role for system administration.

### Audit Access

Audit log access is currently **ADMIN-only**. The BRD requires an audit trail but does not define a dedicated compliance-officer role.

### Simulated Fills

Fill recording is manual/simulated rather than a live broker feed.

The project defines the broker integration interface that could later be connected to a real broker feed.

### Order Types

The current order model does not include market/limit/stop order types because the BRD lifecycle does not specify them.

---

## Not Implemented

The following production features are intentionally outside this demo implementation:

- Real broker connectivity through FIX/REST
- Real compliance/risk engine
- Encryption at rest
- Production key management
- Regulatory data retention/archival policy
- Rate limiting
- Pagination
- WebSocket/streaming order updates
- Production secrets management
- Load testing
- Caching
- Production database deployment

---

## Demo Accounts

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | ADMIN |
| `pm1` | `pm12345` | PORTFOLIO_MANAGER |
| `trader1` | `trader123` | TRADER |
| `ops1` | `ops12345` | OPERATIONS |

> These credentials are for local/demo testing only and should not be used in a production deployment.

## Demo Securities

The seed script creates:

- AAPL
- MSFT
- TSLA
- SPY

---

## Complete OMS Demonstration

Use the following workflow to demonstrate the system:

```text
Portfolio Manager
       │
       │ Create BUY/SELL order
       ▼
      NEW
       │
       │ Compliance check
       ▼
   OK / FAIL
       │
       │ Send to Trading
       ▼
   TRADE_NEW
       │
       │ Trader sends to broker
       ▼
   EXECUTING
       │
       │ Simulated/recorded fill
       ▼
   EXECUTED
       │
       │ Operations sends to post-trade
       ▼
      DONE
```

### Step-by-Step Demo

1. Log in as `pm1`
2. Open **Orders**
3. Create a BUY order for AAPL
4. Run **compliance check**
5. Click **send to trading**
6. Sign out
7. Log in as `trader1`
8. Open **Orders / Trading Desk**
9. Click **send to broker**
10. Simulate or record the fill
11. Sign out
12. Log in as `ops1`
13. Open **Orders / Post-Trade Queue**
14. Click **send to post-trade**
15. Confirm the final order status is **DONE**
16. Log in as `admin`
17. Open **Audit** to review the recorded actions

---

## Quickest Way to Run — Docker

```bash
docker compose up --build
```

Backend:

```text
http://localhost:8000/docs
```

Frontend:

```text
http://localhost:5173
```

---

## Manual Setup — Windows

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --port 8000
```

Backend API documentation:

```text
http://localhost:8000/docs
```

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

The frontend uses:

```text
http://localhost:8000
```

by default.

It can be overridden with:

```text
VITE_API_URL
```

---

## Environment Configuration

### Database

The project uses SQLite by default:

```text
OMS_DATABASE_URL=sqlite:///./oms.db
```

For production, the database URL can be changed to a PostgreSQL database.

### Secret Key

For production, configure:

```text
OMS_SECRET_KEY=<long-random-secret>
```

Do not commit production secrets to GitHub.

---

## Tests

From the backend directory:

```powershell
pip install -r requirements.txt
pytest -v
```

---

## Architecture Notes

### RBAC

RBAC is enforced by FastAPI dependencies such as:

```text
auth.require_roles(...)
```

rather than relying only on frontend visibility.

### Order Visibility

The intended queues are:

- **Portfolio Manager:** own orders
- **Trader:** `TRADE_NEW` onward
- **Operations:** `EXECUTED` / `DONE`
- **Admin:** all orders

### Compliance and Broker Interfaces

Both compliance and broker integrations use a standardized interface plus a demo implementation.

This allows real external systems to be integrated later without rewriting the core order-management workflow.

---

## Project Structure

```text
oms-project/
├── docker-compose.yml
├── README.md
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── audit.py
│   │   ├── database.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── tickers.py
│   │   │   ├── orders.py
│   │   │   ├── fills.py
│   │   │   └── audit.py
│   │   └── services/
│   │       ├── broker_stub.py
│   │       └── compliance_stub.py
│   └── tests/
│       └── test_orders.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── index.css
        ├── main.jsx
        ├── api/
        │   └── client.js
        └── components/
            ├── Login.jsx
            ├── OrderForm.jsx
            ├── OrderTable.jsx
            ├── TickerPanel.jsx
            ├── FillsPanel.jsx
            └── AuditPanel.jsx
```

---

## Project Guidance

This project was developed under the guidance of:

**Pradeep**

## Acknowledgement

I sincerely thank **Pradeep** for his guidance and support throughout the development of this Order Management System project.

---

## Disclaimer

This project is an educational/demo Order Management System.

Broker execution, compliance checks, and trade fills are simulated and do not represent real financial transactions.
