import os
import pathlib
import secrets
import string
import subprocess
import typing

import pytest
import trustme
from _pytest.nodes import Node
from _pytest.reports import BaseReport

keep_kind_cluster = True


def systemd_debug(service: str | None = None) -> None:
    if service is None:
        print("No service name provided, can't show journal output")
        return

    p = subprocess.Popen(
        ["systemctl", "status", service], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8"
    )
    stdout, _stderr = p.communicate()
    print(f"--- systemctl status (return code: {p.returncode}) ---")
    print(stdout)

    p = subprocess.Popen(
        ["journalctl", "-xeu", service],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    stdout, _stderr = p.communicate()
    print(f"--- journalctl -xeu (return code: {p.returncode}) ---")
    print(stdout)


def pytest_exception_interact(node: Node, _call: pytest.CallInfo[typing.Any], report: BaseReport) -> None:
    # when a test with the marker "systemd_debug(service)" fails,
    # we dump the status and journal for the systemd unit, but only when
    # running in CI. Interactive runs can use --pdb to debug.
    if report.failed and os.environ.get("CI") == "true":
        for m in node.iter_markers():
            if m.name == "systemd_debug":
                systemd_debug(*m.args, **m.kwargs)


@pytest.fixture(scope="session")
def certs_dir(tmp_path_factory: pytest.TempPathFactory) -> typing.Callable[[str, str, str], pathlib.Path]:
    def closure(lapi_hostname: str, agent_ou: str = "agent-ou", bouncer_ou: str = "bouncer-ou") -> pathlib.Path:
        path = tmp_path_factory.mktemp("certs")

        ca = trustme.CA()
        ca.cert_pem.write_to_path(path / "ca.crt")

        lapi_cert = ca.issue_server_cert("localhost", lapi_hostname)
        lapi_cert.cert_chain_pems[0].write_to_path(path / "lapi.crt")
        lapi_cert.private_key_pem.write_to_path(path / "lapi.key")

        agent_cert = ca.issue_cert("agent", organization_unit_name=agent_ou)
        agent_cert.cert_chain_pems[0].write_to_path(path / "agent.crt")
        agent_cert.private_key_pem.write_to_path(path / "agent.key")

        bouncer_cert = ca.issue_cert("bouncer", organization_unit_name=bouncer_ou)
        bouncer_cert.cert_chain_pems[0].write_to_path(path / "bouncer.crt")
        bouncer_cert.private_key_pem.write_to_path(path / "bouncer.key")

        return path

    return closure


@pytest.fixture(scope="session")
def api_key_factory() -> typing.Callable[[str], str]:
    def closure(alphabet: str = string.ascii_letters + string.digits) -> str:
        return "".join(secrets.choice(alphabet) for _ in range(32))

    return closure
