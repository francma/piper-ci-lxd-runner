from typing import Dict, List


class Job:

    COMMAND_START = 'printf "::piper_lxd-ci:command:{}:start:%d::\n" `date +%s`'
    COMMAND_END = ''.join([
        'd3d8972793203a4505634f7c3607b4e3697862a=$?;',
        'printf "::piper_lxd-ci:command:{}:end:%d:%d::\n" `date +%s` $d3d8972793203a4505634f7c3607b4e3697862a;',
        'if [[ $d3d8972793203a4505634f7c3607b4e3697862a != 0 ]];',
        'then exit $d3d8972793203a4505634f7c3607b4e3697862a;',
        'fi'
    ])

    def __init__(self, commands: List[str], secret: str, image: str, env: Dict[str, str]):
        self._commands = commands
        self._secret = secret
        self._image = image
        self._env = env

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
        for idx, command in enumerate(self.commands):
            script.append(self.COMMAND_START.format(idx))
            script.append(command)
            script.append(self.COMMAND_END.format(idx))

        return '\n'.join(script)
