import json
import logging
import os
import uuid
from collections import defaultdict

import pytest

from piper_lxd.models.config import Config
from piper_lxd.models.job import ResponseJobStatus, RequestJobStatus, Job

logging.basicConfig()
logging.getLogger('piper-lxd').setLevel(logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def correct_privkey_permissions(request):
    os.chmod('tests/keys/privkey_repo', 0o600)
    os.chmod('tests/keys/privkey_submodule', 0o600)


class FakeConnection:

    def __init__(self):
        self.jobs = list()
        self.statuses = defaultdict(list)
        self.logs = defaultdict(str)

    def fetch_job(self, token: str) -> Job:
        if len(self.jobs) == 0:
            return None

        return self.jobs.pop()

    def push_job(self, job: str):
        with open('tests/jobs/{}.json'.format(job)) as fd:
            self.jobs.append(Job(json.load(fd)))

    def report(self, secret: str, status: RequestJobStatus, log: str = None) -> ResponseJobStatus:
        self.statuses[secret].append(status)
        self.logs[secret] += log

        return ResponseJobStatus.OK


@pytest.fixture()
def connection():
    connection = FakeConnection()

    return connection


@pytest.fixture()
def config():
    config = {
        'lxd': {
            'verify': False,
            'profiles': ['piper-ci'],
            'endpoint': 'https://127.0.0.1:8443',
            'cert': '~/.config/lxc-client/client.crt',
            'key': '~/.config/lxc-client/client.key',
        },
        'runner': {
            'token': uuid.uuid4().hex,
            'endpoint': 'http://localhost',
        }
    }
    config = Config(config)

    return config


@pytest.fixture()
def empty_clone(monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', lambda a, b, c, d, e=None: None)

