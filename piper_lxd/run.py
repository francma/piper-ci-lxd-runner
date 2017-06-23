#!/usr/bin/env python3
import argparse
import json
import logging.config
import time
from pathlib import Path

import requests
from piper_lxd.models.runner import Executor

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
    config = Config(json.loads(parsed['config'].open()))
    connection = Connection(config.runner.endpoint)

    while True:
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

        r = Executor(connection, config.runner.interval, config.lxd, job)
        r.start()


if __name__ == '__main__':
    main()
