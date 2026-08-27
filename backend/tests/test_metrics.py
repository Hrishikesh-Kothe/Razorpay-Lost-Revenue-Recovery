from app.engine.metrics import (
    calculate_metrics,
    get_execution_logs,
    list_transactions,
)
from app.engine.state_manager import transition_state


def test_calculate_metrics_empty_database(db_session):
    metrics = calculate_metrics(db_session)

    assert metrics["total_transactions"] == 0
    assert metrics["total_money_at_risk"] == 0
    assert metrics["total_recovered"] == 0
    assert metrics["recovered_transactions"] == 0
    assert metrics["failed_recoveries"] == 0
    assert metrics["pending_recoveries"] == 0
    assert metrics["recovery_actions"] == 0
    assert metrics["opted_out"] == 0
    assert metrics["recovery_coverage"] == 0
    assert metrics["recovery_rate"] == 0
    assert metrics["recovery_yield"] == 0
    assert metrics["state_counts"] == {}


def test_calculate_metrics_with_mixed_transactions(
    db_session,
    make_transaction,
):
    make_transaction(
        transaction_id="txn_m_1",
        amount=100000,
        current_state="RETRY_SCHEDULED",
        recovery_outcome="RECOVERED",
        recovered_amount=100000,
    )
    make_transaction(
        transaction_id="txn_m_2",
        amount=50000,
        current_state="OUTREACH_SENT",
        recovery_outcome="FAILED",
        recovered_amount=0,
    )
    make_transaction(
        transaction_id="txn_m_3",
        amount=200000,
        current_state="RECOVERY_LINK_CREATED",
        recovery_outcome="PENDING",
        recovered_amount=0,
    )
    make_transaction(
        transaction_id="txn_m_4",
        amount=25000,
        current_state="OPTED_OUT",
        recovery_outcome="PENDING",
        recovered_amount=0,
        opt_out=True,
    )

    metrics = calculate_metrics(db_session)

    assert metrics["total_transactions"] == 4
    assert metrics["total_money_at_risk"] == 375000
    assert metrics["total_recovered"] == 100000
    assert metrics["recovered_transactions"] == 1
    assert metrics["failed_recoveries"] == 1
    assert metrics["pending_recoveries"] == 2
    assert metrics["recovery_actions"] == 3
    assert metrics["opted_out"] == 1
    assert metrics["recovery_coverage"] == 75.0
    assert metrics["recovery_rate"] == 25.0
    assert metrics["recovery_yield"] == 26.7
    assert metrics["state_counts"]["RETRY_SCHEDULED"] == 1
    assert metrics["state_counts"]["OUTREACH_SENT"] == 1
    assert metrics["state_counts"]["RECOVERY_LINK_CREATED"] == 1
    assert metrics["state_counts"]["OPTED_OUT"] == 1


def test_get_execution_logs_orders_newest_first(
    db_session,
    make_transaction,
):
    transaction = make_transaction(transaction_id="txn_logs_001")

    transition_state(
        db=db_session,
        transaction=transaction,
        new_state="CLASSIFIED",
        action="CLASSIFY_FAILURE",
        reason="first",
    )
    transition_state(
        db=db_session,
        transaction=transaction,
        new_state="POLICY_APPROVED",
        action="POLICY_CHECK",
        reason="second",
    )

    logs = get_execution_logs(db_session, limit=10)

    assert len(logs) >= 2
    assert logs[0]["action"] == "POLICY_CHECK"
    assert logs[1]["action"] == "CLASSIFY_FAILURE"
    assert "created_at" in logs[0]


def test_get_execution_logs_respects_limit(
    db_session,
    make_transaction,
):
    transaction = make_transaction(transaction_id="txn_logs_limit")

    for index in range(5):
        transition_state(
            db=db_session,
            transaction=transaction,
            new_state=f"STATE_{index}",
            action=f"ACTION_{index}",
            reason=f"reason_{index}",
        )

    logs = get_execution_logs(db_session, limit=2)

    assert len(logs) == 2


def test_metrics_endpoint(client, make_transaction):
    make_transaction(
        transaction_id="txn_api_metrics",
        amount=100000,
        current_state="RETRY_SCHEDULED",
        recovery_outcome="RECOVERED",
        recovered_amount=100000,
    )

    response = client.get("/metrics/")

    assert response.status_code == 200
    body = response.json()
    assert body["total_transactions"] == 1
    assert body["recovery_actions"] == 1
    assert body["recovery_rate"] == 100.0


def test_metrics_logs_endpoint(client, make_transaction, db_session):
    transaction = make_transaction(transaction_id="txn_api_logs")
    transition_state(
        db=db_session,
        transaction=transaction,
        new_state="CLASSIFIED",
        action="CLASSIFY_FAILURE",
        reason="classified",
    )

    response = client.get("/metrics/logs?limit=5")

    assert response.status_code == 200
    body = response.json()
    assert "logs" in body
    assert len(body["logs"]) >= 1


def test_transaction_detail_endpoint_returns_timeline(
    client,
    make_transaction,
    db_session,
):
    transaction = make_transaction(
        transaction_id="txn_detail_001",
        amount=100000,
        error_code="GATEWAY_ERROR",
        failure_type="BANK_DOWNTIME",
        current_state="RECEIVED",
    )

    transition_state(
        db=db_session,
        transaction=transaction,
        new_state="CLASSIFIED",
        action="CLASSIFY_FAILURE",
        reason="Failure classified as BANK_DOWNTIME",
    )
    transition_state(
        db=db_session,
        transaction=transaction,
        new_state="RETRY_SCHEDULED",
        action="SCHEDULE_RETRY",
        reason="retry scheduled",
    )

    response = client.get("/metrics/transactions/txn_detail_001")

    assert response.status_code == 200
    body = response.json()
    assert body["transaction"]["transaction_id"] == "txn_detail_001"
    assert body["transaction"]["failure_type"] == "BANK_DOWNTIME"
    assert body["transaction"]["current_state"] == "RETRY_SCHEDULED"
    assert len(body["timeline"]) == 2
    assert body["timeline"][0]["action"] == "CLASSIFY_FAILURE"
    assert body["timeline"][1]["action"] == "SCHEDULE_RETRY"


def test_transaction_detail_endpoint_not_found(client):
    response = client.get("/metrics/transactions/missing_txn")

    assert response.status_code == 404


def test_list_transactions_orders_newest_first(
    db_session,
    make_transaction,
):
    make_transaction(transaction_id="txn_list_old", amount=10000)
    make_transaction(transaction_id="txn_list_new", amount=20000)

    rows = list_transactions(db_session)

    assert len(rows) == 2
    assert rows[0]["transaction_id"] == "txn_list_new"
    assert rows[1]["transaction_id"] == "txn_list_old"
    assert rows[0]["amount"] == 20000
    assert "current_state" in rows[0]


def test_list_transactions_endpoint_respects_limit(
    client,
    make_transaction,
):
    for index in range(3):
        make_transaction(transaction_id=f"txn_limit_{index}")

    response = client.get("/metrics/transactions?limit=2")

    assert response.status_code == 200
    body = response.json()
    assert len(body["transactions"]) == 2

    all_response = client.get("/metrics/transactions")
    assert all_response.status_code == 200
    assert len(all_response.json()["transactions"]) == 3
