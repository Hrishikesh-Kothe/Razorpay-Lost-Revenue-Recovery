import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
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
        description="Replace existing demo_* rows before seeding",
    ),
    db: Session = Depends(get_db),
):
    if not _demo_seed_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo seed is disabled. "
                "Set ENABLE_DEMO_SEED=true on the API service, "
                "call this once, then turn it off."
            ),
        )

    return seed_demo_dataset(db, replace=replace)
