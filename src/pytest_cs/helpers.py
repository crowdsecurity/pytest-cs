import os


def get_timeout(default=20):
    t = os.getenv('CROWDSEC_TEST_TIMEOUT', default)
    try:
        return int(t)
    except (ValueError, TypeError):
        raise Exception(f"Invalid CROWDSEC_TEST_TIMEOUT ({t}): must be an integer") from None
