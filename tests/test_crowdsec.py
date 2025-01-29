#!/usr/bin/env python


def test_crowdsec_log(crowdsec):
    with crowdsec() as cs:
        for waiter in cs.log_waiters():
            with waiter as matcher:
                matcher.fnmatch_lines(
                    [
                        "*Loading prometheus collectors*",
                        "*Starting processing data*",
                    ]
                )
        res = cs.cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert "true" == res.output.decode().strip()


def test_crowdsec_log_helper(crowdsec):
    with crowdsec() as cs:
        cs.wait_for_log(
            [
                "*Loading prometheus collectors*",
                "*Starting processing data*",
            ]
        )
        res = cs.cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert "true" == res.output.decode().strip()


def test_port_waiters(crowdsec):
    with crowdsec() as cs:
        for waiter in cs.port_waiters():
            with waiter as probe:
                assert probe.get_bound_port(8080) is not None
                assert probe.http_status_code(8080, "/health") == 200


def test_wait_for_http(crowdsec):
    with crowdsec() as cs:
        status = cs.wait_for_http(8080, "/health")
        assert status == 200
