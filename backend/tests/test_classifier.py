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


def test_network_error_is_bank_downtime():
    assert classify_failure("NETWORK_ERROR") == FailureType.BANK_DOWNTIME


def test_bank_downtime_code():
    assert classify_failure("BANK_DOWNTIME") == FailureType.BANK_DOWNTIME


def test_card_declined_is_insufficient_funds():
    assert classify_failure("CARD_DECLINED") == FailureType.INSUFFICIENT_FUNDS


def test_cart_abandonment():
    assert (
        classify_failure("CART_ABANDONMENT")
        == FailureType.CART_ABANDONMENT
    )


def test_soft_dropoff_is_cart_abandonment():
    assert classify_failure("SOFT_DROPOFF") == FailureType.CART_ABANDONMENT


def test_classifier_is_case_insensitive():
    assert classify_failure("gateway_error") == FailureType.BANK_DOWNTIME
    assert classify_failure("Insufficient_Funds") == FailureType.INSUFFICIENT_FUNDS


def test_empty_error_code_is_unknown():
    assert classify_failure("") == FailureType.UNKNOWN
