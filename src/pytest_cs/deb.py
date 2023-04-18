import pytest
import subprocess

from .misc import lookup_project_repo


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
            cwd=project_repo
    ).decode('utf-8').strip()


@pytest.fixture(scope='session')
def deb_package_arch():
    return subprocess.check_output(
            ['dpkg-architecture', '-qDEB_BUILD_ARCH']
    ).decode('utf-8').strip()


deb_build_done = False


def dpkg_buildpackage(repodir):
    subprocess.check_call(['make', 'clean-debian'], cwd=repodir)
    subprocess.check_call(['dpkg-buildpackage', '-us', '-uc', '-b'],
                          cwd=repodir)


@pytest.fixture(scope='session')
def deb_package_path(deb_package_name, deb_package_version, deb_package_arch, project_repo):
    global deb_build_done
    filename = f'{deb_package_name}_{deb_package_version}_{deb_package_arch}.deb'
    package_path = project_repo.parent / filename

    if not deb_build_done:
        if package_path.exists():
            # remove by hand, before running tests, because it's outside of the
            # project directory
            raise RuntimeError(f'Package {filename} already exists. Please remove it first.')
        dpkg_buildpackage(repodir=project_repo)
        deb_build_done = True

    yield package_path
