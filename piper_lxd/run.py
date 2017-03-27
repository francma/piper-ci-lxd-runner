import configparser
import uuid
import pylxd
import requests

from typing import List
from time import sleep

from piper_lxd import WebSocketHandler
from piper_lxd import AsyncCommand


def run():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    config = configparser.ConfigParser()
    config.read('piper_lxd/config.ini')

    RUNNER_TOKEN = config['runner']['token']
    DRIVER_URL = config['driver']['url']
    PROFILES = config['lxd']['profiles'].split(',')
    INTERVAL = int(config['runner']['interval'])

    run(token=RUNNER_TOKEN, server=DRIVER_URL, profiles=PROFILES, interval=INTERVAL)


COMMAND_START = 'printf "::piper_lxd-ci:command:{}:start:%d::\n" `date +%s`'
COMMAND_END = 'printf "::piper_lxd-ci:command:{}:end:%d::\n" `date +%s`'


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
    ::PIPER:command:2:end:time()::


    :param commands:
    :return:
    """

    script = []
    for idx, command in enumerate(commands):
        script.append(COMMAND_START.format(idx))
        script.append(command)
        script.append(COMMAND_END.format(idx))

    return '\n'.join(script)


def execute(client, job, ws, profiles):
    secret = job['secret']
    commands = job['commands']

    # prepare container
    container_name = 'PIPER' + uuid.uuid4().hex
    config = {
        'name': container_name,
        'profiles': profiles,
        'source': {
            'type': 'image',
            'fingerprint': '4612ea3efef3'
        },
    }
    container = client.containers.create(config, wait=True)
    container.start(wait=True)

    # execute script
    script = create_script(commands)
    handler = WebSocketHandler(ws, 'write-build?secret={}'.format(secret))
    command = AsyncCommand(container, ['/bin/ash', '-c', script], None, handler, handler).wait()
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


def _run(token, server, secure=False, profiles=[], interval=2):
    client = pylxd.Client()

    # define endpoint URLs
    ws = ws_url(server, secure)
    server = server_url(server, secure)
    fetch_job = '{}/{}/{}'.format(server, 'pop-build', token)

    while True:
        try:
            response = requests.get(fetch_job)
        except requests.exceptions.ConnectionError:
            print('CONNECTION ERROR!')
            sleep(interval)
            continue

        # empty response means no job available
        if not response.content or response.status_code != 200:
            sleep(interval)
            continue

        job = response.json()
        execute(client, job, ws, profiles)

        sleep(interval)