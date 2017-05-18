from ws4py.client import WebSocketBaseClient
from ws4py.manager import WebSocketManager
from time import sleep
from enum import Enum
from io import StringIO
import uuid
import logging

import pylxd
import pylxd.exceptions

from piper_lxd.models.job import Job


class BufferHandler:

    def __init__(self):
        self._mem = StringIO()

    def on_message(self, data):
        self._mem.write(data)

    def on_close(self):
        self._mem.close()

    def pop(self):
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

    POLL_TIMEOUT = 100

    class NullWebSocket(WebSocketBaseClient):

        def handshake_ok(self):
            self.close()

    class WebSocket(WebSocketBaseClient):
        def __init__(self, manager, handler, *args, **kwargs):
            self.manager = manager
            self.handler = handler
            super(Script.WebSocket, self).__init__(*args, **kwargs)

        def handshake_ok(self):
            self.manager.add(self)

        def received_message(self, message):
            if len(message.data) == 0:
                self.close()
                self.manager.remove(self)

            if message.encoding:
                decoded = message.data.decode(message.encoding)
            else:
                decoded = message.data.decode('utf-8')

            self.handler.on_message(decoded)

    def __init__(self, job: Job, cwd: str, client: pylxd.Client, profiles):
        self._job = job
        self._client = client
        self._status = ScriptStatus.CREATED
        self._cwd = cwd
        self._profiles = profiles

    def __enter__(self):
        self._container = None
        container_name = 'piper' + uuid.uuid4().hex
        container_config = {
            'name': container_name,
            'profiles': self._profiles,
            'source': self._job.lxd_source,
            'devices': {
                'piper_repository': {
                    'type': 'disk',
                    'path': '/piper',
                    'source': self._cwd,
                }
            }
        }

        self._container = self._client.containers.create(container_config, wait=True)
        self._container.start(wait=True)
        response = self._client.api.containers[container_name].exec.post(json={
            'command': ['/bin/ash', '-c', self._job.script],
            'wait-for-websocket': True,
            'interactive': False,
            'environment': self._job.env,
        })

        fds = response.json()['metadata']['metadata']['fds']
        self.operation_id = response.json()['operation'].split('/')[-1]

        websocket_url = '/1.0/operations/{}/websocket'.format(self.operation_id)
        stdin_url = '{}?secret={}'.format(websocket_url, fds['0'])
        stdout_url = '{}?secret={}'.format(websocket_url, fds['1'])
        stderr_url = '{}?secret={}'.format(websocket_url, fds['2'])

        stdin = self.NullWebSocket(self._client.websocket_url)
        stdin.resource = stdin_url
        stdin.connect()

        self.manager = WebSocketManager()
        self.manager.start()

        self._handler = BufferHandler()
        stdout = self.WebSocket(self.manager, self._handler, self._client.websocket_url)
        stdout.resource = stdout_url
        stdout.connect()

        stderr = self.WebSocket(self.manager, self._handler, self._client.websocket_url)
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

    def poll(self, timeout=None):
        if timeout is None:
            while len(self.manager.websockets.values()) > 0:
                sleep(self.POLL_TIMEOUT / 1000)

            self._status = ScriptStatus.COMPLETED
            return

        while timeout > 0:
            if len(self.manager.websockets.values()) == 0:
                self._status = ScriptStatus.COMPLETED
                return

            if timeout > self.POLL_TIMEOUT:
                sleep(self.POLL_TIMEOUT / 1000)
            else:
                sleep(timeout / 1000)

            timeout -= self.POLL_TIMEOUT

        if len(self.manager.websockets.values()) == 0:
            self._status = ScriptStatus.COMPLETED
            return

        self._status = ScriptStatus.RUNNING

    @property
    def status(self):
        return self._status

    def pop_output(self):
        return self._handler.pop()
