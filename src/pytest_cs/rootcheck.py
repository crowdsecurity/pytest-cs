import os

import pytest


@pytest.fixture(scope='session')
def must_be_root():
    if os.geteuid() != 0:
        pytest.fail('This test must be run as root')


@pytest.fixture(scope='session')
def must_be_nonroot():
    if os.geteuid() == 0:
        pytest.fail('This test must be run as non-root')
