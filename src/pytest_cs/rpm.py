import contextlib
import os
import pathlib
import shutil
import subprocess

import pytest

rpm_build_done = False


@pytest.fixture
def skip_unless_rpm() -> None:
    if not pathlib.Path("/etc/redhat-release").exists():
        pytest.skip("This test is only for RPM-based systems")


def rpmbuild(repodir: pathlib.Path, bouncer_under_test: str, version: str, package_number: str) -> None:
    directory_name = f"{bouncer_under_test}-{version}"

    # git clone repo from PROJECT_ROOT to rpm/SOURCES

    sources = repodir / "rpm/SOURCES"
    clone_dir = sources / directory_name
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(clone_dir)
    _ = subprocess.check_call(["make", "clean-rpm"], cwd=repodir)
    _ = subprocess.check_call(["git", "clone", repodir, clone_dir])
    _ = subprocess.check_call(["tar", "cfz", sources / f"v{version}.tar.gz", directory_name], cwd=sources)
    shutil.rmtree(clone_dir)
    env = os.environ.copy()
    env["VERSION"] = version
    env["PACKAGE_NUMBER"] = package_number
    _ = subprocess.check_call(
        ["rpmbuild", "--define", f"_topdir {repodir}/rpm", "-bb", f"rpm/SPECS/{bouncer_under_test}.spec"],
        cwd=repodir,
        env=env,
    )


@pytest.fixture(scope="session")
def rpm_package_name(deb_package_name: str) -> str:
    return deb_package_name


@pytest.fixture(scope="session")
def rpm_package_version() -> str:
    return "1.0"


@pytest.fixture(scope="session")
def rpm_package_number() -> str:
    return "1"


@pytest.fixture(scope="session")
def rpm_package_path(
    project_repo: pathlib.Path,
    rpm_package_version: str,
    rpm_package_number: str,
    rpm_package_name: str,
    bouncer_under_test: str,  # pyright:ignore[reportUnusedParameter]  # noqa: ARG001
) -> pathlib.Path:
    distversion, arch = subprocess.check_output(["uname", "-r"]).rstrip().decode().split(".")[-2:]
    filename = f"{rpm_package_name}-{rpm_package_version}-{rpm_package_number}.{distversion}.{arch}.rpm"
    return project_repo / "rpm/RPMS" / arch / filename


@pytest.fixture(scope="session")
def rpm_package(
    rpm_package_path: pathlib.Path,
    project_repo: pathlib.Path,
    rpm_package_version: str,
    rpm_package_number: str,
    bouncer_under_test: str,
) -> pathlib.Path:
    # Assume that the rpm package names are the same as the deb ones
    global rpm_build_done
    if not rpm_build_done:
        if rpm_package_path.exists():
            # no need to tell the user to remove the file, as rpmbuild will do it
            pass
        rpmbuild(
            repodir=project_repo,
            bouncer_under_test=bouncer_under_test,
            version=rpm_package_version,
            package_number=rpm_package_number,
        )
        rpm_build_done = True

    return rpm_package_path
