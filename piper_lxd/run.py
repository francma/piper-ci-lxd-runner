#!/usr/bin/env python3
import configparser
import logging
import argparse
import sys
from datetime import timedelta
from typing import List, Dict, Any
from pathlib import Path

from piper_lxd.models.runner import Runner

logging.basicConfig()
LOG = logging.getLogger('piper-lxd')
LOG.setLevel(logging.DEBUG)


def parse_args(args: List[str]) -> Dict[str, Any]:
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument(
        '--config',
        help='Configuration file',
        type=Path
    )
    config_path, args = conf_parser.parse_known_args(args)
    config_path = config_path.config
    config_file_values = {}

    if config_path:
        config_file = configparser.ConfigParser()
        parsed_file = config_file.read(config_path)
        for _, section in config_file.items():
            for key, value in section.items():
                if section.name == 'lxd' and key == 'verify':
                    value = section.getboolean(key)
                config_file_values[section.name + '_' + key] = value

        LOG.info('Loaded configuration from {}'.format(parsed_file))

    config_args = []
    for k, v in config_file_values.items():
        if k == 'lxd_verify':
            if v:
                config_args.append('--lxd-verify')
        else:
            config_args.append('--{}={}'.format(k.replace('_', '-'), v))

    args = config_args + args

    def seconds(n: str) -> timedelta:
        td = timedelta(seconds=int(n))
        if td <= timedelta(0):
            raise ValueError
        return td

    def positive(n: str) -> int:
        n = int(n)
        if n <= 0:
            raise ValueError
        return n

    def comma_list(n: str) -> List[str]:
        return n.split(',')

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--runner-endpoint',
        help='piper-core server url (example: https://yourserver:4040)',
        metavar='URL'
    )
    parser.add_argument(
        '--lxd-profiles',
        help='List of LXC profiles separated by comma (see `lxc profile` shell command)',
        type=comma_list,
        metavar='A,B,...',
    )
    parser.add_argument(
        '--lxd-endpoint',
        help='LXD server url',
        default='https://127.0.0.1:8443',
        metavar='URL',
    )
    parser.add_argument(
        '--lxd-key',
        help='Path to client\'s key trusted by LXD server',
        type=Path,
        required=True,
        metavar='PATH',
    )
    parser.add_argument(
        '--lxd-cert',
        help='Path to client\'s certificate trusted by LXD server',
        type=Path,
        required=True,
        metavar='PATH',
    )
    parser.add_argument(
        '--lxd-verify',
        help='Verify client\'s cert',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--runner-interval',
        help='Wait for x seconds before making next request to piper-core',
        type=seconds,
        default=timedelta(seconds=2),
        metavar='SECONDS'
    )
    parser.add_argument(
        '--runner-token',
        help='Runner\'s secret token',
        required=True,
        metavar='TOKEN',
    )
    parser.add_argument(
        '--runner-instances',
        help='Number of concurrent Job executors',
        type=positive,
        default=1,
        metavar='INT',
    )
    parser.add_argument(
        '--runner-repository-dir',
        help='Base directory where remote repositories (GIT) are cloned',
        required=True,
        type=Path,
        metavar='PATH',
    )

    args = vars(parser.parse_args(args))

    return args


def main() -> None:
    args = parse_args(sys.argv[1:])
    LOG.debug('---- CONFIG BEGIN ----')
    for key, value in args.items():
        LOG.debug('{} = {}'.format(key, value))
    LOG.debug('---- CONFIG END ----')

    runners = list()
    try:
        for i in range(args['runner_instances']):
            r = Runner(**args)
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
