"""
Database configuration.

Uses SQLite for local development by default. Swap SQLALCHEMY_DATABASE_URL
for a Postgres/SQL Server DSN in production (financial-grade deployments
should not run on SQLite).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = os.getenv("OMS_DATABASE_URL", "sqlite:///./oms.db")

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
