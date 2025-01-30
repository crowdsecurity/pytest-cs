import os

import pytest


@pytest.fixture
def must_be_root() -> None:
    if os.geteuid() != 0:
        pytest.fail("This test must be run as root")


@pytest.fixture
def must_be_nonroot() -> None:
    if os.geteuid() == 0:
        pytest.fail("This test must be run as non-root")
