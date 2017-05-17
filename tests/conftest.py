import os
import uuid
import tempfile
import shutil

import pytest

from piper_lxd.models.runner import Runner, Status


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

    yield runner

    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)


