from enum import Enum


class FailureType(str, Enum):
    BANK_DOWNTIME = "BANK_DOWNTIME"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    CART_ABANDONMENT = "CART_ABANDONMENT"
    UNKNOWN = "UNKNOWN"


def classify_failure(error_code: str) -> FailureType:
    error_code = error_code.upper()

    if error_code in {
        "GATEWAY_ERROR",
        "NETWORK_ERROR",
        "BANK_DOWNTIME"
    }:
        return FailureType.BANK_DOWNTIME

    if error_code in {
        "INSUFFICIENT_FUNDS",
        "CARD_DECLINED"
    }:
        return FailureType.INSUFFICIENT_FUNDS

    if error_code in {
        "CART_ABANDONMENT",
        "SOFT_DROPOFF"
    }:
        return FailureType.CART_ABANDONMENT

    return FailureType.UNKNOWN