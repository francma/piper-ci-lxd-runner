from typing import Dict, Any
from enum import Enum

from piper_lxd.models.exceptions import JobException


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

    def __init__(self, job: Dict[str, Any]):
        if 'secret' not in job:
            raise JobException('job["secret"] not found', secret=None)
        self._secret = job['secret']

        if 'commands' not in job:
            raise JobException('job["commands"] not found', secret=self._secret)
        if not isinstance(job['commands'], list):
            raise JobException('job["commands"] not list', secret=self._secret)
        if 'image' not in job:
            raise JobException('job["image"] not found', secret=self._secret)
        if not isinstance(job['image'], str):
            raise JobException('job["image"] not str', secret=self._secret)
        if 'env' in job:
            if not isinstance(job['env'], dict):
                raise JobException('job["env"] not dict', secret=self._secret)
            for k, v in job['env'].items():
                if not isinstance(k, str) or type(v) not in [str, int, bool]:
                    raise JobException('job["env"]["{}"] = {} is invalid'.format(k, v), secret=self._secret)
        if 'after_failure' in job and not isinstance(job['after_failure'], list):
            raise JobException('job["after_failure"] not list', secret=self._secret)
        if 'repository' not in job:
            raise JobException('job["repository"] not found', secret=self._secret)
        if not isinstance(job['repository'], dict):
            raise JobException('job["repository"] not dict', secret=self._secret)
        if 'origin' not in job['repository']:
            raise JobException('job["repository"]["origin"] not found', secret=self._secret)
        if not isinstance(job['repository']['origin'], str):
            raise JobException('job["repository"]["origin"] not str', secret=self._secret)
        if 'branch' not in job['repository']:
            raise JobException('job["repository"]["branch"] not found', secret=self._secret)
        if not isinstance(job['repository']['branch'], str):
            raise JobException('job["repository"]["branch"] not str', secret=self._secret)
        if 'commit' not in job['repository']:
            raise JobException('job["repository"]["commit"] not found', secret=self._secret)
        if not isinstance(job['repository']['commit'], str):
            raise JobException('job["repository"]["commit"] not str', secret=self._secret)

        self._after_failure = job['after_failure'] if 'after_failure' in job else []
        self._commands = job['commands']
        self._env = job['env'] if ('env' in job and job['env']) else {}
        self._image = job['image']
        self._origin = job['repository']['origin']
        self._branch = job['repository']['branch']
        self._commit = job['repository']['commit']
        self._cwd = '/piper'

    @property
    def commands(self):
        return self._commands

    @property
    def origin(self):
        return self._origin

    @property
    def branch(self):
        return self._branch

    @property
    def commit(self):
        return self._commit

    @property
    def secret(self):
        return self._secret

    @property
    def image(self):
        return self._image

    @property
    def env(self):
        return self._env

    @property
    def lxd_source(self):
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
    def script(self):
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
