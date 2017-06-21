import subprocess
from pathlib import Path
from typing import List

from piper_lxd.models.exceptions import *


def clone(origin: str, branch: str, commit: str, destination: Path, ssh_keys_path: List[Path]=None) -> None:
    env = dict()
    if ssh_keys_path is not None:
        ssh_keys_path = [x.expanduser() for x in ssh_keys_path]
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
