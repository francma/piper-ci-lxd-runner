from typing import Dict, Any, List
from enum import Enum
from pathlib import Path

from pykwalify.core import Core as Validator

import piper_lxd.schemas as schemas


class ResponseJobStatus(Enum):
    OK = 'OK'
    CANCEL = 'CANCEL'
    ERROR = 'ERROR'


class RequestJobStatus(Enum):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


class Job:

    COMMAND_PREFIX = 'piper'

    COMMAND_CWD = 'cd "{}"'

    COMMAND_WAIT_FOR_NETWORK = '\n'.join([
        'i=1; d=0',
        'while [ $i -le 50 ]; do',
        'i=$(($i + 1))',
        'if [ -z "$(ip route get 8.8.8.8 2>/dev/null | grep -v unreachable)" ]; then',
        'sleep 0.1; continue',
        'fi',
        'd=1; break;',
        'done',
        'if [ $d -eq 0 ]; then',
        'exit 1',
        'fi',
    ])

    COMMAND_FIRST = 'PIPER_GLOB_EXIT=0'

    COMMAND_START = '\n'.join([
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
        'printf "::' + COMMAND_PREFIX + ':command:{}:start:%d::\\n" `date +%s`;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
    ])

    COMMAND_END = '\n'.join([
        'PIPER_PREV_EXIT=$?;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
        'PIPER_GLOB_EXIT=$PIPER_PREV_EXIT;',
        'printf "::' + COMMAND_PREFIX + ':command:{}:end:%d:%d::\\n" `date +%s` $PIPER_PREV_EXIT;',
        'fi;',
    ])

    COMMAND_LAST = 'exit $PIPER_GLOB_EXIT;'

    AFTER_FAILURE_START = '\n'.join([
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
        'printf "::' + COMMAND_PREFIX + ':after_failure:{}:start:%d::\\n" `date +%s`;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
    ])

    AFTER_FAILURE_END = '\n'.join([
        'PIPER_PREV_EXIT=$?;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
        'printf "::' + COMMAND_PREFIX + ':after_failure:{}:end:%d:%d::\\n" `date +%s` $PIPER_PREV_EXIT;',
        'fi;',
    ])

    def __init__(self, job: Dict[str, Any]) -> None:
        validator = Validator(source_data=job, schema_data=schemas.job)
        validator.validate()

        self._secret = job['secret']
        self._after_failure = job['after_failure'] if 'after_failure' in job else []
        self._commands = job['commands']
        self._env = job['env'] if 'env' in job else {}
        self._image = job['image']
        self._origin = job['repository']['origin']
        self._branch = job['repository']['branch']
        self._commit = job['repository']['commit']
        self._cwd = '/piper'
        self._private_key = Path(job['repository']['private_key']) if 'private_key' in job['repository'] else None

        self._env = {k: str(v) for k, v in self._env.items()}

    @property
    def commands(self) -> List[str]:
        return self._commands

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def commit(self) -> str:
        return self._commit

    @property
    def secret(self) -> str:
        return self._secret

    @property
    def image(self) -> str:
        return self._image

    @property
    def env(self) -> Dict[str, Any]:
        return self._env

    @property
    def private_key(self) -> Path:
        return self._private_key

    @property
    def lxd_source(self) -> Dict[str, str]:
        if self.image.startswith('fingerprint:'):
            return {
                'type': 'image',
                'fingerprint': self.image[len('fingerprint:'):]
            }

        return {
            'type': 'image',
            'alias': self.image
        }

    @property
    def script(self) -> str:
        script = list()
        script.append(self.COMMAND_CWD.format(self._cwd))
        script.append(self.COMMAND_WAIT_FOR_NETWORK)

        script.append(self.COMMAND_FIRST)

        for idx, command in enumerate(self.commands):
            script.append(self.COMMAND_START.format(idx))
            script.append(command)
            script.append(self.COMMAND_END.format(idx))

        for idx, command in enumerate(self._after_failure):
            script.append(self.AFTER_FAILURE_START.format(idx))
            script.append(command)
            script.append(self.AFTER_FAILURE_END.format(idx))

        script.append(self.COMMAND_LAST)

        return '\n'.join(script)
