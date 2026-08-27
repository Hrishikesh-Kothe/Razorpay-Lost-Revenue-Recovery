from sqlalchemy.orm import Session

from app.database.models import Transaction, AuditLog


def calculate_metrics(db: Session):
    transactions = db.query(Transaction).all()

    total_transactions = len(transactions)

    total_money_at_risk = sum(
        transaction.amount
        for transaction in transactions
    )

    total_recovered = sum(
        transaction.recovered_amount or 0
        for transaction in transactions
    )

    still_at_risk = sum(
        transaction.amount
        for transaction in transactions
        if transaction.recovery_outcome != "RECOVERED"
    )

    recovered_transactions = sum(
        1
        for transaction in transactions
        if transaction.recovery_outcome == "RECOVERED"
    )

    failed_recoveries = sum(
        1
        for transaction in transactions
        if transaction.recovery_outcome == "FAILED"
    )

    pending_recoveries = sum(
        1
        for transaction in transactions
        if transaction.recovery_outcome == "PENDING"
    )

    state_counts = {}

    for transaction in transactions:
        state = transaction.current_state

        state_counts[state] = (
            state_counts.get(state, 0) + 1
        )

    recovery_actions = (
        state_counts.get("RETRY_SCHEDULED", 0)
        + state_counts.get("OUTREACH_PENDING", 0)
        + state_counts.get("OUTREACH_SENT", 0)
        + state_counts.get("RECOVERY_LINK_CREATED", 0)
    )

    opted_out = state_counts.get("OPTED_OUT", 0)

    recovery_coverage = (
        recovery_actions / total_transactions * 100
        if total_transactions
        else 0
    )

    recovery_rate = (
        recovered_transactions / total_transactions * 100
        if total_transactions
        else 0
    )

    recovery_yield = (
        total_recovered / total_money_at_risk * 100
        if total_money_at_risk
        else 0
    )

    return {
        "total_transactions": total_transactions,
        "total_money_at_risk": total_money_at_risk,
        "still_at_risk": still_at_risk,
        "total_recovered": total_recovered,
        "recovered_transactions": recovered_transactions,
        "failed_recoveries": failed_recoveries,
        "pending_recoveries": pending_recoveries,
        "recovery_actions": recovery_actions,
        "opted_out": opted_out,
        "recovery_coverage": round(recovery_coverage, 1),
        "recovery_rate": round(recovery_rate, 1),
        "recovery_yield": round(recovery_yield, 1),
        "state_counts": state_counts,
    }


def _serialize_log(log: AuditLog):
    return {
        "id": log.id,
        "transaction_id": log.transaction_id,
        "previous_state": log.previous_state,
        "new_state": log.new_state,
        "action": log.action,
        "reason": log.reason,
        "created_at": (
            log.created_at.isoformat()
            if log.created_at
            else None
        ),
    }


def get_execution_logs(
    db: Session,
    limit: int = 25
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_log(log) for log in logs]


def _serialize_transaction_summary(transaction: Transaction):
    return {
        "transaction_id": transaction.transaction_id,
        "customer_id": transaction.customer_id,
        "amount": transaction.amount,
        "error_code": transaction.error_code,
        "failure_type": transaction.failure_type,
        "current_state": transaction.current_state,
        "attempt_count": transaction.attempt_count,
        "opt_out": transaction.opt_out,
        "recovery_outcome": transaction.recovery_outcome,
        "recovered_amount": transaction.recovered_amount,
        "created_at": (
            transaction.created_at.isoformat()
            if transaction.created_at
            else None
        ),
        "updated_at": (
            transaction.updated_at.isoformat()
            if transaction.updated_at
            else None
        ),
    }


def list_transactions(db: Session, limit: int | None = None):
    query = db.query(Transaction).order_by(
        Transaction.updated_at.desc(),
        Transaction.id.desc(),
    )

    if limit is not None:
        query = query.limit(limit)

    return [_serialize_transaction_summary(txn) for txn in query.all()]


def get_transaction_detail(db: Session, transaction_id: str):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )

    if not transaction:
        return None

    timeline = (
        db.query(AuditLog)
        .filter(AuditLog.transaction_id == transaction_id)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        .all()
    )

    return {
        "transaction": {
            "transaction_id": transaction.transaction_id,
            "customer_id": transaction.customer_id,
            "amount": transaction.amount,
            "error_code": transaction.error_code,
            "failure_type": transaction.failure_type,
            "current_state": transaction.current_state,
            "attempt_count": transaction.attempt_count,
            "opt_out": transaction.opt_out,
            "recovery_outcome": transaction.recovery_outcome,
            "recovered_amount": transaction.recovered_amount,
            "original_amount": transaction.original_amount,
            "discounted_amount": transaction.discounted_amount,
            "payment_link_id": transaction.payment_link_id,
            "payment_link_url": transaction.payment_link_url,
            "retry_scheduled_at": (
                transaction.retry_scheduled_at.isoformat()
                if transaction.retry_scheduled_at
                else None
            ),
            "created_at": (
                transaction.created_at.isoformat()
                if transaction.created_at
                else None
            ),
            "updated_at": (
                transaction.updated_at.isoformat()
                if transaction.updated_at
                else None
            ),
        },
        "timeline": [_serialize_log(log) for log in timeline],
    }