import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Transaction
from app.demo.seed_demo import seed_demo_dataset


router = APIRouter(prefix="/demo", tags=["Demo"])


def _demo_seed_enabled() -> bool:
    return os.getenv("ENABLE_DEMO_SEED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@router.post("/seed")
def seed_demo(
    replace: bool = Query(
        default=True,
        description="Replace existing rows before seeding",
    ),
    db: Session = Depends(get_db),
):
    txn_count = db.query(Transaction).count()
    bootstrap_ok = txn_count < 10

    if not _demo_seed_enabled() and not bootstrap_ok:
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo seed is disabled. "
                "Set ENABLE_DEMO_SEED=true on the API service, "
                "call this once, then turn it off."
            ),
        )

    return seed_demo_dataset(db, replace=replace)
