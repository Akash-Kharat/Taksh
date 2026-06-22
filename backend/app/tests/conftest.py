import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import tempfile
from pathlib import Path
from app.core.config import settings

# Create temporary directory for tests to prevent ChromaDB cross-test pollution
temp_chroma_dir = tempfile.TemporaryDirectory()
settings.CHROMA_DIR = Path(temp_chroma_dir.name)
settings.MOCK_EMBEDDINGS = True

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

SQLALCHEMY_DATABASE_URL = "sqlite:///file:testdb?mode=memory&cache=shared"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
    poolclass=NullPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch SessionLocal globally for background tasks to use the test database
import app.core.database
app.core.database.SessionLocal = TestingSessionLocal

from app.main import app
from app.core.database import Base, get_db


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    keep_alive_conn = engine.connect()
    Base.metadata.create_all(bind=engine)
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    try:
        keep_alive_conn.close()
    except Exception:
        pass

@pytest.fixture
def db_session() -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    try:
        transaction.rollback()
    except Exception:
        pass
    try:
        connection.close()
    except Exception:
        pass

@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    old_value = settings.ENABLE_PROVIDER_HEALTH_CHECKS
    settings.ENABLE_PROVIDER_HEALTH_CHECKS = False
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        settings.ENABLE_PROVIDER_HEALTH_CHECKS = old_value
        app.dependency_overrides.clear()
