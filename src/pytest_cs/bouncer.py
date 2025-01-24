import contextlib
import os
import subprocess
import time

import psutil
import pytest
import yaml

from .waiters import WaiterGenerator

# How long to wait for a child process to spawn
CHILD_SPAWN_TIMEOUT = 2


class ProcessWaiterGenerator(WaiterGenerator):
    def __init__(self, proc):
        self.proc = proc
        super().__init__()

    def context(self):
        return self.proc


class BouncerProc:
    def __init__(self, popen, outpath):
        self.popen = popen
        self.proc = psutil.Process(popen.pid)
        self.outpath = outpath

    # wait for at least one child process to spawn
    # TODO: add a name to look for?
    def wait_for_child(self, timeout=CHILD_SPAWN_TIMEOUT):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            children = self.proc.children()
            if children:
                return children[0]
            time.sleep(0.1)
        raise TimeoutError("No child process found")

    def halt_children(self):
        for child in self.proc.children():
            child.kill()

    def children(self):
        return self.proc.children()

    def get_output(self):
        return pytest.LineMatcher(self.outpath.read_text().splitlines())

    def wait_for_lines_fnmatch(proc, s, timeout=5):
        for waiter in ProcessWaiterGenerator(proc):
            with waiter as p:
                p.get_output().fnmatch_lines(s)


# The bouncer to use is provided by the fixture bouncer_under_test.
# This won't work with different bouncers in the same test
# scenario, but it's unlikely that we'll need that
@pytest.fixture(scope='session')
def bouncer(bouncer_binary, tmp_path_factory):
    @contextlib.contextmanager
    def closure(config, config_local=None):
        # create joint stout/stderr file
        outdir = tmp_path_factory.mktemp('output')

        confpath = outdir / 'bouncer-config.yaml'
        with open(confpath, 'w') as f:
            f.write(yaml.dump(config))

        if config_local is not None:
            with open(confpath.with_suffix('.yaml.local'), 'w') as f:
                f.write(yaml.dump(config_local))

        outpath = outdir / 'output.txt'
        with open(outpath, 'w') as f:
            cb = subprocess.Popen(
                    [bouncer_binary, "-c", confpath.as_posix()],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    )
        try:
            yield BouncerProc(cb, outpath)
        finally:
            cb.kill()
            cb.wait()
    yield closure


@pytest.fixture(scope='session')
def bouncer_binary(project_repo, bouncer_under_test):
    binary_path = project_repo / bouncer_under_test
    if not binary_path.exists() or not os.access(binary_path, os.X_OK):
        raise RuntimeError(f"Bouncer binary not found at {binary_path}. Did you build it?")
    yield binary_path
