
from pathlib import Path

import pytest


def lookup_project_repo():
    """Return the root of the git repository containing the current directory."""

    root = Path.cwd()
    while not (root / '.git').exists():
        root = root.parent
        if root == Path('/'):
            raise RuntimeError('No git repo found')

    return root


@pytest.fixture(scope='session')
def project_repo():
    yield lookup_project_repo()
