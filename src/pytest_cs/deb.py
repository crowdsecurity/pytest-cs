import pathlib
import subprocess
from collections.abc import Iterator

import pytest

from .misc import lookup_project_repo

deb_build_done = False


@pytest.fixture
def skip_unless_deb() -> None:
    if not pathlib.Path("/etc/debian_version").exists():
        pytest.skip("This test is only for Debian-based systems.")


def enum_package_names() -> Iterator[str]:
    repo = lookup_project_repo()
    try:
        with (repo / "debian/control").open() as f:
            for line in f:
                if line.startswith("Package:"):
                    yield line.split()[1]
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session", params=enum_package_names())
def deb_package_name(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="session")
def deb_package_version(project_repo: pathlib.Path) -> str:
    return subprocess.check_output(["dpkg-parsechangelog", "-S", "version"], encoding="utf-8", cwd=project_repo).strip()


@pytest.fixture(scope="session")
def deb_package_arch() -> str:
    return subprocess.check_output(["dpkg-architecture", "-qDEB_BUILD_ARCH"], encoding="utf-8").strip()


def dpkg_buildpackage(repodir: pathlib.Path) -> None:
    _ = subprocess.check_call(["make", "clean-debian"], cwd=repodir)
    _ = subprocess.check_call(["dpkg-buildpackage", "-us", "-uc", "-b"], cwd=repodir)


@pytest.fixture(scope="session")
def deb_package_path(
    deb_package_name: str,
    deb_package_version: str,
    deb_package_arch: str,
    project_repo: pathlib.Path,
) -> pathlib.Path:
    return project_repo.parent / f"{deb_package_name}_{deb_package_version}_{deb_package_arch}.deb"


@pytest.fixture(scope="session")
def deb_package(deb_package_path: pathlib.Path, project_repo: pathlib.Path) -> pathlib.Path:
    global deb_build_done
    if not deb_build_done:
        deb_package_path.unlink(missing_ok=True)
        dpkg_buildpackage(repodir=project_repo)
        deb_build_done = True
    return deb_package_path
