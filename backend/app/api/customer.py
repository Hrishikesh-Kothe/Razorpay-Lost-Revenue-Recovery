from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Transaction
from app.engine.state_manager import transition_state

router = APIRouter(
    prefix="/customer",
    tags=["Customer"]
)


class CustomerMessage(BaseModel):
    transaction_id: str
    message: str


@router.post("/message")
def customer_message(
    payload: CustomerMessage,
    db: Session = Depends(get_db)
):
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_id == payload.transaction_id
        )
        .first()
    )

    if not transaction:
        return {
            "status": "error",
            "message": "Transaction not found"
        }

    message = payload.message.strip().upper()

    if message == "STOP":
        transaction.opt_out = True

        transaction = transition_state(
            db=db,
            transaction=transaction,
            new_state="OPTED_OUT",
            action="USER_OPT_OUT",
            reason="Customer sent STOP"
        )

        return {
            "status": "opted_out",
            "transaction_id": transaction.transaction_id,
            "state": transaction.current_state
        }

    return {
        "status": "ignored",
        "message": "No opt-out keyword detected"
    }