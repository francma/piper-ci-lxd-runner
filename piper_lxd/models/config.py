from pathlib import Path
from typing import List, Dict, Any
from datetime import timedelta
import collections

import yaml
from pykwalify.core import Core as Validator

import piper_lxd.schemas as schemas


class LxdConfig:

    def __init__(self, verify: bool, profiles: List[str], endpoint: str, cert: Path, key: Path):
        self.verify = verify
        self.profiles = profiles
        self.endpoint = endpoint
        self.cert = cert
        self.key = key


class RunnerConfig:

    def __init__(self, token: str, interval: timedelta, instances: int, endpoint: str):
        self.token = token
        self.interval = interval
        self.instances = instances
        self.endpoint = endpoint


class LoggingConfig:

    def __init__(self, config: Dict[Any, Any]):
        self.config = config


class Config:

    _DEFAULTS = {
        'lxd': {
            'profiles': [],
            'verify': False,
        },
        'runner': {
            'interval': 3,
            'instances': 1,
            'repository_dir': '/tmp',
        },
        'logging': {
            'version': 1,
        },
    }

    def __init__(self, d: Dict[Any, Any]):
        validator = Validator(schema_data=schemas.config, source_data=d)
        validator.validate()
        config = self._merge_dicts(self._DEFAULTS, d)

        self.logging = LoggingConfig(config['logging'])
        self.lxd = LxdConfig(
            verify=config['lxd']['verify'],
            profiles=config['lxd']['profiles'],
            endpoint=config['lxd']['endpoint'],
            cert=Path(config['lxd']['cert']),
            key=Path(config['lxd']['key']),
        )
        self.runner = RunnerConfig(
            token=config['runner']['token'],
            interval=timedelta(seconds=config['runner']['interval']),
            instances=config['runner']['instances'],
            endpoint=config['runner']['endpoint'],
        )

    def _merge_dicts(self, d, u):
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                r = self._merge_dicts(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d
