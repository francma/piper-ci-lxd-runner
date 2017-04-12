from typing import Dict, List


class Job:

    COMMAND_FIRST = 'PIPER_GLOB_EXIT=0'

    COMMAND_START = '\n'.join([
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
        'printf "::piper_lxd-ci:command:{}:start:%d::\\n" `date +%s`;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
    ])

    COMMAND_END = '\n'.join([
        'PIPER_PREV_EXIT=$?;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT = 0 ]; then',
        'PIPER_GLOB_EXIT=$PIPER_PREV_EXIT;',
        'printf "::piper_lxd-ci:command:{}:end:%d:%d::\\n" `date +%s` $PIPER_PREV_EXIT;',
        'fi;',
    ])

    COMMAND_LAST = 'exit $PIPER_GLOB_EXIT;'

    AFTER_FAILURE_START = '\n'.join([
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
        'printf "::piper_lxd-ci:after_failure:{}:start:%d::\\n" `date +%s`;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
    ])

    AFTER_FAILURE_END = '\n'.join([
        'PIPER_PREV_EXIT=$?;',
        'fi;',
        'if [ $PIPER_GLOB_EXIT != 0 ]; then',
        'printf "::piper_lxd-ci:after_failure:{}:end:%d:%d::\\n" `date +%s` $PIPER_PREV_EXIT;',
        'fi;',
    ])

    def __init__(self, commands: List[str], secret: str, image: str, after_failure: List[str], env: Dict[str, str]):
        self._commands = commands
        self._secret = secret
        self._image = image
        self._env = env
        self._after_failure = after_failure

    @property
    def commands(self):
        return self._commands

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
        script = []
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
