import random
import uuid

def simulate_recovery_outcome(transaction):
    """
    Simulate whether a recovery action eventually succeeds.

    This is demo/evaluation data only; it does not represent
    an actual customer payment.
    """

    recovery_probability = {
        "BANK_DOWNTIME": 0.70,
        "INSUFFICIENT_FUNDS": 0.45,
        "CART_ABANDONMENT": 0.60,
    }

    probability = recovery_probability.get(
        transaction.failure_type,
        0.50,
    )

    recovered = random.random() < probability

    if recovered:
        transaction.recovery_outcome = "RECOVERED"
        transaction.recovered_amount = transaction.amount
    else:
        transaction.recovery_outcome = "FAILED"
        transaction.recovered_amount = 0

    return transaction

from app.database.database import SessionLocal
from app.database.models import Transaction, AuditLog
from app.engine.graph import recovery_graph


FAILURE_DISTRIBUTION = (
    ["GATEWAY_ERROR"] * 20
    + ["INSUFFICIENT_FUNDS"] * 25
    + ["CART_ABANDONMENT"] * 5
)


def generate_transaction(index: int, error_code: str):
    transaction_id = f"batch_{index:03d}_{uuid.uuid4().hex[:6]}"

    customer_id = f"customer_{index:03d}"

    amount = random.choice([
        50000,
        75000,
        100000,
        150000,
        200000,
        250000,
    ])

    failure_type_map = {
        "GATEWAY_ERROR": "BANK_DOWNTIME",
        "INSUFFICIENT_FUNDS": "INSUFFICIENT_FUNDS",
        "CART_ABANDONMENT": "CART_ABANDONMENT",
    }

    failure_type = failure_type_map[error_code]

    transaction = Transaction(
        transaction_id=transaction_id,
        customer_id=customer_id,
        amount=amount,
        error_code=error_code,
        failure_type=failure_type,
        current_state="RECEIVED",
        attempt_count=0,
        opt_out=False,
        recovery_outcome="PENDING",
        recovered_amount=0,
)

    return transaction


def process_transaction(db, transaction):
    db.add(transaction)

    audit_log = AuditLog(
        transaction_id=transaction.transaction_id,
        previous_state=None,
        new_state="RECEIVED",
        action="BATCH_INGEST",
        reason="Synthetic batch failure generated for evaluation",
    )

    db.add(audit_log)

    db.commit()
    db.refresh(transaction)

    result = recovery_graph.invoke({
        "db": db,
        "transaction_id": transaction.transaction_id,
        "failure_type": transaction.failure_type,
        "policy_allowed": False,
        "policy_reason": "",
        "current_state": transaction.current_state,
    })

    db.refresh(transaction)
    
    transaction = simulate_recovery_outcome(
        transaction
)

    db.commit()
    db.refresh(transaction)

    return transaction


def simulate_recovery_outcome(transaction):
    recovery_probability = {
        "BANK_DOWNTIME": 0.70,
        "INSUFFICIENT_FUNDS": 0.45,
        "CART_ABANDONMENT": 0.60,
    }

    probability = recovery_probability.get(
        transaction.failure_type,
        0.50,
    )

    recovered = random.random() < probability

    if recovered:
        transaction.recovery_outcome = "RECOVERED"
        transaction.recovered_amount = transaction.amount
    else:
        transaction.recovery_outcome = "FAILED"
        transaction.recovered_amount = 0

    return transaction

def main():
    db = SessionLocal()

    try:
        random.shuffle(FAILURE_DISTRIBUTION)

        results = []

        print("\nStarting batch failure simulation...")
        print("-" * 60)

        for index, error_code in enumerate(
            FAILURE_DISTRIBUTION,
            start=1
        ):
            transaction = generate_transaction(
                index,
                error_code
            )

            transaction = process_transaction(
                db,
                transaction
            )

            results.append(transaction)

            print(
                f"[{index:02d}/50] "
                f"{transaction.transaction_id} | "
                f"{transaction.failure_type} | "
                f"{transaction.current_state}"
            )

        print("-" * 60)
        print("Batch simulation complete.\n")

        print("SUMMARY")
        print("-" * 60)

        for failure_type in [
            "BANK_DOWNTIME",
            "INSUFFICIENT_FUNDS",
            "CART_ABANDONMENT",
        ]:
            matching = [
                t for t in results
                if t.failure_type == failure_type
            ]

            print(
                f"{failure_type}: "
                f"{len(matching)}"
            )

        print("\nFinal states:")

        states = {}

        for transaction in results:
            states[transaction.current_state] = (
                states.get(transaction.current_state, 0) + 1
            )

        for state, count in states.items():
            print(f"{state}: {count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()