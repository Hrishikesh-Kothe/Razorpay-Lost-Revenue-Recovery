from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime

from app.database.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False)
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=False)
    action = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(String, nullable=True)

    amount = Column(Integer, nullable=False)
    payment_link_id = Column(String, nullable=True)
    payment_link_url = Column(String, nullable=True)

    recovery_outcome = Column(
    String,
    default="PENDING",
    nullable=False
)

    recovered_amount = Column(
        Integer,
        default=0,
        nullable=False
)
    original_amount = Column(Integer, nullable=True)
    discounted_amount = Column(Integer, nullable=True)

    failure_type = Column(String, nullable=True)
    error_code = Column(String, nullable=True)

    attempt_count = Column(Integer, default=0, nullable=False)
    opt_out = Column(Boolean, default=False, nullable=False)

    current_state = Column(
        String,
        default="RECEIVED",
        nullable=False
    )

    retry_scheduled_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )