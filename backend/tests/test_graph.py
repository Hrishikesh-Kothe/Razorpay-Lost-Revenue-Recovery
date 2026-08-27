from unittest.mock import patch

from app.engine.graph import recovery_graph
from app.database.models import AuditLog, Transaction


def test_graph_exists():
    assert recovery_graph is not None


def _invoke(db_session, transaction):
    return recovery_graph.invoke({
        "db": db_session,
        "transaction_id": transaction.transaction_id,
        "failure_type": transaction.failure_type or "",
        "policy_allowed": False,
        "policy_reason": "",
        "current_state": transaction.current_state,
    })


def test_graph_bank_downtime_path(db_session, make_transaction):
    transaction = make_transaction(
        error_code="GATEWAY_ERROR",
        failure_type=None,
    )

    _invoke(db_session, transaction)
    db_session.refresh(transaction)

    assert transaction.failure_type == "BANK_DOWNTIME"
    assert transaction.current_state == "RETRY_SCHEDULED"
    assert transaction.attempt_count == 1
    assert transaction.retry_scheduled_at is not None


def test_graph_insufficient_funds_path(db_session, make_transaction):
    transaction = make_transaction(
        transaction_id="txn_funds_001",
        error_code="INSUFFICIENT_FUNDS",
    )

    _invoke(db_session, transaction)
    db_session.refresh(transaction)

    assert transaction.failure_type == "INSUFFICIENT_FUNDS"
    assert transaction.current_state == "OUTREACH_SENT"
    assert transaction.attempt_count == 1


def test_graph_cart_abandonment_path(db_session, make_transaction):
    transaction = make_transaction(
        transaction_id="txn_cart_graph_001",
        error_code="CART_ABANDONMENT",
        amount=200000,
    )

    mock_link = {
        "id": "plink_graph_001",
        "short_url": "https://rzp.io/i/graph001",
    }

    with patch(
        "app.engine.recovery.client.payment_link.create",
        return_value=mock_link,
    ):
        _invoke(db_session, transaction)

    db_session.refresh(transaction)

    assert transaction.failure_type == "CART_ABANDONMENT"
    assert transaction.current_state == "RECOVERY_LINK_CREATED"
    assert transaction.discounted_amount == 190000
    assert transaction.payment_link_id == "plink_graph_001"


def test_graph_unknown_failure_terminates(db_session, make_transaction):
    transaction = make_transaction(
        transaction_id="txn_unknown_001",
        error_code="NOT_A_REAL_CODE",
    )

    _invoke(db_session, transaction)
    db_session.refresh(transaction)

    assert transaction.failure_type == "UNKNOWN"
    assert transaction.current_state == "TERMINATED"
    assert transaction.attempt_count == 1


def test_graph_blocks_when_opted_out(db_session, make_transaction):
    transaction = make_transaction(
        transaction_id="txn_optout_graph",
        error_code="GATEWAY_ERROR",
        opt_out=True,
    )

    _invoke(db_session, transaction)
    db_session.refresh(transaction)

    assert transaction.current_state == "TERMINATED"
    assert transaction.attempt_count == 0

    actions = [
        log.action
        for log in db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .all()
    ]
    assert "POLICY_BLOCKED" in actions
    assert "SCHEDULE_RETRY" not in actions


def test_graph_blocks_when_max_attempts_reached(
    db_session,
    make_transaction,
):
    transaction = make_transaction(
        transaction_id="txn_max_graph",
        error_code="GATEWAY_ERROR",
        attempt_count=3,
    )

    _invoke(db_session, transaction)
    db_session.refresh(transaction)

    assert transaction.current_state == "TERMINATED"
    assert transaction.attempt_count == 3


def test_graph_writes_classification_audit(db_session, make_transaction):
    transaction = make_transaction(
        transaction_id="txn_audit_graph",
        error_code="NETWORK_ERROR",
    )

    _invoke(db_session, transaction)

    classify_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.transaction_id == transaction.transaction_id,
            AuditLog.action == "CLASSIFY_FAILURE",
        )
        .one()
    )
    assert classify_log.new_state == "CLASSIFIED"
    assert "BANK_DOWNTIME" in classify_log.reason
