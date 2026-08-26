from app.engine.policy import check_policy


def test_policy_allows_first_attempt():
    allowed, reason = check_policy(0, False)

    assert allowed is True
    assert reason == "POLICY_APPROVED"


def test_policy_allows_second_attempt():
    allowed, reason = check_policy(1, False)

    assert allowed is True
    assert reason == "POLICY_APPROVED"


def test_policy_blocks_third_attempt():
    allowed, reason = check_policy(3, False)

    assert allowed is False
    assert reason == "MAX_ATTEMPTS_REACHED"


def test_policy_blocks_opt_out():
    allowed, reason = check_policy(0, True)

    assert allowed is False
    assert reason == "USER_OPTED_OUT"


def test_opt_out_wins_over_attempt_count():
    allowed, reason = check_policy(3, True)

    assert allowed is False
    assert reason == "USER_OPTED_OUT"