from unittest.mock import patch

from seed_failures import simulate_recovery_outcome


def test_simulate_recovery_outcome_recovered(make_transaction, db_session):
    transaction = make_transaction(
        transaction_id="txn_outcome_ok",
        amount=100000,
        failure_type="BANK_DOWNTIME",
        recovery_outcome="PENDING",
        recovered_amount=0,
    )

    with patch("seed_failures.random.random", return_value=0.0):
        result = simulate_recovery_outcome(transaction)

    assert result.recovery_outcome == "RECOVERED"
    assert result.recovered_amount == 100000


def test_simulate_recovery_outcome_failed(make_transaction, db_session):
    transaction = make_transaction(
        transaction_id="txn_outcome_fail",
        amount=100000,
        failure_type="INSUFFICIENT_FUNDS",
        recovery_outcome="PENDING",
        recovered_amount=0,
    )

    with patch("seed_failures.random.random", return_value=0.99):
        result = simulate_recovery_outcome(transaction)

    assert result.recovery_outcome == "FAILED"
    assert result.recovered_amount == 0


def test_simulate_recovery_outcome_uses_failure_type_probability(
    make_transaction,
):
    transaction = make_transaction(
        transaction_id="txn_outcome_boundary",
        amount=50000,
        failure_type="CART_ABANDONMENT",
    )

    # CART_ABANDONMENT threshold is 0.60 — 0.59 recovers, 0.60 fails
    with patch("seed_failures.random.random", return_value=0.59):
        recovered = simulate_recovery_outcome(transaction)
    assert recovered.recovery_outcome == "RECOVERED"

    transaction.recovery_outcome = "PENDING"
    transaction.recovered_amount = 0

    with patch("seed_failures.random.random", return_value=0.60):
        failed = simulate_recovery_outcome(transaction)
    assert failed.recovery_outcome == "FAILED"
