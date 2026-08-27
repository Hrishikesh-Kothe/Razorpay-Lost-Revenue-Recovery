"""
Deterministic demo dataset for video / judge walkthroughs.

Creates a fixed mix of recovered, failed, and pending recoveries so
dashboard metrics stay stable and easy to narrate.
"""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.database.models import AuditLog, Transaction
from app.engine.graph import recovery_graph
from app.engine.metrics import calculate_metrics


# Fixed demo plan: 36 failures → 22 recovered / 8 failed / 6 pending
# Amounts are in paise (₹1 = 100).
DEMO_PLAN = [
    # BANK_DOWNTIME (GATEWAY_ERROR) — 18
    ("demo_bank_01", "GATEWAY_ERROR", 149900, "RECOVERED"),
    ("demo_bank_02", "GATEWAY_ERROR", 99900, "RECOVERED"),
    ("demo_bank_03", "GATEWAY_ERROR", 199900, "RECOVERED"),
    ("demo_bank_04", "GATEWAY_ERROR", 74900, "RECOVERED"),
    ("demo_bank_05", "GATEWAY_ERROR", 249900, "RECOVERED"),
    ("demo_bank_06", "GATEWAY_ERROR", 129900, "RECOVERED"),
    ("demo_bank_07", "GATEWAY_ERROR", 89900, "RECOVERED"),
    ("demo_bank_08", "GATEWAY_ERROR", 159900, "RECOVERED"),
    ("demo_bank_09", "GATEWAY_ERROR", 109900, "RECOVERED"),
    ("demo_bank_10", "GATEWAY_ERROR", 179900, "RECOVERED"),
    ("demo_bank_11", "GATEWAY_ERROR", 59900, "RECOVERED"),
    ("demo_bank_12", "GATEWAY_ERROR", 219900, "RECOVERED"),
    ("demo_bank_13", "GATEWAY_ERROR", 139900, "FAILED"),
    ("demo_bank_14", "GATEWAY_ERROR", 84900, "FAILED"),
    ("demo_bank_15", "GATEWAY_ERROR", 169900, "FAILED"),
    ("demo_bank_16", "GATEWAY_ERROR", 119900, "PENDING"),
    ("demo_bank_17", "GATEWAY_ERROR", 94900, "PENDING"),
    ("demo_bank_18", "GATEWAY_ERROR", 189900, "PENDING"),
    # INSUFFICIENT_FUNDS — 12
    ("demo_funds_01", "INSUFFICIENT_FUNDS", 99900, "RECOVERED"),
    ("demo_funds_02", "INSUFFICIENT_FUNDS", 149900, "RECOVERED"),
    ("demo_funds_03", "INSUFFICIENT_FUNDS", 79900, "RECOVERED"),
    ("demo_funds_04", "INSUFFICIENT_FUNDS", 199900, "RECOVERED"),
    ("demo_funds_05", "INSUFFICIENT_FUNDS", 64900, "RECOVERED"),
    ("demo_funds_06", "INSUFFICIENT_FUNDS", 129900, "RECOVERED"),
    ("demo_funds_07", "INSUFFICIENT_FUNDS", 109900, "FAILED"),
    ("demo_funds_08", "INSUFFICIENT_FUNDS", 89900, "FAILED"),
    ("demo_funds_09", "INSUFFICIENT_FUNDS", 159900, "FAILED"),
    ("demo_funds_10", "INSUFFICIENT_FUNDS", 74900, "FAILED"),
    ("demo_funds_11", "INSUFFICIENT_FUNDS", 119900, "PENDING"),
    ("demo_funds_12", "INSUFFICIENT_FUNDS", 179900, "PENDING"),
    # CART_ABANDONMENT — 6
    ("demo_cart_01", "CART_ABANDONMENT", 249900, "RECOVERED"),
    ("demo_cart_02", "CART_ABANDONMENT", 149900, "RECOVERED"),
    ("demo_cart_03", "CART_ABANDONMENT", 99900, "RECOVERED"),
    ("demo_cart_04", "CART_ABANDONMENT", 199900, "RECOVERED"),
    ("demo_cart_05", "CART_ABANDONMENT", 129900, "FAILED"),
    ("demo_cart_06", "CART_ABANDONMENT", 179900, "PENDING"),
]


def _apply_outcome(transaction: Transaction, outcome: str) -> None:
    if outcome == "RECOVERED":
        transaction.recovery_outcome = "RECOVERED"
        transaction.recovered_amount = transaction.amount
    elif outcome == "FAILED":
        transaction.recovery_outcome = "FAILED"
        transaction.recovered_amount = 0
    else:
        transaction.recovery_outcome = "PENDING"
        transaction.recovered_amount = 0


def _clear_all_rows(db: Session) -> int:
    deleted_logs = db.query(AuditLog).delete(synchronize_session=False)
    deleted_txns = db.query(Transaction).delete(synchronize_session=False)
    db.commit()
    return deleted_txns + deleted_logs


def _process_one(
    db: Session,
    transaction_id: str,
    error_code: str,
    amount: int,
    outcome: str,
    index: int,
) -> Transaction:
    transaction = Transaction(
        transaction_id=transaction_id,
        customer_id=f"customer_demo_{index:02d}",
        amount=amount,
        error_code=error_code,
        failure_type=None,
        current_state="RECEIVED",
        attempt_count=0,
        opt_out=False,
        recovery_outcome="PENDING",
        recovered_amount=0,
    )
    db.add(transaction)
    db.add(
        AuditLog(
            transaction_id=transaction_id,
            previous_state=None,
            new_state="RECEIVED",
            action="DEMO_INGEST",
            reason="Deterministic demo failure for walkthrough",
        )
    )
    db.commit()
    db.refresh(transaction)

    mock_link = {
        "id": f"plink_mock_{transaction_id}",
        "short_url": f"https://rzp.io/i/mock/{transaction_id}",
    }

    with patch(
        "app.engine.recovery.client.payment_link.create",
        return_value=mock_link,
    ):
        recovery_graph.invoke({
            "db": db,
            "transaction_id": transaction.transaction_id,
            "failure_type": transaction.failure_type or "",
            "policy_allowed": False,
            "policy_reason": "",
            "current_state": transaction.current_state,
        })

    db.refresh(transaction)
    _apply_outcome(transaction, outcome)
    db.commit()
    db.refresh(transaction)
    return transaction


def seed_demo_dataset(db: Session, replace: bool = True) -> dict:
    cleared = 0
    if replace:
        cleared = _clear_all_rows(db)

    for index, (txn_id, error_code, amount, outcome) in enumerate(
        DEMO_PLAN,
        start=1,
    ):
        _process_one(db, txn_id, error_code, amount, outcome, index)

    metrics = calculate_metrics(db)
    return {
        "status": "seeded",
        "plan_size": len(DEMO_PLAN),
        "created": len(DEMO_PLAN),
        "cleared_rows": cleared,
        "metrics": metrics,
    }
