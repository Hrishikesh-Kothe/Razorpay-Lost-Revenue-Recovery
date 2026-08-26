MAX_ATTEMPTS = 3


def check_policy(
    attempt_count: int,
    opt_out: bool
) -> tuple[bool, str]:

    # STOP always wins
    if opt_out:
        return False, "USER_OPTED_OUT"

    # Block if 3 recovery attempts have already happened
    if attempt_count >= MAX_ATTEMPTS:
        return False, "MAX_ATTEMPTS_REACHED"

    return True, "POLICY_APPROVED"