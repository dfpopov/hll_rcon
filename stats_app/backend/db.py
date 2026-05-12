"""Database connection layer for stats_app.

Reuses CRCON's PostgreSQL via DATABASE_URL env (set in compose.yaml).
Read-only access pattern: no schema migrations, no writes. SQLAlchemy
engine and sessionmaker exported for use in route handlers.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://rcon:password@postgres:5432/rcon")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency providing a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
