
import pytest

from pytest_cs import Status


def test_log_waiters(container):
    with container(image='hello-world', wait_status=Status.EXITED) as c:
        for waiter in c.log_waiters(timeout=5):
            with waiter as matcher:
                matcher.fnmatch_lines(["Hello from Docker!"])


@pytest.mark.xfail
def test_log_waiters_fail(container):
    with container(image='hello-world', wait_status=Status.EXITED) as c:
        for waiter in c.log_waiters(timeout=5):
            with waiter as matcher:
                matcher.fnmatch_lines(["Hullo from Docker!"])


def test_wait_for_log(container):
    with container(image='hello-world', wait_status=Status.EXITED) as c:
        c.wait_for_log("Hello from Docker!", timeout=5)


@pytest.mark.xfail
def test_wait_for_log_fail(container):
    with container(image='hello-world', wait_status=Status.EXITED) as c:
        c.wait_for_log("Hullo from Docker!", timeout=5)
