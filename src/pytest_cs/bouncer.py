import contextlib
import os
import pathlib
import subprocess
import time
from typing import Final, override

import psutil
import pytest
import yaml

from .waiters import WaiterGenerator

# How long to wait for a child process to spawn
CHILD_SPAWN_TIMEOUT = 2


class ProcessWaiterGenerator(WaiterGenerator["BouncerProc"]):
    def __init__(self, proc: "BouncerProc") -> None:
        self.proc: Final = proc
        super().__init__()

    @override
    def context(self) -> "BouncerProc":
        return self.proc


class BouncerProc:
    def __init__(self, popen: subprocess.Popen[str], outpath: pathlib.Path) -> None:
        self.popen: Final = popen
        self.proc: Final = psutil.Process(popen.pid)
        self.outpath: Final = outpath

    # wait for at least one child process to spawn
    # TODO: add a name to look for?
    def wait_for_child(self, timeout: int = CHILD_SPAWN_TIMEOUT) -> psutil.Process:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            children = self.proc.children()
            if children:
                return children[0]
            time.sleep(0.1)
        raise TimeoutError("No child process found")

    def halt_children(self) -> None:
        for child in self.proc.children():
            child.kill()

    def children(self) -> list[psutil.Process]:
        return self.proc.children()

    def get_output(self) -> pytest.LineMatcher:
        return pytest.LineMatcher(self.outpath.read_text().splitlines())

    # TODO: add timeout?
    def wait_for_lines_fnmatch(self, s: list[str]):
        for waiter in ProcessWaiterGenerator(self):
            with waiter as p:
                p.get_output().fnmatch_lines(s)


# The bouncer to use is provided by the fixture bouncer_under_test.
# This won't work with different bouncers in the same test
# scenario, but it's unlikely that we'll need that
@pytest.fixture(scope="session")
def bouncer(bouncer_binary: str, tmp_path_factory: pytest.TempPathFactory):
    @contextlib.contextmanager
    def closure(config, config_local=None):
        # create joint stout/stderr file
        outdir = tmp_path_factory.mktemp("output")

        confpath = outdir / "bouncer-config.yaml"
        with pathlib.Path(confpath).open("w") as f:
            _ = f.write(yaml.dump(config))

        if config_local is not None:
            with confpath.with_suffix(".yaml.local").open("w") as f:
                _ = f.write(yaml.dump(config_local))

        outpath = outdir / "output.txt"
        with outpath.open("w") as f:
            cb = subprocess.Popen[str](
                [bouncer_binary, "-c", confpath.as_posix()],
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
        try:
            yield BouncerProc(cb, outpath)
        finally:
            cb.kill()
            _ = cb.wait()

    return closure


@pytest.fixture(scope="session")
def bouncer_binary(project_repo: pathlib.Path, bouncer_under_test: str) -> pathlib.Path:
    binary_path = project_repo / bouncer_under_test
    if not binary_path.exists() or not os.access(binary_path, os.X_OK):
        raise RuntimeError(f"Bouncer binary not found at {binary_path}. Did you build it?")
    return binary_path
