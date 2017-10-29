#!/usr/bin/env python3
import argparse
import logging.config
import time
from pathlib import Path
import multiprocessing

import yaml
from pykwalify.errors import SchemaError

from piper_lxd.models.executor import Executor
from piper_lxd.models.config import Config
from piper_lxd.models.connection import Connection
from piper_lxd.models.errors import PConnectionException

LOG = logging.getLogger('piper-lxd')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config',
        help='Configuration file',
        type=Path
    )

    parsed = vars(parser.parse_args())
    path = parsed['config'].expanduser()
    config = Config(yaml.load(path.open()))
    connection = Connection(config.runner.endpoint)
    logging.config.dictConfig(config.logging.config)

    while True:
        if multiprocessing.active_children() == config.runner.instances:  # type: ignore
            time.sleep(config.runner.interval.total_seconds())
            continue

        job = None
        try:
            job = connection.fetch_job(config.runner.token)
        except PConnectionException as e:
            LOG.warning('Job fetch from failed: {}'.format(e))
        except SchemaError as e:
            LOG.warning('Fetched Job has invalid schema: {}'.format(e))

        if job is None:
            LOG.debug('No job available')
            time.sleep(config.runner.interval.total_seconds())
            continue

        Executor(connection, config.runner.interval, config.lxd, job, name=job.secret).start()


if __name__ == '__main__':
    main()
