from app.demo.seed_demo import DEMO_PLAN, seed_demo_dataset
from app.engine.metrics import calculate_metrics


def test_seed_demo_dataset_is_deterministic(db_session):
    result = seed_demo_dataset(db_session, replace=True)

    assert result["status"] == "seeded"
    assert result["plan_size"] == len(DEMO_PLAN)
    assert result["created"] == len(DEMO_PLAN)

    metrics = calculate_metrics(db_session)

    assert metrics["total_transactions"] == 36
    assert metrics["recovered_transactions"] == 22
    assert metrics["failed_recoveries"] == 8
    assert metrics["pending_recoveries"] == 6
    assert (
        metrics["recovered_transactions"]
        + metrics["failed_recoveries"]
        + metrics["pending_recoveries"]
        == metrics["total_transactions"]
    )
    assert (
        metrics["total_recovered"] + metrics["still_at_risk"]
        == metrics["total_money_at_risk"]
    )
    assert metrics["recovery_rate"] == 61.1
    assert metrics["total_recovered"] > 0


def test_demo_seed_endpoint_respects_flag(client, monkeypatch, make_transaction):
    monkeypatch.setenv("ENABLE_DEMO_SEED", "false")

    # Sparse DB (<10) may bootstrap even when the flag is off.
    allowed = client.post("/demo/seed")
    assert allowed.status_code == 200
    assert allowed.json()["metrics"]["total_transactions"] == 36

    monkeypatch.setenv("ENABLE_DEMO_SEED", "false")
    for index in range(10):
        make_transaction(transaction_id=f"block_{index}")

    blocked = client.post("/demo/seed")
    assert blocked.status_code == 403

    monkeypatch.setenv("ENABLE_DEMO_SEED", "true")
    forced = client.post("/demo/seed")
    assert forced.status_code == 200
    assert forced.json()["metrics"]["total_transactions"] == 36
