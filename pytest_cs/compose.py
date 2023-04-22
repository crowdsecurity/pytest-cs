# -*- coding: utf-8 -*-

import contextlib
import json
import subprocess

import pytest


# run a Compose v2 project by calling the "docker compose" command
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
    yield closure
