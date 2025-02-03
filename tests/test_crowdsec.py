from http import HTTPStatus


def test_crowdsec_log(crowdsec) -> None:
    with crowdsec() as cs:
        for waiter in cs.log_waiters():
            with waiter as matcher:
                matcher.fnmatch_lines(
                    [
                        "*Loading prometheus collectors*",
                        "*Starting processing data*",
                    ],
                )
        res = cs.cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert res.output.decode().strip() == "true"


def test_crowdsec_log_helper(crowdsec) -> None:
    with crowdsec() as cs:
        cs.wait_for_log(
            [
                "*Loading prometheus collectors*",
                "*Starting processing data*",
            ],
        )
        res = cs.cont.exec_run('sh -c "echo $CI_TESTING"')
        assert res.exit_code == 0
        assert res.output.decode().strip() == "true"


def test_port_waiters(crowdsec) -> None:
    with crowdsec() as cs:
        for waiter in cs.port_waiters():
            with waiter as probe:
                assert probe.get_bound_port(8080) is not None
                assert probe.http_status_code(8080, "/health") == HTTPStatus.OK


def test_wait_for_http(crowdsec) -> None:
    with crowdsec() as cs:
        assert cs.wait_for_http(8080, "/health") == HTTPStatus.OK
