import re
import io
import urllib3

import pytest
import requests

from piper_lxd.models.executor import Executor
from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus

urllib3.disable_warnings()


def test_fail(connection, config, empty_clone):
    connection.push_job('fail')
    job = connection.fetch_job('token')
    exe = Executor(connection, config.runner.interval, config.lxd, job)
    exe.run()

    output = connection.logs['fail']
    statuses = connection.statuses['fail']
    assert statuses[-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:1::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:start:\d+::$', st.readline())
        assert st.readline().strip() == 'failed!'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_ok(connection, config, empty_clone):
    connection.push_job('ok')
    job = connection.fetch_job('token')
    exe = Executor(connection, config.runner.interval, config.lxd, job)
    exe.run()

    output = connection.logs['ok']
    statuses = connection.statuses['ok']
    assert statuses[-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert st.readline().strip() == 'I want to die'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert st.readline().strip() == 'Please'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:start:\d+::$', st.readline())
        pwd = st.readline()
        assert pwd
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:2:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:3:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:4:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:4:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:5:start:\d+::$', st.readline())
        pwd2 = st.readline()
        assert pwd2
        assert pwd2 != pwd
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:5:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_clone(connection, config):
    connection.push_job('clone')
    job = connection.fetch_job('token')
    exe = Executor(connection, config.runner.interval, config.lxd, job)
    exe.run()

    output = connection.logs['clone']
    statuses = connection.statuses['clone']
    assert statuses[-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output) as st:
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


@pytest.mark.timeout(60)
def test_cancel(connection, config, empty_clone):
    connection.report = lambda a, b, c, d=None: ResponseJobStatus.CANCEL
    connection.push_job('sleep_long')
    job = connection.fetch_job('token')
    exe = Executor(connection, config.runner.interval, config.lxd, job)
    exe.run()


@pytest.mark.timeout(10)
def test_not_responding(connection, config, empty_clone):
    def raise_exc(a, b, c, d=None):
        raise requests.RequestException
    connection.report = raise_exc
    connection.push_job('sleep_long')
    job = connection.fetch_job('token')
    exe = Executor(connection, config.runner.interval, config.lxd, job)
    exe.run()
