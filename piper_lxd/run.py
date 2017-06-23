#!/usr/bin/env python3
import argparse
import logging.config
import time
from pathlib import Path
import multiprocessing

import requests
import yaml
from piper_lxd.models.executor import Executor

from piper_lxd.models.config import Config
from piper_lxd.models.connection import Connection

LOG = logging.getLogger('piper-lxd')


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        'config',
        help='Configuration file',
        type=Path
    )

    parsed = vars(parser.parse_args())
    config = Config(yaml.load(parsed['config'].open()))
    connection = Connection(config.runner.endpoint)
    logging.config.dictConfig(config.logging.config)

    while True:
        if multiprocessing.active_children() == config.runner.instances:
            time.sleep(config.runner.interval.total_seconds())
            continue

        try:
            job = connection.fetch_job(config.runner.token)
        except requests.exceptions.ConnectionError as e:
            LOG.warning('Job fetch from failed: {}'.format(e))
            time.sleep(config.runner.interval.total_seconds())
            continue
        if job is None:
            LOG.debug('No job available')
            time.sleep(config.runner.interval.total_seconds())
            continue

        r = Executor(connection, config.runner.interval, config.lxd, job, name=job.secret)
        r.start()


if __name__ == '__main__':
    main()
