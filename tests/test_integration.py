import pytest
import subprocess
import time
import os
import shlex
import uuid
import tempfile
import signal
import re


def start_dummy_server(test_key, jobs=[]):
    cwd = os.path.dirname(os.path.realpath(__file__))
    tempdir = os.path.join(tempfile.tempdir, test_key)
    queue_file = os.path.join(tempdir, 'queue')

    with open(queue_file, 'w') as fp:
        fp.write(os.linesep.join(jobs))

    command = shlex.split('''
        uwsgi 
        --master 
        --http :4444 
        --http-websockets 
        --wsgi dummy_driver:app 
        --processes 8 
        --env PIPER_TEST_KEY=''' + test_key
    )
    stdout = open(os.path.join(os.path.join(tempdir, 'dummy_server.out')), 'w')
    stderr = open(os.path.join(os.path.join(tempdir, 'dummy_server.err')), 'w')

    server = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd)

    return server


def start_piper_lxd(test_key):
    command = shlex.split('''
        piper_lxd 
        --driver-url 127.0.0.1:4444
        --runner-token TOKEN 
        --lxd-profiles piper-ci
        --lxd-endpoint https://127.0.0.1:8443
        --lxd-key ~/.config/lxc-client/client.key
        --lxd-cert ~/.config/lxc-client/client.crt
    ''')
    tempdir = os.path.join(tempfile.tempdir, test_key)
    os.makedirs(tempdir, exist_ok=True)

    stdout = open(os.path.join(os.path.join(tempdir, 'piper_lxd.out')), 'w')
    stderr = open(os.path.join(os.path.join(tempdir, 'piper_lxd.err')), 'w')
    worker = subprocess.Popen(command, stdout=stdout, stderr=stderr)

    return worker


def get_test_key():
    return 'PIPER-{}-{}'.format(int(time.time()), uuid.uuid4().hex)


def wait_until_finished(test_key, jobs, timeout=60):
    for i in range(timeout * 10):
        test_temp_files = os.listdir(os.path.join(tempfile.gettempdir(), test_key, 'job'))
        completed = [''.join(x.split('-')[:-1]) for x in test_temp_files if x.endswith('-completed')]
        failed = [''.join(x.split('-')[:-1]) for x in test_temp_files if x.endswith('-failed')]
        if sorted(completed + failed) == sorted(jobs):
            return completed, failed
        time.sleep(.1)

    return completed, failed


@pytest.fixture
def connect(request):
    test_key, jobs = request.param

    tempdir = os.path.join(tempfile.tempdir, test_key)
    os.makedirs(tempdir, exist_ok=True)
    os.makedirs(os.path.join(tempdir, 'job'))

    server = start_dummy_server(test_key=test_key, jobs=jobs)
    client = start_piper_lxd(test_key=test_key)

    # wait for start
    # time.sleep(1)

    # check if started and running
    assert server.returncode is None
    assert client.returncode is None

    # return
    yield server, client, request.param[0], request.param[1], tempdir

    # stop server and client
    # https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html
    os.kill(server.pid, signal.SIGINT)
    server.wait()

    client.terminate()
    client.wait()


@pytest.mark.parametrize(
    'connect',
    [[
        get_test_key(),
        ['sleep']
    ]],
    indirect=True
)
def test_sleep(connect):
    server, worker, test_key, jobs, tempdir = connect
    completed, failed = wait_until_finished(test_key, jobs, timeout=30)
    assert sorted(completed) == sorted(jobs), "expected {}, got {}".format(jobs, completed)

    with open(os.path.join(tempdir, 'job', 'sleep')) as fp:
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
    'connect',
    [[
        get_test_key(),
        ['cd']
    ]],
    indirect=True
)
def test_cd(connect):
    server, worker, test_key, jobs, tempdir = connect
    completed, failed = wait_until_finished(test_key, jobs)
    assert sorted(completed) == sorted(jobs), "expected {}, got {}".format(jobs, completed)

    with open(os.path.join(tempdir, 'job', 'cd')) as fp:
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
    'connect',
    [[
        get_test_key(),
        ['env']
    ]],
    indirect=True
)
def test_env(connect):
    server, worker, test_key, jobs, tempdir = connect
    completed, failed = wait_until_finished(test_key, jobs)
    assert sorted(completed) == sorted(jobs), "expected {}, got {}".format(jobs, completed)

    with open(os.path.join(tempdir, 'job', 'env')) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert fp.readline().strip() == 'I want to die'
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:0::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:1:start:\d+::$', fp.readline())
        assert fp.readline().strip() == 'Please'
        assert re.match(r'^::piper_lxd-ci:command:1:end:\d+:0::$', fp.readline())

        assert fp.readline() == ''


@pytest.mark.parametrize(
    'connect',
    [[
        get_test_key(),
        ['fail']
    ]],
    indirect=True
)
def test_fail(connect):
    server, worker, test_key, jobs, tempdir = connect
    completed, failed = wait_until_finished(test_key, jobs)
    assert sorted(completed) == sorted(jobs), "expected {}, got {}".format(jobs, completed)

    with open(os.path.join(tempdir, 'job', 'fail')) as fp:
        assert re.match(r'^::piper_lxd-ci:command:0:start:\d+::$', fp.readline())
        assert re.match(r'^::piper_lxd-ci:command:0:end:\d+:1::$', fp.readline())

        assert fp.readline() == ''


# @pytest.mark.parametrize(
#     'connect',
#     [[
#         get_test_key(),
#         ['not_json']
#     ]],
#     indirect=True
# )
# def test_not_json(connect):
#     server, worker, test_key, jobs, tempdir = connect
#     completed, failed = wait_until_finished(test_key, jobs)
#     assert sorted(failed) == sorted(jobs), "expected {}, got {}".format(failed, completed)
