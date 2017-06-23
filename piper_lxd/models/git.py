import subprocess
from pathlib import Path
from typing import List, Optional

from piper_lxd.models.exceptions import CloneException


def clone(origin: str, branch: str, commit: str, destination: Path, ssh_keys_path: Optional[List[Path]]=None) -> None:
    env = dict()
    if ssh_keys_path is not None:
        paths = [str(x.expanduser()) for x in ssh_keys_path]
        env['GIT_SSH_COMMAND'] = 'ssh -i ' + ' -i '.join(paths) + ' -F /dev/null'

    command = ['git', 'clone', '--recursive', '--branch', branch, origin, '.']
    process = subprocess.Popen(command, cwd=str(destination), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = process.communicate()
    if process.returncode != 0:
        raise CloneException(err)

    command = ['git', 'checkout', '-f', commit]
    process = subprocess.Popen(command, cwd=str(destination), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = process.communicate()
    if process.returncode != 0:
        raise CloneException(err)
