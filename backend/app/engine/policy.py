MAX_ATTEMPTS = 3


def check_policy(
    attempt_count: int,
    opt_out: bool
) -> tuple[bool, str]:

    # STOP always wins
    if opt_out:
        return False, "USER_OPTED_OUT"

    # Policy runs before attempt increment, so counts 0, 1, and 2
    # are allowed (three executions). Count >= 3 blocks further recovery.
    if attempt_count >= MAX_ATTEMPTS:
        return False, "MAX_ATTEMPTS_REACHED"

    return True, "POLICY_APPROVED"
