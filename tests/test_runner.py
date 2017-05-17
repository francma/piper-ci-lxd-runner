import json
from typing import List, Dict
import re
import io

from piper_lxd.models.runner import Runner, Status
from piper_lxd.models.job import Job


def get_fetch_function(jobs: List):
    def fn(self):
        try:
            job = jobs.pop()
        except IndexError:
            raise StopIteration
        with open('tests/jobs/{}.json'.format(job)) as fd:
            return json.load(fd)

    return fn


def get_report_function(outputs: Dict[str, str], statuses: Dict[str, List[Status]]):
    def fn(self, secret: str, status: Status, data=None):
        if secret not in statuses:
            statuses[secret] = list()
        if secret not in outputs:
            outputs[secret] = ''
        statuses[secret].append(status)
        if data is not None:
            outputs[secret] += data

    return fn


def get_clone_function():
    def fn(origin, branch, commit, destination: str, ssh_keys_path=None):
        return

    return fn


def _run(runner, jobs, monkeypatch):
    output = dict()
    statuses = dict()
    monkeypatch.setattr('piper_lxd.models.runner.Runner._fetch_job', get_fetch_function(jobs))
    monkeypatch.setattr('piper_lxd.models.runner.Runner._report_status', get_report_function(output, statuses))

    try:
        runner.run()
    except StopIteration:
        pass

    return output, statuses


def test_fail(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['fail'], monkeypatch)
    assert statuses['fail'][-1] is Status.COMPLETED

    with io.StringIO(output['fail']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:1::$', st.readline())

        assert st.readline() == ''


def test_sleep(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['sleep'], monkeypatch)
    assert statuses['sleep'][-1] is Status.COMPLETED

    with io.StringIO(output['sleep']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^START$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:start:\d+::$', st.readline())
        assert re.match(r'^END', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_clone(runner: Runner, monkeypatch):
    output, statuses = _run(runner, ['clone'], monkeypatch)
    assert statuses['clone'][-1] is Status.COMPLETED

    with io.StringIO(output['clone']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        while True:
            line = st.readline()
            assert line != ''
            if re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', line):
                break
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        while True:
            line = st.readline()
            assert line != ''
            if re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', line):
                break
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:start:\d+::$', st.readline())
        assert st.readline().strip() == 'e7a4739755a81a06242bc3249e36b133b3783f9b'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:start:\d+::$', st.readline())
        assert sorted(st.readline().strip().split(' ')) == sorted(['README.md', 'submodule'])
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:4:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:4:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:5:start:\d+::$', st.readline())
        assert st.readline().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:5:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:6:start:\d+::$', st.readline())
        assert sorted(st.readline().strip().split(' ')) == sorted(['README.md'])
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:6:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_env(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['env'], monkeypatch)
    assert statuses['env'][-1] is Status.COMPLETED

    with io.StringIO(output['env']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert st.readline().strip() == 'I want to die'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert st.readline().strip() == 'Please'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_after_failure(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['after_failure'], monkeypatch)
    assert statuses['after_failure'][-1] is Status.COMPLETED

    with io.StringIO(output['after_failure']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:1::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:start:\d+::$', st.readline())
        assert st.readline().strip() == '1'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_cd(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['cd'], monkeypatch)
    assert statuses['cd'][-1] is Status.COMPLETED

    with io.StringIO(output['cd']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        pwd = st.readline()
        assert pwd
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:start:\d+::$', st.readline())
        pwd2 = st.readline()
        assert pwd2
        assert pwd2 != pwd
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_multiple(runner: Runner, monkeypatch):
    monkeypatch.setattr('piper_lxd.models.git.clone', get_clone_function())
    output, statuses = _run(runner, ['multiple_1', 'multiple_2'], monkeypatch)
    assert statuses['multiple_1'][-1] is Status.COMPLETED
    assert statuses['multiple_2'][-1] is Status.COMPLETED

    with io.StringIO(output['multiple_1']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert st.readline().strip() == '1'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert st.readline() == ''

    with io.StringIO(output['multiple_2']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert st.readline().strip() == '2'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert st.readline() == ''
