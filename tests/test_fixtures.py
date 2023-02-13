
import pytest

from pytest_cs import log_waiters, wait_for_log, Status


def test_log_waiters(container):
    with container(image='hello-world', wait_status=Status.EXITED) as cont:
        for waiter in log_waiters(cont, timeout=5):
            with waiter as matcher:
                matcher.fnmatch_lines(["Hello from Docker!"])


@pytest.mark.xfail
def test_log_waiters_fail(container):
    with container(image='hello-world', wait_status=Status.EXITED) as cont:
        for waiter in log_waiters(cont, timeout=5):
            with waiter as matcher:
                matcher.fnmatch_lines(["Hullo from Docker!"])


def test_wait_for_log(container):
    with container(image='hello-world', wait_status=Status.EXITED) as cont:
        wait_for_log(cont, "Hello from Docker!", timeout=5)


@pytest.mark.xfail
def test_wait_for_log_fail(container):
    with container(image='hello-world', wait_status=Status.EXITED) as cont:
        wait_for_log(cont, "Hullo from Docker!", timeout=5)
