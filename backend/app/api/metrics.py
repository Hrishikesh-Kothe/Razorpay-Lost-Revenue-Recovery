from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.engine.metrics import (
    calculate_metrics,
    get_execution_logs,
    get_transaction_detail,
    list_transactions,
)


router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/")
def get_metrics(db: Session = Depends(get_db)):
    return calculate_metrics(db)


@router.get("/logs")
def get_logs(
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
):
    return {"logs": get_execution_logs(db, limit)}


@router.get("/transactions")
def get_transactions(
    limit: int | None = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return {"transactions": list_transactions(db, limit)}


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    detail = get_transaction_detail(db, transaction_id)

    if not detail:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return detail
