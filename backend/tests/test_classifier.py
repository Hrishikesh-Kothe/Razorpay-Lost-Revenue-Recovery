from app.engine.classifier import classify_failure, FailureType


def test_insufficient_funds():
    result = classify_failure("INSUFFICIENT_FUNDS")

    assert result == FailureType.INSUFFICIENT_FUNDS


def test_gateway_error():
    result = classify_failure("GATEWAY_ERROR")

    assert result == FailureType.BANK_DOWNTIME


def test_unknown_error():
    result = classify_failure("SOMETHING_RANDOM")

    assert result == FailureType.UNKNOWN