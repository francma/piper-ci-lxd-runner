#!/usr/bin/env python3
import configparser
import logging
from datetime import timedelta

import click

from piper_lxd.models.runner import Runner

DEFAULT_INTERVAL = timedelta(seconds=2)
DEFAULT_WORKERS = 1

LOG = logging.getLogger(__name__)


@click.command()
@click.option(
    '--driver-endpoint',
    help='Driver server without protocol definition (example: server.com)',
)
@click.option(
    '--lxd-profiles',
    help='List of LXC profiles (see `lxc profile` shell command), separated by comma',
)
@click.option(
    '--lxd-endpoint',
    help='LXD server endpoint',
)
@click.option(
    '--lxd-cert',
    help='Client\'s certificate trusted by LXD server',
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    '--lxd-key',
    help='Client\'s key trusted by LXD server',
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    '--lxd-verify',
    help='Verify client\'s cert',
    type=click.BOOL,
    is_flag=True,
)
@click.option(
    '--runner-interval',
    help='Wait for x seconds before making next request to server after empty response (no job)',
    type=click.INT,
)
@click.option(
    '--runner-token',
    help='Runner\'s secret token used as identification',
)
@click.option(
    '--runner-workers',
    help='Number of worker processes',
    type=click.INT,
)
@click.option(
    '--runner-repository-dir',
    help='Base directory where remote repositories (GIT) are cloned',
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    '--config',
    help='Configuration file',
    type=click.Path(exists=True, resolve_path=True),
)
def run(
    runner_token,
    runner_interval,
    runner_repository_dir,
    runner_workers,
    driver_endpoint,
    lxd_profiles,
    lxd_key,
    lxd_cert,
    lxd_verify,
    lxd_endpoint,
    config
):
    config_file = {}
    if config:
        # load config from defined location
        config_file = configparser.ConfigParser()
        parsed_file = config_file.read(config)
        LOG.info('Loaded configuration from {}'.format(parsed_file))

    if not runner_token:
        try:
            runner_token = config_file['runner']['token']
        except KeyError:
            LOG.fatal('Empty runner token, exiting...')
            exit(1)

    if not runner_repository_dir:
        try:
            runner_repository_dir = config_file['runner']['repository_dir']
        except KeyError:
            LOG.fatal('No repository base directory set, exiting...')
            exit(1)

    if not driver_endpoint:
        try:
            driver_endpoint = config_file['driver']['url']
        except KeyError:
            LOG.fatal('Driver endpoint not set, exiting...')
            exit(1)

    if lxd_verify is None:
        try:
            lxd_verify = config_file['lxd'].getboolean('verify')
        except KeyError:
            lxd_verify = False

    if lxd_profiles:
        lxd_profiles = lxd_profiles.split(',')
    else:
        try:
            lxd_profiles = config_file['lxd']['profiles'].split(',')
        except KeyError:
            pass

    if not lxd_key:
        try:
            lxd_key = config_file['lxd']['key']
        except KeyError:
            pass

    if not lxd_cert:
        try:
            lxd_cert = config_file['lxd']['cert']
        except KeyError:
            pass

    if not lxd_endpoint:
        try:
            lxd_endpoint = config_file['lxd']['endpoint']
        except KeyError:
            pass

    if not runner_interval:
        try:
            runner_interval = timedelta(seconds=config_file['runner']['interval'])
        except KeyError:
            runner_interval = DEFAULT_INTERVAL

    if not runner_workers:
        try:
            runner_workers = int(config_file['runner']['workers'])
        except KeyError:
            runner_workers = DEFAULT_WORKERS

    LOG.debug('Config:')
    LOG.debug('  runner_token = {}'.format(runner_token))
    LOG.debug('  runner_repository_dir = {}'.format(runner_repository_dir))
    LOG.debug('  runner_interval = {}'.format(runner_interval))
    LOG.debug('  driver_endpoint = {}'.format(driver_endpoint))
    LOG.debug('  lxd_profiles = {}'.format(lxd_profiles))
    LOG.debug('  lxd_endpoint = {}'.format(lxd_endpoint))
    LOG.debug('  lxd_cert = {}'.format(lxd_cert))
    LOG.debug('  lxd_key = {}'.format(lxd_key))
    LOG.debug('  lxd_verify = {}'.format(lxd_verify))

    runners = list()
    try:
        for i in range(runner_workers):
            r = Runner(
                runner_token=runner_token,
                runner_repository_dir=runner_repository_dir,
                driver_endpoint=driver_endpoint,
                lxd_profiles=lxd_profiles,
                runner_interval=runner_interval,
                lxd_endpoint=lxd_endpoint,
                lxd_cert=lxd_cert,
                lxd_key=lxd_key,
                lxd_verify=lxd_verify
            )
            runners.append(r)
            r.start()

        for r in runners:
            r.join()
    except KeyboardInterrupt:
        for r in runners:
            LOG.info('Terminating worker(PID={})'.format(r.pid))
            r.terminate()


logging.basicConfig()
LOG.setLevel(logging.DEBUG)

LOG.info('Starting piper-lxd')

if __name__ == '__main__':
    run()
