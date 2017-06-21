from time import sleep
from enum import Enum
from io import StringIO
import uuid
import logging
from typing import List
from datetime import timedelta
from pathlib import Path

import pylxd
import pylxd.exceptions
from ws4py.client import WebSocketBaseClient
from ws4py.manager import WebSocketManager
import ws4py.messaging

from piper_lxd.models.job import Job


class BufferHandler:

    def __init__(self):
        self._mem = StringIO()

    def on_message(self, data: str) -> None:
        self._mem.write(data)

    def on_close(self) -> None:
        self._mem.close()

    def pop(self) -> str:
        data = self._mem.getvalue()
        self._mem.truncate(0)
        self._mem.seek(0)
        return data


class ScriptStatus(Enum):
    CREATED = 'CREATED'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


class Script:

    POLL_TIMEOUT = timedelta(milliseconds=100)

    class NullWebSocket(WebSocketBaseClient):

        def handshake_ok(self):
            self.close()

    class WebSocket(WebSocketBaseClient):
        def __init__(self, manager: WebSocketManager, handler: BufferHandler, *args, **kwargs) -> None:
            self.manager = manager
            self.handler = handler
            super(Script.WebSocket, self).__init__(*args, **kwargs)

        def handshake_ok(self) -> None:
            self.manager.add(self)

        def received_message(self, message: ws4py.messaging.TextMessage) -> None:
            if len(message.data) == 0:
                self.close()
                self.manager.remove(self)

            if message.encoding:
                decoded = message.data.decode(message.encoding)
            else:
                decoded = message.data.decode('utf-8')

            self.handler.on_message(decoded)

    def __init__(self, job: Job, repository_path: Path, lxd_client: pylxd.Client, lxd_profiles: List[str]) -> None:
        self._job = job
        self._lxd_client = lxd_client
        self._status = ScriptStatus.CREATED
        self._repository_path = repository_path
        self._lxd_profiles = lxd_profiles

    def __enter__(self):
        self._container = None
        container_name = 'piper' + uuid.uuid4().hex
        container_config = {
            'name': container_name,
            'profiles': self._lxd_profiles,
            'source': self._job.lxd_source,
            'devices': {
                'piper_repository': {
                    'type': 'disk',
                    'path': '/piper',
                    'source': str(self._repository_path),
                }
            }
        }

        self._container = self._lxd_client.containers.create(container_config, wait=True)
        self._container.start(wait=True)
        env = {k: str(v) for k, v in self._job.env.items()}
        config = {
            'command': ['/bin/ash', '-c', self._job.script],
            'wait-for-websocket': True,
            'interactive': False,
            'environment': env,
        }
        response = self._lxd_client.api.containers[container_name].exec.post(json=config)

        fds = response.json()['metadata']['metadata']['fds']
        self.operation_id = response.json()['operation'].split('/')[-1]

        websocket_url = '/1.0/operations/{}/websocket'.format(self.operation_id)
        stdin_url = '{}?secret={}'.format(websocket_url, fds['0'])
        stdout_url = '{}?secret={}'.format(websocket_url, fds['1'])
        stderr_url = '{}?secret={}'.format(websocket_url, fds['2'])

        stdin = self.NullWebSocket(self._lxd_client.websocket_url)
        stdin.resource = stdin_url
        stdin.connect()

        self.manager = WebSocketManager()
        self.manager.start()

        self._handler = BufferHandler()
        stdout = self.WebSocket(self.manager, self._handler, self._lxd_client.websocket_url)
        stdout.resource = stdout_url
        stdout.connect()

        stderr = self.WebSocket(self.manager, self._handler, self._lxd_client.websocket_url)
        stderr.resource = stderr_url
        stderr.connect()
        self._status = ScriptStatus.RUNNING

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._container is not None:
            try:
                self._container.stop(wait=True)
            except pylxd.exceptions.LXDAPIException as e:
                logging.warning(e)

            self._container.delete()

    def poll(self, timeout: timedelta=None) -> None:
        if timeout is None:
            while len(self.manager.websockets.values()) > 0:
                sleep(self.POLL_TIMEOUT.total_seconds())

            self._status = ScriptStatus.COMPLETED
            return

        while timeout > timedelta(0):
            if len(self.manager.websockets.values()) == 0:
                self._status = ScriptStatus.COMPLETED
                return

            if timeout > self.POLL_TIMEOUT:
                sleep(self.POLL_TIMEOUT.total_seconds())
            else:
                sleep(timeout.total_seconds())

            timeout -= self.POLL_TIMEOUT

        if len(self.manager.websockets.values()) == 0:
            self._status = ScriptStatus.COMPLETED
            return

        self._status = ScriptStatus.RUNNING

    @property
    def status(self) -> ScriptStatus:
        return self._status

    def pop_output(self) -> str:
        return self._handler.pop()
