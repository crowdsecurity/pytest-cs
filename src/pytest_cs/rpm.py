import os
import shutil
import subprocess

import pytest

rpm_build_done = False


def rpmbuild(repodir, bouncer_under_test, version, package_number):
    directory_name = f'{bouncer_under_test}-{version}'

    # git clone repo from PROJECT_ROOT to rpm/SOURCES

    sources = repodir / 'rpm/SOURCES'
    clone_dir = sources / directory_name
    try:
        shutil.rmtree(clone_dir)
    except FileNotFoundError:
        pass
    subprocess.check_call(['make', 'clean-rpm'], cwd=repodir)
    subprocess.check_call(['git', 'clone', repodir, clone_dir])
    subprocess.check_call(['tar', 'cfz', sources / f'v{version}.tar.gz', directory_name], cwd=sources)
    shutil.rmtree(clone_dir)
    env = os.environ.copy()
    env['VERSION'] = version
    env['PACKAGE_NUMBER'] = package_number
    subprocess.check_call(['rpmbuild', '--define', f'_topdir {repodir}/rpm',
                           '-bb', f'rpm/SPECS/{bouncer_under_test}.spec'], cwd=repodir, env=env)


@pytest.fixture(scope='session')
def rpm_package_name(deb_package_name):
    yield deb_package_name


@pytest.fixture(scope='session')
def rpm_package_version():
    yield '1.0'


@pytest.fixture(scope='session')
def rpm_package_number():
    yield '1'


@pytest.fixture(scope='session')
def rpm_package_path(project_repo, rpm_package_version, rpm_package_number, rpm_package_name, bouncer_under_test):
    distversion, arch = subprocess.check_output(['uname', '-r']).rstrip().decode().split('.')[-2:]
    filename = f'{rpm_package_name}-{rpm_package_version}-{rpm_package_number}.{distversion}.{arch}.rpm'
    yield project_repo / 'rpm/RPMS' / arch / filename


@pytest.fixture(scope='session')
def rpm_package(rpm_package_path, project_repo, rpm_package_version, bouncer_under_test):
    # Assume that the rpm package names are the same as the deb ones
    global rpm_build_done
    if not rpm_build_done:
        if rpm_package_path.exists():
            # no need to tell the user to remove the file, as rpmbuild will do it
            pass
        rpmbuild(repodir=project_repo,
                 bouncer_under_test=bouncer_under_test,
                 version=rpm_package_version,
                 package_number=rpm_package_number)
        rpm_build_done = True

    yield rpm_package_path
