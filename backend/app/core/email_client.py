"""
Recovery email outreach via Resend HTTP API.

Uses httpx (already in requirements).

Credit protection:
  Real Resend calls run only when EMAIL_SEND_LIVE=true AND EMAIL_API_KEY is set.
  Otherwise the send is simulated (full audit trail, zero provider credits).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"


def _amount_rupees(amount_paise: int) -> str:
    return f"₹{(amount_paise / 100):,.2f}"


def _live_send_enabled() -> bool:
    return os.getenv("EMAIL_SEND_LIVE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def resolve_recipient(customer_id: str | None) -> str:
    override = os.getenv("EMAIL_TO_OVERRIDE", "").strip()
    if override:
        return override

    default_to = os.getenv("EMAIL_DEFAULT_TO", "").strip()
    if default_to:
        return default_to

    if customer_id:
        safe = "".join(
            ch if ch.isalnum() or ch in "._-" else "_"
            for ch in customer_id
        )
        return f"{safe}@example.com"

    return "customer@example.com"


def compose_recovery_email(transaction) -> dict[str, str]:
    amount = _amount_rupees(transaction.amount or 0)
    txn_id = transaction.transaction_id
    failure = transaction.failure_type or transaction.error_code or "payment failure"

    subject = f"Action required: incomplete payment {txn_id}"

    text = (
        f"Dear Customer,\n\n"
        f"We were unable to complete your payment of {amount} "
        f"(reason: {failure}).\n\n"
        f"Transaction reference: {txn_id}\n\n"
        f"To complete this payment, you may:\n"
        f"1. Retry using an alternate method such as UPI\n"
        f"2. Schedule a promise-to-pay date\n\n"
        f"If you no longer wish to receive recovery emails, reply with: STOP\n\n"
        f"Kind regards,\n"
        f"Revenue Recovery Engine\n"
    )

    html = (
        f"<p>Dear Customer,</p>"
        f"<p>We were unable to complete your payment of "
        f"<strong>{amount}</strong> "
        f"(reason: <code>{failure}</code>).</p>"
        f"<p>Transaction reference: <code>{txn_id}</code></p>"
        f"<p>To complete this payment, you may:</p>"
        f"<ol>"
        f"<li>Retry using an alternate method such as UPI</li>"
        f"<li>Schedule a promise-to-pay date</li>"
        f"</ol>"
        f"<p>If you no longer wish to receive recovery emails, "
        f"reply with: <strong>STOP</strong></p>"
        f"<p>Kind regards,<br/>Revenue Recovery Engine</p>"
    )

    return {
        "subject": subject,
        "text": text,
        "html": html,
    }


def send_recovery_email(transaction) -> dict[str, Any]:
    """
    Send recovery outreach email.

    Returns a result dict:
      status: "sent" | "simulated" | "error"
      to, subject, provider_id?, detail?
    """
    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    from_email = os.getenv(
        "EMAIL_FROM",
        "Revenue Recovery <onboarding@resend.dev>",
    ).strip()
    to_email = resolve_recipient(transaction.customer_id)
    message = compose_recovery_email(transaction)

    if not api_key:
        return {
            "status": "simulated",
            "to": to_email,
            "subject": message["subject"],
            "detail": "EMAIL_API_KEY not set; email not sent to provider",
        }

    if not _live_send_enabled():
        return {
            "status": "simulated",
            "to": to_email,
            "subject": message["subject"],
            "detail": (
                "EMAIL_SEND_LIVE is not enabled; "
                "email simulated to conserve provider credits"
            ),
        }

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": message["subject"],
        "text": message["text"],
        "html": message["html"],
    }

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "status": "sent",
            "to": to_email,
            "subject": message["subject"],
            "provider_id": data.get("id"),
            "detail": "Sent via Resend",
        }
    except Exception as exc:
        return {
            "status": "error",
            "to": to_email,
            "subject": message["subject"],
            "detail": str(exc),
        }
