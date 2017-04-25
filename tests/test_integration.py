import pytest
import subprocess
import time
import os
import shlex
import uuid
import tempfile
import signal
import re
from typing import List

from piper_lxd.runner import JobStatus


class Context:

    def __init__(self, jobs: List):
        self._key = 'PIPER-{}-{}'.format(int(time.time()), uuid.uuid4().hex)
        self._tempdir = os.path.join(tempfile.tempdir, self._key)
        self._job_dir = os.path.join(self._tempdir, 'job')
        os.makedirs(self._tempdir, exist_ok=True)
        os.makedirs(os.path.join(self._tempdir, 'job'))

        self._jobs = jobs
        self._status = dict()
        for job in self._jobs:
            self._status[job] = None

        self._server = self._start_dummy_server()
        self._worker = self._start_piper_lxd()
        assert self._server.returncode is None
        assert self._worker.returncode is None

    def __repr__(self):
        return self._key

    def wait(self, timeout=120):
        jobs = set(self._jobs)
        completed = set()
        failed = set()
        for i in range(timeout * 10):
            files = os.listdir(self._job_dir)
            status_files = [x for x in files if x.endswith('-status')]

            for file in status_files:
                path = os.path.join(tempfile.gettempdir(), self._key, 'job', file)
                job = ''.join(file.split('-')[:-1])

                if job in completed or job in failed:
                    continue

                with open(path) as fd:
                    lines = fd.readlines()
                    if len(lines):
                        status = lines[-1].strip()
                    if status == JobStatus.COMPLETED.value:
                        self._status[job] = JobStatus.COMPLETED
                        completed.add(job)
                    if status.startswith('ERROR'):
                        self._status[job] = JobStatus(status)
                        failed.add(job)

            if (completed | failed) == jobs:
                return completed, failed
            time.sleep(.1)

        return completed, failed

    def job_status(self, job) -> JobStatus:
        return self._status[job]

    def log_file(self, job):
        return os.path.join(self._job_dir, job)

    def _status_file(self, job):
        return os.path.join(self._job_dir, job + '-status')

    def _start_dummy_server(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        tempdir = os.path.join(tempfile.tempdir, self._key)
        queue_file = os.path.join(tempdir, 'queue')

        with open(queue_file, 'w') as fp:
            fp.write(os.linesep.join(self._jobs))

        command = shlex.split('''
            uwsgi 
            --master 
            --http :4444 
            --http-websockets 
            --wsgi dummy_driver:app 
            --processes 2 
            --env PIPER_TEST_KEY=''' + self._key
        )
        stdout = open(os.path.join(os.path.join(tempdir, 'dummy_server.out')), 'w')
        stderr = open(os.path.join(os.path.join(tempdir, 'dummy_server.err')), 'w')

        server = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd)

        return server

    def _start_piper_lxd(self):
        tempdir = os.path.join(tempfile.tempdir, self._key)
        os.makedirs(tempdir, exist_ok=True)
        repository_dir = os.path.join(tempdir, 'repository')
        os.makedirs(repository_dir)
        stdout = open(os.path.join(os.path.join(tempdir, 'piper_lxd.out')), 'w')
        stderr = open(os.path.join(os.path.join(tempdir, 'piper_lxd.err')), 'w')

        command = shlex.split('''
                    piper_lxd 
                    --driver-url 127.0.0.1:4444
                    --runner-token TOKEN 
                    --lxd-profiles piper-ci
                    --lxd-endpoint https://127.0.0.1:8443
                    --lxd-key ~/.config/lxc-client/client.key
                    --lxd-cert ~/.config/lxc-client/client.crt
                    --runner-repository-dir
                ''' + ' ' + repository_dir)
        worker = subprocess.Popen(command, stdout=stdout, stderr=stderr)

        return worker

    def server(self):
        return self._server

    def worker(self):
        return self._worker

    def jobs(self):
        return self._jobs


@pytest.fixture
def context(request):
    jobs = request.param
    test_context = Context(jobs)
    yield test_context

    # stop server and client
    # https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html
    os.kill(test_context.server().pid, signal.SIGINT)
    test_context.server().wait()

    test_context.worker().terminate()
    test_context.worker().wait()


