import contextlib
import http
import os
import time
from collections.abc import Callable, Iterator
from typing import Final, TypeVar, override

import docker
import docker.errors
import docker.models.containers
import pytest
import requests

from .helpers import default_timeout
from .waiters import WaiterGenerator


@pytest.fixture(scope="session")
def crowdsec_version() -> str:
    return os.environ["CROWDSEC_TEST_VERSION"]


@pytest.fixture(scope="session")
def docker_network() -> str:
    return os.environ["CROWDSEC_TEST_NETWORK"]


def crowdsec_flavors() -> list[str]:
    try:
        return os.environ["CROWDSEC_TEST_FLAVORS"].split(",")
    except KeyError:
        return ["full"]


@pytest.fixture(scope="session", params=crowdsec_flavors())
def flavor(request: pytest.FixtureRequest) -> str:
    return request.param


class Container:
    def __init__(self, cont: docker.models.containers.Container) -> None:
        self.cont: Final = cont

    def log_waiters(self, *args, **kw):
        return log_waiters(self.cont, *args, **kw)

    def port_waiters(self, *args, **kw):
        return port_waiters(self.cont, *args, **kw)

    def wait_for_log(self, s: str | list[str], timeout: float | None = None) -> None:
        if timeout is None:
            timeout = default_timeout()
        if isinstance(s, str):
            s = [s]
        for waiter in log_waiters(self.cont, timeout):
            with waiter as matcher:
                matcher.fnmatch_lines(s)

    def wait_for_http(
        self, port: int, path: str, want_status: http.HTTPStatus | None = None, timeout: float | None = None
    ) -> http.HTTPStatus | None:
        if timeout is None:
            timeout = default_timeout()
        for waiter in port_waiters(self.cont, timeout):
            with waiter as probe:
                status = probe.http_status_code(port, path)
                # the iteration is invalidated if it raises an exception (i.e. the check will be retried)
                assert status is not None
                # wait for a specific status code - this could be behind a proxy/load balancer
                # status_code=None if we don't care about it
                if want_status is not None:
                    assert status == want_status
                return status
        return None

    # Return the last 'tail' lines of the container's logs (either a number or the string 'all')
    # The default is a measure to avoid performance or memory issues.
    def log_lines(self, tail: int = 10000) -> list[str]:
        return self.cont.logs(tail=tail).decode("utf-8").splitlines()

    @property
    def probe(self) -> "Probe":
        return Probe(self.cont.ports)


class CrowdsecContainer(Container):
    pass


# Create a container. If the image was not found, pull it
# and try again
def pull_and_create_container(
    docker_client: docker.DockerClient,
    *args,
    **kwargs,
) -> docker.models.containers.Container:
    try:
        return docker_client.containers.create(*args, **kwargs)
    except docker.errors.ImageNotFound:
        try:
            repo, tag = kwargs["image"].split(":")
        except ValueError:
            repo = kwargs["image"]
            tag = "latest"
        _ = docker_client.images.pull(repo, tag)
        return docker_client.containers.create(*args, **kwargs)


def get_image(version: str, flavor: str) -> str:
    if flavor == "full":
        return f"crowdsecurity/crowdsec:{version}"
    return f"crowdsecurity/crowdsec:{version}-{flavor}"


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    return docker.from_env()


@pytest.fixture(scope="session")
def crowdsec(
    docker_client: docker.DockerClient,
    crowdsec_version: str,
    docker_network: str,
) -> Callable[..., contextlib.AbstractContextManager[CrowdsecContainer]]:
    # return a context manager that will create a container, yield it, and
    # stop it when the context manager exits
    @contextlib.contextmanager
    def closure(*args, **kwargs) -> Iterator[CrowdsecContainer]:
        kw = kwargs.copy()

        wait_status = kw.pop("wait_status", Status.RUNNING)

        if "image" in kw and "flavor" in kw:
            msg = "cannot specify both image and flavor"
            raise ValueError(msg)
        if "image" not in kw:
            kw["image"] = get_image(crowdsec_version, kw.pop("flavor", "full"))
        kw.setdefault("detach", True)
        kw.setdefault("auto_remove", False)
        kw.setdefault("environment", {})
        kw.setdefault("network", docker_network)

        # defaults for all crowdsec tests
        kw["environment"].setdefault("DISABLE_ONLINE_API", "true")
        kw["environment"].setdefault("NO_HUB_UPGRADE", "true")
        kw["environment"].setdefault("CROWDSEC_FEATURE_DISABLE_HTTP_RETRY_BACKOFF", "true")

        # forced
        kw["environment"]["CI_TESTING"] = "true"

        # TODO:
        kw.setdefault("ports", {"8080": None, "6060": None})

        cont = pull_and_create_container(docker_client, *args, **kw)
        cont.start()

        if wait_status:
            wait_for_status(cont, wait_status)

        try:
            yield CrowdsecContainer(cont)
        finally:
            cont.stop(timeout=0)
            _ = cont.wait()
            cont.reload()
            # we don't remove the container, so that we can inspect it if the test fails
            # cont.remove(force=True)

    return closure


