from datetime import datetime, timedelta
from unittest.mock import patch

from app.engine.recovery import (
    execute_recovery,
    handle_bank_downtime,
    handle_insufficient_funds,
    handle_cart_abandonment,
)
from app.database.models import AuditLog


def test_bank_downtime_schedules_retry(db_session, make_transaction):
    transaction = make_transaction(
        failure_type="BANK_DOWNTIME",
        current_state="POLICY_APPROVED",
    )

    before = datetime.utcnow()
    result = handle_bank_downtime(db_session, transaction)
    after = datetime.utcnow()

    assert result.current_state == "RETRY_SCHEDULED"
    assert result.retry_scheduled_at is not None
    assert before + timedelta(hours=5, minutes=59) <= result.retry_scheduled_at
    assert result.retry_scheduled_at <= after + timedelta(hours=6, minutes=1)

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit.action == "SCHEDULE_RETRY"


def test_insufficient_funds_sends_outreach_email(
    db_session,
    make_transaction,
):
    transaction = make_transaction(
        failure_type="INSUFFICIENT_FUNDS",
        error_code="INSUFFICIENT_FUNDS",
        current_state="POLICY_APPROVED",
        customer_id="cust_email_001",
    )

    result = handle_insufficient_funds(db_session, transaction)

    assert result.current_state == "OUTREACH_SENT"

    actions = [
        log.action
        for log in db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.asc())
        .all()
    ]
    assert "GENERATE_RECOVERY_OUTREACH" in actions
    assert "SEND_RECOVERY_EMAIL" in actions

    send_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.transaction_id,
            AuditLog.action == "SEND_RECOVERY_EMAIL",
        )
        .one()
    )
    assert "simulated" in send_log.reason.lower() or "sent" in send_log.reason.lower()


def test_cart_abandonment_creates_discounted_payment_link(
    db_session,
    make_transaction,
):
    transaction = make_transaction(
        transaction_id="txn_cart_001",
        failure_type="CART_ABANDONMENT",
        error_code="CART_ABANDONMENT",
        amount=100000,
        current_state="POLICY_APPROVED",
    )

    mock_link = {
        "id": "plink_test_001",
        "short_url": "https://rzp.io/i/test001",
    }

    with patch(
        "app.engine.recovery.client.payment_link.create",
        return_value=mock_link,
    ) as create_link:
        result = handle_cart_abandonment(db_session, transaction)

    create_link.assert_called_once()
    payload = create_link.call_args[0][0]
    assert payload["amount"] == 95000
    assert payload["currency"] == "INR"
    assert payload["accept_partial"] is False
    assert payload["reference_id"] == "recovery_txn_cart_001"

    assert result.current_state == "RECOVERY_LINK_CREATED"
    assert result.original_amount == 100000
    assert result.discounted_amount == 95000
    assert result.payment_link_id == "plink_test_001"
    assert result.payment_link_url == "https://rzp.io/i/test001"


def test_unknown_failure_terminates(db_session, make_transaction):
    transaction = make_transaction(
        failure_type="UNKNOWN",
        error_code="SOMETHING_RANDOM",
        current_state="POLICY_APPROVED",
    )

    result = execute_recovery(db_session, transaction)

    assert result.current_state == "TERMINATED"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit.action == "RECOVERY_REJECTED"


def test_execute_recovery_routes_bank_downtime(
    db_session,
    make_transaction,
):
    transaction = make_transaction(
        failure_type="BANK_DOWNTIME",
        current_state="POLICY_APPROVED",
    )

    result = execute_recovery(db_session, transaction)

    assert result.current_state == "RETRY_SCHEDULED"
