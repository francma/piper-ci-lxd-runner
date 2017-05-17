from ws4py.client import WebSocketBaseClient
from ws4py.manager import WebSocketManager
from time import sleep
from enum import Enum
from collections import deque


class BufferHandler:

    def __init__(self):
        self._mem = deque()

    @property
    def path(self):
        return self._path

    def on_message(self, data):
        self._mem.append(data)

    def on_close(self):
        del self._mem

    def pop(self):
        return ''.join(self._mem)


class ScriptStatus(Enum):
    CREATED = 0
    RUNNING = 1
    COMPLETED = 2
    ERROR = 3


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

    def __init__(self, container, commands, env):
        self.client = container.client
        self.completed_operation = None
        self._status = ScriptStatus.CREATED

        response = self.client.api.containers[container.name].exec.post(json={
            'command': commands,
            'wait-for-websocket': True,
            'interactive': False,
            'environment': env,
        })

        fds = response.json()['metadata']['metadata']['fds']
        self.operation_id = response.json()['operation'].split('/')[-1]

        websocket_url = '/1.0/operations/{}/websocket'.format(self.operation_id)

        stdin_url = '{}?secret={}'.format(websocket_url, fds['0'])
        stdout_url = '{}?secret={}'.format(websocket_url, fds['1'])
        stderr_url = '{}?secret={}'.format(websocket_url, fds['2'])

        stdin = self.NullWebSocket(self.client.websocket_url)
        stdin.resource = stdin_url
        stdin.connect()

        self.manager = WebSocketManager()
        self.manager.start()

        self._handler = BufferHandler()

        stdout = self.WebSocket(self.manager, self._handler, self.client.websocket_url)
        stdout.resource = stdout_url
        stdout.connect()

        stderr = self.WebSocket(self.manager, self._handler, self.client.websocket_url)
        stderr.resource = stderr_url
        stderr.connect()

    @property
    def return_code(self):
        if len(self.manager.websockets.values()) > 0:
            return None

        if self.completed_operation is None:
            self.completed_operation = self.client.operations.get(self.operation_id)

        return self.completed_operation.metadata['return']

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
