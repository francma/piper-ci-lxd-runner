#!/usr/bin/env python3
import configparser
import logging

import click

from piper_lxd.models.runner import Runner

DEFAULT_INTERVAL = 2


@click.command()
@click.option(
    '--driver-url',
    help='Driver server without protocol definition (example: server.com)',
)
@click.option(
    '--driver-secure',
    help='FIXME',
    type=click.BOOL,
    is_flag=True,
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
)
@click.option(
    '--lxd-key',
    help='Client\'s key trusted by LXD server',
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
    '--runner-repository-dir',
    help='Base directory where remote repositories (GIT) are cloned',
)
@click.option(
    '--config',
    help='Configuration file',
)
def run(
    runner_token,
    runner_interval,
    runner_repository_dir,
    driver_url,
    driver_secure,
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
        logging.info('Loaded configuration from {}'.format(parsed_file))

    if not runner_token:
        try:
            runner_token = config_file['runner']['token']
        except KeyError:
            logging.fatal('Empty runner token, exiting...')
            exit(1)

    if not runner_repository_dir:
        try:
            runner_repository_dir = config_file['runner']['repository_dir']
        except KeyError:
            logging.fatal('No repository base directory set, exiting...')
            exit(1)

    if not driver_url:
        try:
            driver_url = config_file['driver']['url']
        except KeyError:
            logging.fatal('Driver endpoint not set, exiting...')
            exit(1)

    if driver_secure is None:
        try:
            driver_secure = config_file['driver'].getboolean('secure')
        except KeyError:
            driver_secure = False

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
            runner_interval = int(config_file['runner']['interval'])
        except KeyError:
            runner_interval = DEFAULT_INTERVAL

    runner = Runner(
        runner_token=runner_token,
        runner_repository_dir=runner_repository_dir,
        driver_url=driver_url,
        lxd_profiles=lxd_profiles,
        runner_interval=runner_interval,
        driver_secure=driver_secure,
        lxd_endpoint=lxd_endpoint,
        lxd_cert=lxd_cert,
        lxd_key=lxd_key,
        lxd_verify=lxd_verify
    )

    runner.run()


if __name__ == '__main__':
    run()
