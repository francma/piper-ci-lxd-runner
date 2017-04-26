import subprocess

from piper_lxd.models.exceptions import *


class Repository:

    def __init__(self, origin):
        self._origin = origin

    @property
    def origin(self):
        return self._origin


class Branch:

    def __init__(self, ref: str, repository: Repository):
        self._ref = ref
        self._repository = repository

    @property
    def ref(self):
        return self._ref

    @property
    def repository(self):
        return self._repository


class Commit:

    def __init__(self, sha: str, branch: Branch):
        self._sha = sha
        self._branch = branch

    @property
    def sha(self):
        return self._sha

    @property
    def branch(self):
        return self._branch

    def clone(self, destination: str, ssh_keys_path=None):
        env = dict()
        if ssh_keys_path is not None:
            assert type(ssh_keys_path) is list
            env['GIT_SSH_COMMAND'] = 'ssh -i ' + ' -i '.join(ssh_keys_path) + ' -F /dev/null'

        command = ['git', 'clone', self.branch.repository.origin, '.']
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)

        command = ['git', 'reset', '--hard', self.sha]
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)

        command = ['git', 'submodule', 'update', '--init', '--recursive']
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)
