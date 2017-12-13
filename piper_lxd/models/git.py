import subprocess
from pathlib import Path

from piper_lxd.models.errors import PCloneException


def clone(origin: str, branch: str, commit: str, destination: Path) -> None:
    command = ['git', 'clone', '--recursive', '--branch', branch, origin, '.']
    process = subprocess.Popen(
        command,
        cwd=str(destination),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    out, err = process.communicate()
    if process.returncode != 0:
        raise PCloneException(err)

    command = ['git', 'checkout', '-f', commit]
    process = subprocess.Popen(
        command,
        cwd=str(destination),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    out, err = process.communicate()
    if process.returncode != 0:
        raise PCloneException(err)
