import re
import io
import urllib3

import pytest

from piper_lxd.models.runner import Runner, ReportStatusFail
from piper_lxd.models.job import Job, ResponseJobStatus, RequestJobStatus

urllib3.disable_warnings()


def test_fail(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['fail'])
    assert statuses['fail'][-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output['fail']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:1::$', st.readline())

        assert st.readline() == ''


def test_sleep(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['sleep'])
    assert statuses['sleep'][-1] is RequestJobStatus.COMPLETED

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


def test_clone(runner: Runner):
    output, statuses = runner.run_test(['clone'])
    assert statuses['clone'][-1] is RequestJobStatus.COMPLETED

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


def test_env(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['env'])
    assert statuses['env'][-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output['env']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert st.readline().strip() == 'I want to die'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert st.readline().strip() == 'Please'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_after_failure(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['after_failure'])
    assert statuses['after_failure'][-1] is RequestJobStatus.COMPLETED

    with io.StringIO(output['after_failure']) as st:
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:0:end:\d+:0::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:start:\d+::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':command:1:end:\d+:1::$', st.readline())
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:start:\d+::$', st.readline())
        assert st.readline().strip() == '1'
        assert re.match(r'^::' + Job.COMMAND_PREFIX + ':after_failure:0:end:\d+:0::$', st.readline())

        assert st.readline() == ''


def test_cd(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['cd'])
    assert statuses['cd'][-1] is RequestJobStatus.COMPLETED

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


def test_multiple(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['multiple_1', 'multiple_2'])
    assert statuses['multiple_1'][-1] is RequestJobStatus.COMPLETED
    assert statuses['multiple_2'][-1] is RequestJobStatus.COMPLETED

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


@pytest.mark.timeout(60)
def test_cancel(runner: Runner, empty_clone):
    output, statuses = runner.run_test(['sleep_long'], ResponseJobStatus.CANCEL)


# @pytest.mark.timeout(10)
# def test_not_responding(runner: Runner, empty_clone, monkeypatch):
#     def raise_exc(a, b, c, d):
#         print(1000*'RAISE')
#         raise ReportStatusFail
#
#     monkeypatch.setattr('piper_lxd.models.runner.Runner._report_status', raise_exc)
#     output, statuses = runner.run_test(['sleep_long'])
