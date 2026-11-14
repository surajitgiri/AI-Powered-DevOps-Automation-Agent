from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Use NullPool to avoid PgBouncer/psycopg3 rollback conflicts with Neon
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all database models
Base = declarative_base()

# Database dependency
def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()