import os
import uuid
import tempfile
import shutil
import json
from typing import List, Dict
import logging

import pytest

from piper_lxd.models.runner import Runner
from piper_lxd.models.job import ResponseJobStatus, RequestJobStatus

logging.basicConfig()
logging.getLogger('piper_lxd.models.runner').setLevel(logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def correct_privkey_permissions(request):
    os.chmod('tests/keys/privkey_repo', 0o600)
    os.chmod('tests/keys/privkey_submodule', 0o600)


@pytest.fixture()
def runner(monkeypatch):
    token = uuid.uuid4().hex
    tempdir = os.path.join(tempfile.gettempdir(), token)

    runner = Runner(
        runner_repository_dir=os.path.join(tempdir, 'repository'),
        runner_token=token,
        driver_endpoint='http://localhost',
        lxd_profiles=['piper-ci'],
        runner_interval=2,
        lxd_cert='~/.config/lxc-client/client.crt',
        lxd_key='~/.config/lxc-client/client.key',
        lxd_endpoint='https://127.0.0.1:8443'
    )

    def get_fetch_function(jobs: List):
        def fn(self):
            try:
                job = jobs.pop()
            except IndexError:
                raise StopIteration
            with open('tests/jobs/{}.json'.format(job)) as fd:
                return json.load(fd)

        return fn

    def get_report_function(outputs: Dict[str, str], statuses: Dict[str, List[RequestJobStatus]], response_status):
        def fn(self, secret: str, status: RequestJobStatus, data=None):
            if secret not in statuses:
                statuses[secret] = list()
            if secret not in outputs:
                outputs[secret] = ''
            statuses[secret].append(status)
            if data is not None:
                outputs[secret] += data

            return response_status

        return fn

    def run_test(self, jobs, response_status=ResponseJobStatus.OK):
        output = dict()
        statuses = dict()
        monkeypatch.setattr('piper_lxd.models.runner.Runner._fetch_job', get_fetch_function(jobs))
        monkeypatch.setattr('piper_lxd.models.runner.Runner._report_status',
                            get_report_function(output, statuses, response_status))

        try:
            self.run()
        except StopIteration:
            pass

        return output, statuses

    Runner.run_test = run_test

    yield runner

    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)


@pytest.fixture()
def empty_clone(monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', lambda a, b, c, d, e=None: None)

