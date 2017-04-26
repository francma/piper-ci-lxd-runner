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

    # TODO add keys for private repos
    # git config core.sshCommand "ssh -i ~/.ssh/id_rsa_example -F /dev/null"
    def clone(self, destination: str):
        command = ['git', 'clone', self.branch.repository.origin, '.']
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)

        command = ['git', 'reset', '--hard', self.sha]
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)

        command = ['git', 'submodule', 'update', '--init', '--recursive']
        process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            raise GitCloneException(err)