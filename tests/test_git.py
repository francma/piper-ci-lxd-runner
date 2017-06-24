import tempfile
import os
import subprocess
from pathlib import Path
import pytest

from piper_lxd.models import git
from piper_lxd.models.exceptions import CloneException


def test_basic():
    origin = 'https://github.com/francma/piper-ci-test-repo.git'
    branch = 'master'
    commit = 'e7a4739755a81a06242bc3249e36b133b3783f9b'

    with tempfile.TemporaryDirectory() as td:
        git.clone(origin, branch, commit, Path(td))
        command = ['git', 'log', '-1', '--format=%H']
        process = subprocess.Popen(command, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == commit
        assert sorted(['submodule', 'README.md', '.gitmodules', '.git']) == sorted(os.listdir(td))

        command = ['git', 'log', '-1', '--format=%H']
        cwd = os.path.join(td, 'submodule')
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert sorted(['README.md', '.git']) == sorted(os.listdir(cwd))


def test_with_keys():
    origin = 'git@github.com:francma/piper-ci-test-repo.git'
    branch = 'master'
    commit = '09d13744b731539507bf7071f2e444aeba01cbc5'
    repo_key = Path('tests/keys/privkey_repo').resolve()
    sub_key = Path('tests/keys/privkey_submodule').resolve()

    with tempfile.TemporaryDirectory() as td:
        git.clone(origin, branch, commit, Path(td), [repo_key, sub_key])
        command = ['git', 'log', '-1', '--format=%H']
        process = subprocess.Popen(command, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == commit
        assert sorted(['submodule', 'README.md', '.gitmodules', '.git']) == sorted(os.listdir(td))

        command = ['git', 'log', '-1', '--format=%H']
        cwd = os.path.join(td, 'submodule')
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert sorted(['README.md', '.git']) == sorted(os.listdir(cwd))


def test_fail_1():
    origin = 'https://github.com/francma/NONEXISTENT.git'
    branch = 'master'
    commit = 'e7a4739755a81a06242bc3249e36b133b3783f9b'

    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(CloneException):
            git.clone(origin, branch, commit, Path(td))


def test_fail_2():
    origin = 'https://github.com/francma/piper-ci-test-repo.git'
    branch = 'master'
    commit = 'e7a4739755a8nonexistent49e36b133b3783f9b'

    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(CloneException):
            git.clone(origin, branch, commit, Path(td))
