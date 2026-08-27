from unittest.mock import patch

from app.database.models import AuditLog, Transaction


def test_webhook_processes_bank_downtime(client, db_session):
    response = client.post(
        "/webhooks/razorpay",
        json={
            "event": "payment.failed",
            "transaction_id": "txn_wh_bank_001",
            "error_code": "GATEWAY_ERROR",
            "amount": 150000,
            "customer_id": "cust_wh_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["failure_type"] == "BANK_DOWNTIME"
    assert body["state"] == "RETRY_SCHEDULED"

    transaction = (
        db_session.query(Transaction)
        .filter(Transaction.transaction_id == "txn_wh_bank_001")
        .one()
    )
    assert transaction.attempt_count == 1
    assert transaction.amount == 150000

    ingest = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == "txn_wh_bank_001",
            AuditLog.action == "INGEST_FAILURE",
        )
        .one()
    )
    assert ingest.new_state == "RECEIVED"


def test_webhook_processes_insufficient_funds(client, db_session):
    response = client.post(
        "/webhooks/razorpay",
        json={
            "event": "payment.failed",
            "transaction_id": "txn_wh_funds_001",
            "error_code": "INSUFFICIENT_FUNDS",
            "amount": 50000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["failure_type"] == "INSUFFICIENT_FUNDS"
    assert body["state"] == "OUTREACH_SENT"


def test_webhook_processes_cart_abandonment_with_mocked_link(
    client,
    db_session,
):
    mock_link = {
        "id": "plink_wh_001",
        "short_url": "https://rzp.io/i/wh001",
    }

    with patch(
        "app.engine.recovery.client.payment_link.create",
        return_value=mock_link,
    ):
        response = client.post(
            "/webhooks/razorpay",
            json={
                "event": "payment.failed",
                "transaction_id": "txn_wh_cart_001",
                "error_code": "CART_ABANDONMENT",
                "amount": 100000,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["failure_type"] == "CART_ABANDONMENT"
    assert body["state"] == "RECOVERY_LINK_CREATED"

    transaction = (
        db_session.query(Transaction)
        .filter(Transaction.transaction_id == "txn_wh_cart_001")
        .one()
    )
    assert transaction.payment_link_id == "plink_wh_001"
    assert transaction.discounted_amount == 95000


def test_webhook_is_idempotent(client, db_session):
    payload = {
        "event": "payment.failed",
        "transaction_id": "txn_wh_dup_001",
        "error_code": "GATEWAY_ERROR",
        "amount": 100000,
    }

    first = client.post("/webhooks/razorpay", json=payload)
    second = client.post("/webhooks/razorpay", json=payload)

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"

    count = (
        db_session.query(Transaction)
        .filter(Transaction.transaction_id == "txn_wh_dup_001")
        .count()
    )
    assert count == 1


def test_webhook_rejects_missing_required_fields(client):
    response = client.post(
        "/webhooks/razorpay",
        json={
            "event": "payment.failed",
            "transaction_id": "txn_invalid_001",
        },
    )

    assert response.status_code == 422


def test_webhook_rejects_invalid_amount_type(client):
    response = client.post(
        "/webhooks/razorpay",
        json={
            "event": "payment.failed",
            "transaction_id": "txn_invalid_002",
            "error_code": "GATEWAY_ERROR",
            "amount": "not-an-int",
        },
    )

    assert response.status_code == 422


def test_webhook_rejects_empty_body(client):
    response = client.post("/webhooks/razorpay", json={})

    assert response.status_code == 422
