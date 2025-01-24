import os
import pytest
import subprocess

from .misc import lookup_project_repo

deb_build_done = False


@pytest.fixture
def skip_unless_deb():
    if not os.path.exists('/etc/debian_version'):
        pytest.skip('This test is only for Debian-based systems.')


def enum_package_names():
    repo = lookup_project_repo()
    try:
        with open(repo / 'debian/control') as f:
            for line in f:
                if line.startswith('Package:'):
                    yield line.split()[1]
    except FileNotFoundError:
        pass


@pytest.fixture(scope='session', params=enum_package_names())
def deb_package_name(request):
    return request.param


@pytest.fixture(scope='session')
def deb_package_version(project_repo):
    return subprocess.check_output(
        ['dpkg-parsechangelog', '-S', 'version'],
        encoding='utf-8',
        cwd=project_repo
    ).strip()


@pytest.fixture(scope='session')
def deb_package_arch():
    return subprocess.check_output(
        ['dpkg-architecture', '-qDEB_BUILD_ARCH'],
        encoding='utf-8'
    ).strip()


def dpkg_buildpackage(repodir):
    subprocess.check_call(['make', 'clean-debian'], cwd=repodir)
    subprocess.check_call(['dpkg-buildpackage', '-us', '-uc', '-b'], cwd=repodir)


@pytest.fixture(scope='session')
def deb_package_path(deb_package_name, deb_package_version, deb_package_arch, project_repo):
    yield project_repo.parent / f'{deb_package_name}_{deb_package_version}_{deb_package_arch}.deb'


@pytest.fixture(scope='session')
def deb_package(deb_package_path, project_repo):
    global deb_build_done
    if not deb_build_done:
        deb_package_path.unlink(missing_ok=True)
        dpkg_buildpackage(repodir=project_repo)
        deb_build_done = True
    yield deb_package_path
