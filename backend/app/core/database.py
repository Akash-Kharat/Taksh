from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Create engine with sqlite connect_args to allow multithreading
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency generator that yields the database session context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
