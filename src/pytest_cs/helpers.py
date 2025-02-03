import os


def default_timeout() -> float:
    t = os.getenv("CROWDSEC_TEST_TIMEOUT", "20")
    try:
        return float(t)
    except (ValueError, TypeError):
        raise Exception(f"Invalid CROWDSEC_TEST_TIMEOUT ({t}): must be an integer or float") from None
