# -*- coding: utf-8 -*-

import contextlib
import json
import os
import subprocess
import textwrap

import docker
import docker.errors
import pytest
import trustme

import re
import time

keep_kind_cluster = True


@pytest.fixture(scope='session')
def certs_dir(tmp_path_factory):
    def create(lapi_hostname, agent_ou='agent-ou'):
        path = tmp_path_factory.mktemp('certs')

        ca = trustme.CA()
        ca.cert_pem.write_to_path(path / 'ca.crt')

        lapi_cert = ca.issue_server_cert('localhost', lapi_hostname)
        lapi_cert.cert_chain_pems[0].write_to_path(path / 'lapi.crt')
        lapi_cert.private_key_pem.write_to_path(path / 'lapi.key')

        agent_cert = ca.issue_cert('agent', common_name='agent', organization_unit_name=agent_ou)
        agent_cert.cert_chain_pems[0].write_to_path(path / 'agent.crt')
        agent_cert.private_key_pem.write_to_path(path / 'agent.key')

        return path
    return create


@pytest.fixture(scope='session')
def crowdsec_version():
    return os.environ['CROWDSEC_TEST_VERSION']


@pytest.fixture(scope='session')
def docker_network():
    return os.environ['CROWDSEC_TEST_NETWORK']


def crowdsec_flavors():
    try:
        return os.environ['CROWDSEC_TEST_FLAVORS'].split(',')
    except KeyError:
        return ['full']


@pytest.fixture(scope='session', params=crowdsec_flavors())
def flavor(request):
    return request.param


# Create a container. If the image was not found, pull it
# and try again
def pull_and_create_container(docker_client, *args, **kwargs):
    try:
        return docker_client.containers.create(*args, **kwargs)
    except docker.errors.ImageNotFound:
        repo, tag = kwargs['image'].split(':')
        docker_client.images.pull(repo, tag)
        return docker_client.containers.create(*args, **kwargs)


def get_image(version, flavor):
    if flavor == 'full':
        return f'crowdsecurity/crowdsec:{version}'
    return f'crowdsecurity/crowdsec:{version}-{flavor}'


@pytest.fixture(scope='session')
def docker_client():
    return docker.from_env()


# implement a Compose v2 project by calling the "docker compose" command
class ComposeProject:
    def __init__(self, compose_file):
        self.compose_file = compose_file
        self.cmd = ['docker', 'compose', '-f', compose_file.as_posix()]

    def up(self):
        cmd = self.cmd + ['up', '-d']
        subprocess.run(cmd, check=True)

    def down(self):
        cmd = self.cmd + ['down']
        subprocess.run(cmd, check=True)

    def ps(self):
        cmd = self.cmd + ['ps', '--format', 'json']
        p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
        j = json.loads(p.stdout)
        return j


@pytest.fixture(scope='session')
def compose():
    @contextlib.contextmanager
    def closure(compose_file):
        project = ComposeProject(compose_file)
        project.up()
        try:
            yield project
        finally:
            project.down()
    return closure


@pytest.fixture(scope='session')
def crowdsec(docker_client, crowdsec_version, docker_network):
    # return a context manager that will create a container, yield it, and
    # remove it when the context manager exits
    @contextlib.contextmanager
    def closure(*args, **kwargs):
        kw = kwargs.copy()

        wait_status = kw.pop('wait_status', Status.RUNNING)

        if 'image' in kw and 'flavor' in kw:
            raise ValueError('cannot specify both image and flavor')
        if 'image' not in kw:
            kw['image'] = get_image(crowdsec_version, kw.pop('flavor', 'full'))
        kw.setdefault('detach', True)
        kw.setdefault('auto_remove', False)
        kw.setdefault('environment', {})
        kw.setdefault('network', docker_network)

        # defaults for all crowdsec tests
        kw['environment'].setdefault('DISABLE_ONLINE_API', 'true')
        kw['environment'].setdefault('CROWDSEC_FEATURE_DISABLE_HTTP_RETRY_BACKOFF', 'true')

        # forced
        kw['environment']['CI_TESTING'] = 'true'

        # TODO:
        # kw.setdefault('ports', {'8080': None, '6060': None})

        cont = pull_and_create_container(docker_client, *args, **kw)
        cont.start()

        if wait_status:
            wait_for_status(cont, wait_status)

        try:
            yield cont
        finally:
            cont.stop(timeout=0)
            cont.wait()
            cont.reload()
            cont.remove(force=True)
    return closure


