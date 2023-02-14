#!/usr/bin/env python

from pytest_cs import log_waiters, port_waiters, wait_for_http, wait_for_log

import pytest
import time


def test_crowdsec_log(crowdsec):
    with crowdsec() as cont:
        for waiter in log_waiters(cont, timeout=10):
            with waiter as matcher:
                matcher.fnmatch_lines([
                    "*Loading prometheus collectors*",
                    "*Starting processing data*",
                ])
        res = cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert 'true' == res.output.decode().strip()


def test_crowdsec_log_helper(crowdsec):
    with crowdsec() as cont:
        wait_for_log(cont, [
            "*Loading prometheus collectors*",
            "*Starting processing data*",
        ])
        res = cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert 'true' == res.output.decode().strip()


def test_port_waiters(crowdsec):
    with crowdsec() as cont:
        for waiter in port_waiters(cont, timeout=10):
            with waiter as probe:
                assert probe.get_bound_port(8080) is not None
                assert probe.http_status_code(8080, '/health') == 200


def test_wait_for_http(crowdsec):
    with crowdsec() as cont:
        status = wait_for_http(cont, 8080, '/health')
        assert status == 200
