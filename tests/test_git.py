import tempfile
import os
import subprocess

from piper_lxd.models.git import *


def test_basic_clone():
    repo = Repository('https://github.com/francma/piper-ci-test-repo.git')
    branch = Branch('master', repo)
    commit_hash = 'e7a4739755a81a06242bc3249e36b133b3783f9b'
    commit = Commit(commit_hash, branch)

    with tempfile.TemporaryDirectory() as td:
        commit.clone(td)
        command = ['git', 'log', '-1', '--format=%H']
        process = subprocess.Popen(command, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == commit_hash
        assert sorted(['submodule', 'README.md', '.gitmodules', '.git']) == sorted(os.listdir(td))

        command = ['git', 'log', '-1', '--format=%H']
        cwd = os.path.join(td, 'submodule')
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert sorted(['README.md', '.git']) == sorted(os.listdir(cwd))


def test_clone_with_keys():
    repo = Repository('git@github.com:francma/piper-ci-test-repo.git')
    branch = Branch('master', repo)
    commit_hash = '09d13744b731539507bf7071f2e444aeba01cbc5'
    commit = Commit(commit_hash, branch)

    with tempfile.TemporaryDirectory() as td:
        repo_key = os.path.abspath('tests/keys/privkey_repo')
        sub_key = os.path.abspath('tests/keys/privkey_submodule')

        commit.clone(td, ssh_keys_path=[repo_key, sub_key])
        command = ['git', 'log', '-1', '--format=%H']
        process = subprocess.Popen(command, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == commit_hash
        assert sorted(['submodule', 'README.md', '.gitmodules', '.git']) == sorted(os.listdir(td))

        command = ['git', 'log', '-1', '--format=%H']
        cwd = os.path.join(td, 'submodule')
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0
        assert out.decode().strip() == '82a5fe97f68c66db1ba232338122b715dc776610'
        assert sorted(['README.md', '.git']) == sorted(os.listdir(cwd))
