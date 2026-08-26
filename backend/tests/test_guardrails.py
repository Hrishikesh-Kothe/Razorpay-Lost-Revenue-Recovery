from app.engine.policy import check_policy


def test_stop_blocks_recovery():
    allowed, reason = check_policy(0, True)

    assert allowed is False
    assert reason == "USER_OPTED_OUT"


def test_three_attempts_blocks_recovery():
    allowed, reason = check_policy(3, False)

    assert allowed is False
    assert reason == "MAX_ATTEMPTS_REACHED"


def test_two_attempts_still_allows_recovery():
    allowed, reason = check_policy(2, False)

    assert allowed is True
    assert reason == "POLICY_APPROVED"