@pytest.fixture(scope='session')
def container(docker_client, docker_network):
    # return a context manager that will create a container, yield it, and
    # remove it when the context manager exits
    @contextlib.contextmanager
    def closure(*args, **kwargs):
        kw = kwargs.copy()

        wait_status = kw.pop('wait_status', Status.RUNNING)

        kw.setdefault('detach', True)
        kw.setdefault('auto_remove', False)
        kw.setdefault('environment', {})
        kw.setdefault('network', docker_network)

        # defaults for all crowdsec tests. We set them for all containers, just in case
        kw['environment'].setdefault('DISABLE_ONLINE_API', 'true')
        kw['environment'].setdefault('CROWDSEC_FEATURE_DISABLE_HTTP_RETRY_BACKOFF', 'true')

        # forced
        kw['environment']['CI_TESTING'] = 'true'

        cont = pull_and_create_container(docker_client, *args, **kw)
        cont.start()

        if wait_status:
            wait_for_status(cont, wait_status)

        try:
            yield cont
        finally:
            cont.stop(timeout=0)
            cont.wait()
            cont.reload()
            cont.remove(force=True)
    return closure


# this won't create a new cluster if one already exists
# and will optionally leave the cluster running after the tests
@pytest.fixture(scope='session')
def kind(tmp_path_factory):
    name = 'test'
    path = tmp_path_factory.mktemp('kind')
    kind_yml = path / 'kind.yml'
    kind_yml.write_text(textwrap.dedent('''\
        # three node (two workers) cluster config
        kind: Cluster
        apiVersion: kind.x-k8s.io/v1alpha4
        nodes:
        - role: control-plane
          kubeadmConfigPatches:
          - |
            kind: InitConfiguration
            nodeRegistration:
              kubeletExtraArgs:
                node-labels: "ingress-ready=true"
          extraPortMappings:
          - containerPort: 30000
            hostPort: 80
            protocol: TCP
          - containerPort: 30001
            hostPort: 443
            protocol: TCP
        - role: worker
    '''))

    clusters = subprocess.run(['kind', 'get', 'clusters'], stdout=subprocess.PIPE, check=True)
    out = clusters.stdout.decode('utf-8').splitlines()
    if 'No kind clusters found' in out or name not in out:
        subprocess.run(['kind', 'create', 'cluster', '--name', name, '--config', kind_yml.as_posix()], check=True)

    try:
        yield
    finally:
        if keep_kind_cluster:
            return
        subprocess.run(['kind', 'delete', 'cluster', '--name', name], check=True)


@pytest.fixture(scope='session')
def helm(kind):
    # return a context manager that will create a release, yield its name, and
    # remove it when the context manager exits
    @contextlib.contextmanager
    def closure(namespace, chart, values=None):
        release = f'test-{namespace}'
        cmd = ['helm', 'install', '--create-namespace', release, chart, '--namespace', namespace]
        if values:
            cmd += ['-f', values.as_posix()]
        subprocess.run(cmd, check=True)
        try:
            yield release
        finally:
            subprocess.run(['helm', 'uninstall', release, '--namespace', namespace], check=True)
    return closure


def wait_for_status(cont, status, timeout=30):
    start = time.monotonic()
    now = start
    while (now - start) < timeout:
        cont.reload()
        if cont.status == status:
            return
        time.sleep(.1)
        now = time.monotonic()
    raise TimeoutError(f'Container {cont.name} ({cont.status}) did not reach state {status} in {timeout} seconds')


# Return the last 'tail' lines of the container's logs (either a number or the string 'all')
# The default is a measure to avoid performance or memory issues.
def log_lines(cont, tail=10000):
    return cont.logs(tail=tail).decode('utf-8').splitlines()


# watch the container's logs for a line containing the given string
def wait_for_log(cont, s, timeout=30):
    start = time.monotonic()
    now = start
    while (now - start) < timeout:
        lines = log_lines(cont)
        for line in lines:
            if s in line:
                return
        time.sleep(.1)
        now = time.monotonic()
    raise TimeoutError(f'Container {cont.name} did not log "{s}" in {timeout} seconds')


# watch the container's logs for a line matching the given regex
def wait_for_log_re(cont, regex, timeout=30):
    if not hasattr(regex, 'search'):
        regex = re.compile(regex)
    start = time.monotonic()
    now = start
    while (now - start) < timeout:
        lines = log_lines(cont)
        for line in lines:
            if regex.search(line):
                return
        time.sleep(.1)
        now = time.monotonic()
    raise TimeoutError(f'Container {cont.name} did not log r"{regex.pattern}" in {timeout} seconds')


class Status:
    CREATED = 'created'
    RUNNING = 'running'
    PAUSED = 'paused'
    RESTARTING = 'restarting'
    EXITED = 'exited'
    DEAD = 'dead'
    REMOVING = 'removing'
