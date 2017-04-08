#!/usr/bin/env python3
import configparser
import uuid
import pylxd
import requests
import logging
import click
import os

from typing import List
from time import sleep

from piper_lxd.websocket_handler import WebSocketHandler
from piper_lxd.async_command import AsyncCommand


COMMAND_START = 'printf "::piper_lxd-ci:command:{}:start:%d::\n" `date +%s`'
COMMAND_END = 'd3d8972793203a4505634f7c3607b4e3697862a=$?; printf "::piper_lxd-ci:command:{}:end:%d:%d::\n" `date +%s` $d3d8972793203a4505634f7c3607b4e3697862a; if [[ $d3d8972793203a4505634f7c3607b4e3697862a != 0 ]]; then exit $d3d8972793203a4505634f7c3607b4e3697862a; fi'
DEFAULT_INTERVAL = 2


def create_script(commands: List[str]) -> str:
    """
    command1
    command2
    --->
    ::PIPER:command:1:start:time()::
    `command1`
    ::PIPER:command:1:end:time()::
    ::PIPER:command:2:start:time()::
    `command2`
    ::PIPER:command:2:end:time():return_code::


    :param commands:
    :return:
    """

    script = []
    for idx, command in enumerate(commands):
        script.append(COMMAND_START.format(idx))
        script.append(command)
        script.append(COMMAND_END.format(idx))

    return '\n'.join(script)


def execute(client: pylxd.Client, secret, commands, ws, source, config={}, profiles=[]):
    # prepare container
    container_name = 'PIPER' + uuid.uuid4().hex
    container_config = {
        'name': container_name,
        'profiles': profiles,
        'source': source,
    }
    container = client.containers.create(container_config, wait=True)
    container.start(wait=True)

    env = config['env'] if 'env' in config else {}

    # execute script
    script = create_script(commands)
    handler = WebSocketHandler(ws, '/build/write?secret={}'.format(secret))
    command = AsyncCommand(container, ['/bin/ash', '-c', script], env, handler, handler).wait()
    handler.close(command.return_code)

    # delete container
    container.stop(wait=True)
    container.delete()


def delete_all_containers(client):
    for x in client.containers.all():
        try:
            x.stop(wait=True)
        except Exception as e:
            pass
        x.delete()


def ws_url(server, secure):
    return '{}://{}'.format('wss' if secure else 'ws', server)


def server_url(server, secure):
    return '{}://{}'.format('https' if secure else 'http', server)


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
    '--config',
    help='Configuration file',
)
def run(
        runner_token,
        runner_interval,
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

    _run(
        runner_token=runner_token,
        driver_url=driver_url,
        lxd_profiles=lxd_profiles,
        runner_interval=runner_interval,
        driver_secure=driver_secure,
        lxd_endpoint=lxd_endpoint,
        lxd_cert=lxd_cert,
        lxd_key=lxd_key,
        lxd_verify=lxd_verify
    )


def _run(
        runner_token: str,
        driver_url: str,
        driver_secure=False,
        lxd_profiles=[],
        runner_interval=2,
        lxd_key=None,
        lxd_endpoint=None,
        lxd_cert=None,
        lxd_verify=False
):
    """
    Runner's main execution loop.
    
    :param runner_token: Runner's secret token used to identification 
    :param driver_url: Driver server without protocol definition (example: server.com)
    :param driver_secure: Set to true for HTTPs and WSS
    :param lxd_profiles: List of LXC profiles (see `lxc profile` shell command)
    :param runner_interval: Wait for x seconds before making next request to server after empty response (no job)  
    :return: 
    """
    cert = (os.path.expanduser(lxd_cert), os.path.expanduser(lxd_key)) if lxd_key and lxd_cert else None
    client = pylxd.Client(cert=cert, endpoint=lxd_endpoint, verify=lxd_verify)

    # define endpoint URLs
    ws = ws_url(driver_url, driver_secure)
    driver_url = server_url(driver_url, driver_secure)
    fetch_job = '{}/build/pop/{}'.format(driver_url, runner_token)

    while True:
        try:
            response = requests.get(fetch_job)
        except requests.exceptions.ConnectionError:
            logging.warning('Job fetch from {} failed. Connection error.'.format(driver_url))
            sleep(runner_interval)
            continue

        # empty response means no job available
        if not response.content or response.status_code != 200:
            sleep(runner_interval)
            continue

        job = response.json()
        commands = job['commands']
        secret = job['secret']
        config = job['config'] if 'config' in job else {}

        if job['config']['image'].startswith('fingerprint:'):
            source = {
                'type': 'image',
                'fingerprint': job['config']['image'][len('fingerprint:'):]
            }
        else:
            source = {
                'type': 'image',
                'alias': job['config']['image']
            }

        execute(
            client=client,
            secret=secret,
            commands=commands,
            config=config,
            ws=ws,
            profiles=lxd_profiles,
            source=source,
        )

if __name__ == '__main__':
    run()
