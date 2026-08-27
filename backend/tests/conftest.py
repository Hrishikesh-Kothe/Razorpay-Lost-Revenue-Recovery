import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.database.models import Transaction
from app.main import app


@pytest.fixture(autouse=True)
def _isolate_email_env(monkeypatch):
    # Keep suite offline unless a test explicitly sets EMAIL_API_KEY
    monkeypatch.delenv("EMAIL_API_KEY", raising=False)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def make_transaction(db_session):
    def _make_transaction(**overrides):
        values = {
            "transaction_id": "txn_test_001",
            "customer_id": "cust_001",
            "amount": 100000,
            "error_code": "GATEWAY_ERROR",
            "failure_type": None,
            "current_state": "RECEIVED",
            "attempt_count": 0,
            "opt_out": False,
            "recovery_outcome": "PENDING",
            "recovered_amount": 0,
        }
        values.update(overrides)

        transaction = Transaction(**values)
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        return transaction

    return _make_transaction
