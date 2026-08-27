def test_customer_stop_opts_out(client, make_transaction, db_session):
    transaction = make_transaction(
        transaction_id="txn_stop_001",
        current_state="OUTREACH_PENDING",
    )

    response = client.post(
        "/customer/message",
        json={
            "transaction_id": "txn_stop_001",
            "message": "STOP",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "opted_out"
    assert body["state"] == "OPTED_OUT"

    db_session.refresh(transaction)
    assert transaction.opt_out is True
    assert transaction.current_state == "OPTED_OUT"


def test_customer_stop_is_case_insensitive_and_trims(
    client,
    make_transaction,
    db_session,
):
    transaction = make_transaction(
        transaction_id="txn_stop_002",
        current_state="RETRY_SCHEDULED",
    )

    response = client.post(
        "/customer/message",
        json={
            "transaction_id": "txn_stop_002",
            "message": "  stop  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "opted_out"

    db_session.refresh(transaction)
    assert transaction.opt_out is True


def test_customer_non_stop_message_is_ignored(client, make_transaction):
    make_transaction(
        transaction_id="txn_ignore_001",
        current_state="OUTREACH_PENDING",
    )

    response = client.post(
        "/customer/message",
        json={
            "transaction_id": "txn_ignore_001",
            "message": "RETRY",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ignored"


def test_customer_message_unknown_transaction(client):
    response = client.post(
        "/customer/message",
        json={
            "transaction_id": "does_not_exist",
            "message": "STOP",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == "Transaction not found"


def test_customer_message_rejects_missing_fields(client):
    response = client.post(
        "/customer/message",
        json={"transaction_id": "txn_only"},
    )

    assert response.status_code == 422
