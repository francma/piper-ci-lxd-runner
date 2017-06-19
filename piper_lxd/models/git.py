import subprocess

from piper_lxd.models.exceptions import *


def clone(origin, branch, commit, destination: str, ssh_keys_path=None):
    env = dict()
    if ssh_keys_path is not None:
        assert type(ssh_keys_path) is list
        env['GIT_SSH_COMMAND'] = 'ssh -i ' + ' -i '.join(ssh_keys_path) + ' -F /dev/null'

    command = ['git', 'clone', '--recursive', '--branch', branch, origin, '.']
    process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = process.communicate()
    if process.returncode != 0:
        raise CloneException(err)

    command = ['git', 'checkout', '-f', commit]
    process = subprocess.Popen(command, cwd=destination, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = process.communicate()
    if process.returncode != 0:
        raise CloneException(err)
