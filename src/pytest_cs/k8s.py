import contextlib
import subprocess
import textwrap

import pytest

keep_kind_cluster = True


# this won't create a new cluster if one already exists
# and will optionally leave the cluster running after the tests
@pytest.fixture(scope="session")
def kind(tmp_path_factory: pytest.TempPathFactory):
    name = "test"
    path = tmp_path_factory.mktemp("kind")
    kind_yml = path / "kind.yml"
    kind_yml.write_text(
        textwrap.dedent("""\
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
    """)
    )

    clusters = subprocess.run(["kind", "get", "clusters"], stdout=subprocess.PIPE, encoding="utf-8", check=True)
    out = clusters.stdout.splitlines()
    if "No kind clusters found" in out or name not in out:
        subprocess.run(["kind", "create", "cluster", "--name", name, "--config", kind_yml.as_posix()], check=True)

    try:
        yield
    finally:
        if not keep_kind_cluster:
            subprocess.run(["kind", "delete", "cluster", "--name", name], check=True)


@pytest.fixture(scope="session")
def helm(kind):
    # return a context manager that will create a release, yield its name, and
    # remove it when the context manager exits
    @contextlib.contextmanager
    def closure(namespace, chart, values=None):
        release = f"test-{namespace}"
        cmd = ["helm", "install", "--create-namespace", release, chart, "--namespace", namespace]
        if values:
            cmd += ["-f", values.as_posix()]
        subprocess.run(cmd, check=True)
        try:
            yield release
        finally:
            subprocess.run(["helm", "uninstall", release, "--namespace", namespace], check=True)

    yield closure
