from app.database.models import AuditLog
from app.engine.state_manager import (
    transition_state,
    run_policy_check,
    increment_attempt,
)


def test_transition_state_updates_state_and_writes_audit(
    db_session,
    make_transaction,
):
    transaction = make_transaction(current_state="RECEIVED")

    result = transition_state(
        db=db_session,
        transaction=transaction,
        new_state="CLASSIFIED",
        action="CLASSIFY_FAILURE",
        reason="Failure classified as BANK_DOWNTIME",
    )

    assert result.current_state == "CLASSIFIED"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .one()
    )
    assert audit.previous_state == "RECEIVED"
    assert audit.new_state == "CLASSIFIED"
    assert audit.action == "CLASSIFY_FAILURE"
    assert "BANK_DOWNTIME" in audit.reason


def test_run_policy_check_approves_eligible_transaction(
    db_session,
    make_transaction,
):
    transaction = make_transaction(attempt_count=0, opt_out=False)

    result = run_policy_check(db_session, transaction)

    assert result.current_state == "POLICY_APPROVED"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit.action == "POLICY_CHECK"
    assert audit.reason == "POLICY_APPROVED"


def test_increment_attempt_increases_count_and_audits(
    db_session,
    make_transaction,
):
    transaction = make_transaction(
        attempt_count=0,
        current_state="POLICY_APPROVED",
    )

    result = increment_attempt(db_session, transaction)

    assert result.attempt_count == 1

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "ATTEMPT_INCREMENTED")
        .one()
    )
    assert audit.new_state == "POLICY_APPROVED"
    assert "1" in audit.reason
