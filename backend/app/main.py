from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, orders, tickers, fills, audit

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OMS API",
    description="Order Management System — core orders, tickers, fills, and RBAC.",
    version="0.1.0",
)

# Dev-friendly CORS. Lock this down to known origins before production use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickers.router)
app.include_router(orders.router)
app.include_router(fills.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok"}
