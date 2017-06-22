#!/usr/bin/env python3
import logging
import logging.config
import argparse
import sys
from datetime import timedelta
from pathlib import Path
import collections

import yaml
from pykwalify.core import Core as Validator
from pykwalify.errors import SchemaError

from piper_lxd.models.runner import Runner

LOG = logging.getLogger('piper-lxd')


def merge_dicts(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = merge_dicts(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

defaults = {
    'lxd': {
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


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        'config',
        help='Configuration file',
        type=Path
    )

    parsed = vars(parser.parse_args())
    config = yaml.load(parsed['config'].open())

    validator = Validator(schema_files=['config.schema.yml'], source_data=config)
    try:
        validator.validate()
    except SchemaError as e:
        print(e, file=sys.stderr)
        exit(2)

    config = merge_dicts(config, defaults)
    logging.config.dictConfig(config['logging'])
    config['lxd']['cert'] = Path(config['lxd']['cert'])
    config['lxd']['key'] = Path(config['lxd']['key'])
    config['runner']['interval'] = timedelta(seconds=config['runner']['interval'])

    a = {'runner_' + a: b for a, b in config['runner'].items()}
    b = {'lxd_' + a: b for a, b in config['lxd'].items()}
    runner_config = {**a, **b}

    runners = list()
    try:
        for i in range(config['runner']['instances']):
            r = Runner(**runner_config)
            runners.append(r)
            r.start()

        for r in runners:
            r.join()
    except KeyboardInterrupt:
        for r in runners:
            LOG.info('Terminating worker(PID={})'.format(r.pid))
            r.terminate()


if __name__ == '__main__':
    main()
