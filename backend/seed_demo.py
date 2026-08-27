"""Load the deterministic demo dataset into the configured database."""

from app.database.database import SessionLocal
from app.demo.seed_demo import seed_demo_dataset
from app.engine.metrics import calculate_metrics


def main():
    db = SessionLocal()
    try:
        result = seed_demo_dataset(db, replace=True)
        metrics = result["metrics"] or calculate_metrics(db)

        print("\nDemo dataset seeded.")
        print("-" * 48)
        print(f"Failed payments : {metrics['total_transactions']}")
        print(
            f"Recovered       : {metrics['recovered_transactions']} "
            f"(₹{metrics['total_recovered'] / 100:,.0f})"
        )
        print(f"Failed outcomes : {metrics['failed_recoveries']}")
        print(f"Pending         : {metrics['pending_recoveries']}")
        print(f"Success rate    : {metrics['recovery_rate']}%")
        print(f"Recovery yield  : {metrics['recovery_yield']}%")
        print("-" * 48)
    finally:
        db.close()


if __name__ == "__main__":
    main()
