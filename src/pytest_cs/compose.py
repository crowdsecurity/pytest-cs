import contextlib
import json
import pathlib
import subprocess
from typing import Final

import pytest


# run a Compose v2 project by calling the "docker compose" command
class ComposeProject:
    def __init__(self, compose_file: pathlib.Path) -> None:
        self.compose_file: Final = compose_file
        self.cmd: Final = ["docker", "compose", "-f", compose_file.as_posix()]

    def up(self) -> None:
        cmd = [*self.cmd, "up", "-d"]
        _ = subprocess.run(cmd, check=True)

    def down(self) -> None:
        cmd = [*self.cmd, "down"]
        _ = subprocess.run(cmd, check=True)

    def ps(self):
        cmd = [*self.cmd, "ps", "--format", "json"]
        p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
        return json.loads(p.stdout)


@pytest.fixture(scope="session")
def compose():
    @contextlib.contextmanager
    def closure(compose_file: pathlib.Path):
        project = ComposeProject(compose_file)
        project.up()
        try:
            yield project
        finally:
            project.down()

    return closure
