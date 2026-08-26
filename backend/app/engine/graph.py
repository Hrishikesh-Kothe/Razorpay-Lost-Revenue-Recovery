from typing import TypedDict, Any

from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, START, END

from app.database.models import Transaction
from app.engine.classifier import classify_failure
from app.engine.state_manager import (
    transition_state,
    run_policy_check,
    increment_attempt,
)
from app.engine.recovery import execute_recovery


class RecoveryState(TypedDict):
    db: Session
    transaction_id: str
    failure_type: str
    policy_allowed: bool
    policy_reason: str
    current_state: str


def get_transaction(state: RecoveryState) -> Transaction:
    transaction = (
        state["db"]
        .query(Transaction)
        .filter(
            Transaction.transaction_id == state["transaction_id"]
        )
        .first()
    )

    if not transaction:
        raise ValueError(
            f"Transaction {state['transaction_id']} not found"
        )

    return transaction


def classify_node(state: RecoveryState):
    db = state["db"]
    transaction = get_transaction(state)

    failure_type = classify_failure(
        transaction.error_code
    )

    transaction.failure_type = failure_type.value

    transaction = transition_state(
        db=db,
        transaction=transaction,
        new_state="CLASSIFIED",
        action="CLASSIFY_FAILURE",
        reason=f"Failure classified as {failure_type.value}"
    )

    return {
        "failure_type": failure_type.value,
        "current_state": transaction.current_state
    }


def policy_node(state: RecoveryState):
    db = state["db"]
    transaction = get_transaction(state)

    transaction = run_policy_check(
        db=db,
        transaction=transaction
    )

    allowed = transaction.current_state == "POLICY_APPROVED"

    return {
        "policy_allowed": allowed,
        "policy_reason": (
            "POLICY_APPROVED"
            if allowed
            else "POLICY_BLOCKED"
        ),
        "current_state": transaction.current_state
    }


def route_after_policy(state: RecoveryState):
    if state["policy_allowed"]:
        return "execute"

    return "end"


def execute_node(state: RecoveryState):
    db = state["db"]
    transaction = get_transaction(state)

    transaction = increment_attempt(
        db=db,
        transaction=transaction
    )

    transaction = execute_recovery(
        db=db,
        transaction=transaction
    )

    return {
        "current_state": transaction.current_state
    }


def build_recovery_graph():
    graph = StateGraph(RecoveryState)

    graph.add_node("classify", classify_node)
    graph.add_node("policy", policy_node)
    graph.add_node("execute", execute_node)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "policy")

    graph.add_conditional_edges(
        "policy",
        route_after_policy,
        {
            "execute": "execute",
            "end": END
        }
    )

    graph.add_edge("execute", END)

    return graph.compile()


recovery_graph = build_recovery_graph()