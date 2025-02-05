import os


def default_timeout() -> float:
    t = os.getenv("CROWDSEC_TEST_TIMEOUT", "20")
    try:
        return float(t)
    except ValueError:
        msg = f"Invalid CROWDSEC_TEST_TIMEOUT ({t}): must be a number (integer or float)"
        raise ValueError(msg) from None
