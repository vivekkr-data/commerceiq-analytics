"""PostgreSQL connection configuration from environment variables."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine import URL


def database_configured() -> bool:
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    return all(os.getenv(name) for name in required)


def create_database_engine() -> Engine:
    if not database_configured():
        raise RuntimeError("PostgreSQL credentials are incomplete")
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
    )
    return create_engine(url, pool_pre_ping=True)
