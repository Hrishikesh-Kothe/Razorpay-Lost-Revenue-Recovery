from unittest.mock import MagicMock, patch

from app.core.email_client import (
    compose_recovery_email,
    resolve_recipient,
    send_recovery_email,
)


class _Txn:
    def __init__(self):
        self.transaction_id = "txn_email_001"
        self.customer_id = "cust_42"
        self.amount = 250000
        self.failure_type = "INSUFFICIENT_FUNDS"
        self.error_code = "INSUFFICIENT_FUNDS"


def test_compose_recovery_email_is_formal_english():
    message = compose_recovery_email(_Txn())

    assert "txn_email_001" in message["subject"]
    assert "₹2,500.00" in message["text"]
    assert "Dear Customer" in message["text"]
    assert "STOP" in message["text"]
    assert "INSUFFICIENT_FUNDS" in message["html"]
    assert "Namaste" not in message["text"]
    assert "Aapki" not in message["text"]


def test_resolve_recipient_prefers_override(monkeypatch):
    monkeypatch.setenv("EMAIL_TO_OVERRIDE", "demo@student.edu")
    assert resolve_recipient("cust_42") == "demo@student.edu"


def test_send_recovery_email_simulates_without_api_key(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "")
    monkeypatch.setenv("EMAIL_SEND_LIVE", "false")
    monkeypatch.setenv("EMAIL_TO_OVERRIDE", "demo@student.edu")

    result = send_recovery_email(_Txn())

    assert result["status"] == "simulated"
    assert result["to"] == "demo@student.edu"
    assert "Action required" in result["subject"]


def test_send_recovery_email_simulates_when_live_disabled(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_SEND_LIVE", "false")
    monkeypatch.setenv("EMAIL_TO_OVERRIDE", "demo@student.edu")

    with patch("app.core.email_client.httpx.post") as post:
        result = send_recovery_email(_Txn())

    assert result["status"] == "simulated"
    assert "conserve" in result["detail"].lower()
    post.assert_not_called()


def test_send_recovery_email_posts_to_resend_when_live(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_SEND_LIVE", "true")
    monkeypatch.setenv("EMAIL_FROM", "Recovery <onboarding@resend.dev>")
    monkeypatch.setenv("EMAIL_TO_OVERRIDE", "demo@student.edu")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"id": "email_123"}

    with patch(
        "app.core.email_client.httpx.post",
        return_value=mock_response,
    ) as post:
        result = send_recovery_email(_Txn())

    assert result["status"] == "sent"
    assert result["provider_id"] == "email_123"
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://api.resend.com/emails"
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert kwargs["json"]["to"] == ["demo@student.edu"]
    assert "Dear Customer" in kwargs["json"]["text"]
