from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.engine.metrics import calculate_metrics, get_execution_logs


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