@pytest.mark.parametrize(
    'context',
    [['clone']],
    indirect=True
)
def test_clone(context: Context):
    completed, failed = context.wait(120)
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        while True:
            line = fp.readline()
            assert line != ''
            if re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', line):
                break
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert fp.readline().strip() == 'e7a4739755a81a06242bc3249e36b133b3783f9b'
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:2:start:\d+::$', fp.readline())
        assert sorted(fp.readline().strip().split(' ')) == sorted(['README.md', 'submodule'])
        assert re.match(r'^::piper_lxd-ci:command:2:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:3:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:3:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:4:start:\d+::$', fp.readline())
        assert fp.readline().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert re.match(r'^::piper_lxd-ci:command:4:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:5:start:\d+::$', fp.readline())
        assert sorted(fp.readline().strip().split(' ')) == sorted(['README.md'])
        assert re.match(r'^::piper_lxd-ci:command:5:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['sleep']],
    indirect=True
)
def test_sleep(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert re.match(r'^START$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:2:start:\d+::$', fp.readline())
        assert re.match(r'^END', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:2:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['cd']],
    indirect=True
)
def test_cd(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        pwd = fp.readline()
        assert pwd
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:2:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:2:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:3:start:\d+::$', fp.readline())
        pwd2 = fp.readline()
        assert pwd2
        assert pwd2 != pwd
        assert re.match(r'^::piper_lxd-ci:command:3:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['env']],
    indirect=True
)
def test_env(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert fp.readline().strip() == 'I want to die'
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert fp.readline().strip() == 'Please'
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['fail']],
    indirect=True
)
def test_fail(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:1::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['after_failure']],
    indirect=True
)
def test_after_failure(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:1::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:after_failure:0:start:\d+::$', fp.readline())
        assert fp.readline().strip() == '1'
        assert re.match(r'^::piper_lxd-ci:after_failure:0:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['multiple_1', 'multiple_2', 'multiple_3']],
    indirect=True
)
def test_multiple(context: Context):
    completed, failed = context.wait()
    assert completed == set(context.jobs())

    with open(context.log_file(context.jobs()[0])) as fd:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fd.readline())
        assert fd.readline().strip() == '1'
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fd.readline())
        assert fd.readline() == ''

    with open(context.log_file(context.jobs()[1])) as fd:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fd.readline())
        assert fd.readline().strip() == '2'
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fd.readline())
        assert fd.readline() == ''

    with open(context.log_file(context.jobs()[2])) as fd:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fd.readline())
        assert fd.readline().strip() == '3'
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fd.readline())
        assert fd.readline() == ''


@pytest.mark.parametrize(
    'context',
    [['no_commands']],
    indirect=True
)
def test_no_commands(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_NO_COMMANDS


@pytest.mark.parametrize(
    'context',
    [['commands_not_list']],
    indirect=True
)
def test_commands_not_list(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_COMMANDS_NOT_LIST


@pytest.mark.parametrize(
    'context',
    [['no_config']],
    indirect=True
)
def test_no_config(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_CONFIG_MISSING


@pytest.mark.parametrize(
    'context',
    [['config_not_dict']],
    indirect=True
)
def test_config_not_dict(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_CONFIG_NOT_DICT


@pytest.mark.parametrize(
    'context',
    [['no_image']],
    indirect=True
)
def test_no_image(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_NO_IMAGE


@pytest.mark.parametrize(
    'context',
    [['image_not_str']],
    indirect=True
)
def test_image_not_str(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_IMAGE_NOT_STR


@pytest.mark.parametrize(
    'context',
    [['image_not_found']],
    indirect=True
)
def test_image_not_found(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0


@pytest.mark.parametrize(
    'context',
    [['after_failure_not_list']],
    indirect=True
)
def test_after_failure_not_list(context: Context):
    completed, failed = context.wait()
    assert failed == set(context.jobs())
    assert len(completed) == 0
    assert context.job_status(context.jobs()[0]) is JobStatus.ERROR_AFTER_FAILURE_NOT_LIST
