from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.engine.graph import recovery_graph

from app.database.database import get_db
from app.database.models import Transaction, AuditLog
from app.engine.classifier import classify_failure
from app.engine.recovery import execute_recovery

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class PaymentFailure(BaseModel):
    event: str
    transaction_id: str
    error_code: str
    amount: int
    customer_id: Optional[str] = None


@router.post("/razorpay")
def razorpay_webhook(
    payload: PaymentFailure,
    db: Session = Depends(get_db)
):
    # Check whether this transaction already exists
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_id == payload.transaction_id
        )
        .first()
    )

    # Avoid processing the same webhook twice
    if transaction:
        return {
            "status": "already_processed",
            "transaction_id": payload.transaction_id
        }

    # Classify the failure
    failure_type = classify_failure(payload.error_code)

    # Create transaction
    transaction = Transaction(
        transaction_id=payload.transaction_id,
        customer_id=payload.customer_id,
        amount=payload.amount,
        error_code=payload.error_code,
        failure_type=failure_type.value,
        current_state="RECEIVED",
        attempt_count=0,
        opt_out=False
    )

    db.add(transaction)

    # Create audit log
    audit_log = AuditLog(
        transaction_id=payload.transaction_id,
        previous_state=None,
        new_state="RECEIVED",
        action="INGEST_FAILURE",
        reason=f"Failure classified as {failure_type.value}"
    )

    db.add(audit_log)

    db.commit()
    db.refresh(transaction)

    graph_result = recovery_graph.invoke({
    "db": db,
    "transaction_id": transaction.transaction_id,
    "failure_type": transaction.failure_type,
    "policy_allowed": False,
    "policy_reason": "",
    "current_state": transaction.current_state
})

    db.refresh(transaction)

    return {
        "status": "processed",
        "transaction_id": payload.transaction_id,
        "failure_type": failure_type.value,
        "state": transaction.current_state
}