@pytest.fixture(scope="session")
def container(
    docker_client: docker.DockerClient,
    docker_network: str,
) -> Callable[..., contextlib.AbstractContextManager[Container]]:
    # return a context manager that will create a container, yield it, and
    # stop it when the context manager exits
    @contextlib.contextmanager
    def closure(*args, **kwargs) -> Iterator[Container]:
        kw = kwargs.copy()

        wait_status = kw.pop("wait_status", Status.RUNNING)

        kw.setdefault("detach", True)
        kw.setdefault("auto_remove", False)
        kw.setdefault("environment", {})
        kw.setdefault("network", docker_network)

        # defaults for all crowdsec tests. We set them for all containers, just in case
        kw["environment"].setdefault("DISABLE_ONLINE_API", "true")
        kw["environment"].setdefault("NO_HUB_UPGRADE", "true")
        kw["environment"].setdefault("CROWDSEC_FEATURE_DISABLE_HTTP_RETRY_BACKOFF", "true")

        # forced
        kw["environment"]["CI_TESTING"] = "true"

        cont = pull_and_create_container(docker_client, *args, **kw)
        cont.start()

        if wait_status:
            wait_for_status(cont, wait_status)

        try:
            yield Container(cont)
        finally:
            cont.stop(timeout=0)
            _ = cont.wait()
            cont.reload()
            # we don't remove the container, so that we can inspect it if the test fails
            # cont.remove(force=True)

    return closure


T = TypeVar("T")


class ContainerWaiterGenerator(WaiterGenerator[T]):
    def __init__(self, cont: docker.models.containers.Container, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = default_timeout()
        super().__init__(timeout)
        self.cont: Final = cont

    @override
    def refresh(self) -> None:
        self.cont.reload()
        super().refresh()


class Probe:
    def __init__(self, ports: dict[str, list[dict[str, str]]]) -> None:
        self.ports: Final = ports

    def get_bound_port(self, port: int):
        full_port = f"{port}/tcp"
        if full_port not in self.ports:
            return None
        return self.ports[full_port][0]["HostPort"]

    def http_status_code(self, port: int, path: str) -> http.HTTPStatus | None:
        bound_port = self.get_bound_port(port)
        if bound_port is None:
            return None

        url = f"http://localhost:{bound_port}{path}"

        try:
            r = requests.get(url, timeout=30)
        except requests.exceptions.ConnectionError:
            return None
        return http.HTTPStatus(r.status_code)


class port_waiters(ContainerWaiterGenerator[Probe]):
    @override
    def context(self) -> Probe:
        return Probe(self.cont.ports)


def wait_for_status(cont: docker.models.containers.Container, status: str, timeout: float | None = None) -> None:
    if timeout is None:
        timeout = default_timeout()
    start = time.monotonic()
    now = start
    while (now - start) < timeout:
        cont.reload()
        if cont.status == status:
            return
        time.sleep(0.1)
        now = time.monotonic()
    msg = f"Container {cont.name} ({cont.status}) did not reach state {status} in {timeout} seconds"
    raise TimeoutError(msg)


class log_waiters(ContainerWaiterGenerator[pytest.LineMatcher]):
    @override
    def context(self) -> pytest.LineMatcher:
        lines = self.cont.logs(tail=10000).decode("utf-8").splitlines()
        return pytest.LineMatcher(lines)


# TODO: enum
class Status:
    CREATED: Final = "created"
    RUNNING: Final = "running"
    PAUSED: Final = "paused"
    RESTARTING: Final = "restarting"
    EXITED: Final = "exited"
    DEAD: Final = "dead"
    REMOVING: Final = "removing"
