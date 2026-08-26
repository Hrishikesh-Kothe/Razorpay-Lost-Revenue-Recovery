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

    return [
        {
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
        for log in logs
    ]