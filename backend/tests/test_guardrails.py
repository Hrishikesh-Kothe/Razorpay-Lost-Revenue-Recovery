from app.engine.policy import check_policy
from app.engine.state_manager import run_policy_check
from app.database.models import AuditLog


def test_stop_blocks_recovery():
    allowed, reason = check_policy(0, True)

    assert allowed is False
    assert reason == "USER_OPTED_OUT"


def test_three_attempts_blocks_recovery():
    allowed, reason = check_policy(3, False)

    assert allowed is False
    assert reason == "MAX_ATTEMPTS_REACHED"


def test_two_attempts_still_allows_recovery():
    allowed, reason = check_policy(2, False)

    assert allowed is True
    assert reason == "POLICY_APPROVED"


def test_run_policy_check_terminates_when_max_attempts_reached(
    db_session,
    make_transaction,
):
    transaction = make_transaction(attempt_count=3)

    result = run_policy_check(db_session, transaction)

    assert result.current_state == "TERMINATED"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit.action == "POLICY_BLOCKED"
    assert audit.reason == "MAX_ATTEMPTS_REACHED"


def test_run_policy_check_terminates_when_opted_out(
    db_session,
    make_transaction,
):
    transaction = make_transaction(opt_out=True)

    result = run_policy_check(db_session, transaction)

    assert result.current_state == "TERMINATED"

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction.transaction_id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit.action == "POLICY_BLOCKED"
    assert audit.reason == "USER_OPTED_OUT"
