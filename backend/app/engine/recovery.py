from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time

from app.core.razorpay_client import client
from app.core.email_client import send_recovery_email

from app.database.models import Transaction
from app.engine.state_manager import transition_state


def execute_recovery(
    db: Session,
    transaction: Transaction
):
    failure_type = transaction.failure_type

    if failure_type == "BANK_DOWNTIME":
        return handle_bank_downtime(db, transaction)

    if failure_type == "INSUFFICIENT_FUNDS":
        return handle_insufficient_funds(db, transaction)

    if failure_type == "CART_ABANDONMENT":
        return handle_cart_abandonment(db, transaction)

    return transition_state(
        db=db,
        transaction=transaction,
        new_state="TERMINATED",
        action="RECOVERY_REJECTED",
        reason="Unknown failure type"
    )


def handle_bank_downtime(
    db: Session,
    transaction: Transaction
):
    retry_time = datetime.utcnow() + timedelta(hours=6)

    transaction.retry_scheduled_at = retry_time

    return transition_state(
        db=db,
        transaction=transaction,
        new_state="RETRY_SCHEDULED",
        action="SCHEDULE_RETRY",
        reason="Bank/network failure; retry scheduled for 6 hours later"
    )


def handle_insufficient_funds(
    db: Session,
    transaction: Transaction
):
    transaction = transition_state(
        db=db,
        transaction=transaction,
        new_state="OUTREACH_PENDING",
        action="GENERATE_RECOVERY_OUTREACH",
        reason="Insufficient funds; preparing email recovery outreach"
    )

    email_result = send_recovery_email(transaction)

    if email_result["status"] == "sent":
        reason = (
            f"Recovery email sent to {email_result['to']} "
            f"({email_result['subject']})"
        )
    elif email_result["status"] == "simulated":
        reason = (
            f"Recovery email simulated to {email_result['to']} "
            f"({email_result['subject']}); {email_result['detail']}"
        )
    else:
        reason = (
            f"Recovery email failed for {email_result['to']}: "
            f"{email_result.get('detail', 'unknown error')}"
        )

    return transition_state(
        db=db,
        transaction=transaction,
        new_state="OUTREACH_SENT",
        action="SEND_RECOVERY_EMAIL",
        reason=reason,
    )


def handle_cart_abandonment(
    db: Session,
    transaction: Transaction
):
    original_amount = transaction.amount

    # Apply the optional 5% recovery discount
    discounted_amount = round(original_amount * 0.95)

    # Payment Links require a Unix timestamp for expiry
    expire_by = int(time.time()) + (24 * 60 * 60)

    reference_id = f"recovery_{transaction.transaction_id}"

    payment_link = client.payment_link.create({
        "amount": discounted_amount,
        "currency": "INR",
        "accept_partial": False,
        "expire_by": expire_by,
        "reference_id": reference_id,
        "description": "AI Revenue Recovery Payment",
        "reminder_enable": False
    })

    transaction.original_amount = original_amount
    transaction.discounted_amount = discounted_amount
    transaction.payment_link_id = payment_link["id"]
    transaction.payment_link_url = payment_link["short_url"]

    return transition_state(
        db=db,
        transaction=transaction,
        new_state="RECOVERY_LINK_CREATED",
        action="CREATE_PAYMENT_LINK",
        reason="Expiring Razorpay Payment Link created with 5% recovery discount"
    )