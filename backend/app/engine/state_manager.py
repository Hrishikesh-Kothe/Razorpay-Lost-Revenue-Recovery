from sqlalchemy.orm import Session

from app.database.models import Transaction, AuditLog
from app.engine.policy import check_policy


def transition_state(
    db: Session,
    transaction: Transaction,
    new_state: str,
    action: str,
    reason: str
):
    previous_state = transaction.current_state

    transaction.current_state = new_state

    audit_log = AuditLog(
        transaction_id=transaction.transaction_id,
        previous_state=previous_state,
        new_state=new_state,
        action=action,
        reason=reason
    )

    db.add(audit_log)
    db.commit()
    db.refresh(transaction)

    return transaction


def run_policy_check(
    db: Session,
    transaction: Transaction
):
    allowed, reason = check_policy(
        transaction.attempt_count,
        transaction.opt_out
    )

    if allowed:
        return transition_state(
            db=db,
            transaction=transaction,
            new_state="POLICY_APPROVED",
            action="POLICY_CHECK",
            reason=reason
        )

    return transition_state(
        db=db,
        transaction=transaction,
        new_state="TERMINATED",
        action="POLICY_BLOCKED",
        reason=reason
    )

def increment_attempt(
    db: Session,
    transaction: Transaction
):
    transaction.attempt_count += 1

    audit_log = AuditLog(
        transaction_id=transaction.transaction_id,
        previous_state=transaction.current_state,
        new_state=transaction.current_state,
        action="ATTEMPT_INCREMENTED",
        reason=f"Recovery attempt count increased to {transaction.attempt_count}"
    )

    db.add(audit_log)
    db.commit()
    db.refresh(transaction)

    return transaction