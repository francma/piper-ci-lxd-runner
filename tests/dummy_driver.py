#!/usr/bin/env python3
import flask
from flask_uwsgi_websocket import GeventWebSocket
from flask_uwsgi_websocket import GeventWebSocketClient
import os
import portalocker
import tempfile
import json

app = flask.Flask(__name__)
ws = GeventWebSocket(app)

GLOBAL_SECRET = 'SECRET'
BUILD_LOG_FOLDER = os.path.join(tempfile.gettempdir(), os.environ['PIPER_TEST_KEY'], 'job')


class Listener:

    def on_message(self, data: str):
        raise NotImplementedError


class FileListener(Listener):

    def __init__(self, path: str):
        self.path = path
        self.fd = open(path, 'w')

    def on_message(self, data: str):
        self.fd.write(data)
        self.fd.flush()


class SocketHandler:

    def __init__(self, socket: GeventWebSocketClient):
        self.socket = socket
        self.listeners = []

    def receive(self):
        while True:
            data = self.socket.receive()
            # socket was closed
            if data is None:
                return
            # timeout
            if len(data) == 0:
                continue

            for listener in self.listeners:
                listener.send(data.decode('utf-8'))

    def add_listener(self, listener: Listener):
        self.listeners.append(listener)


def status_file_path(secret: str):
    return os.path.join(BUILD_LOG_FOLDER, secret + '-status')


def log_file_path(secret: str):
    return os.path.join(BUILD_LOG_FOLDER, secret)


class Queue:

    QUEUE_FILE = os.path.join(tempfile.gettempdir(), os.environ['PIPER_TEST_KEY'], 'queue')

    @staticmethod
    def pop():
        with portalocker.Lock(Queue.QUEUE_FILE, timeout=5, mode='r+') as fp:
            lines = fp.readlines()
            lines = [x for x in lines if x.strip()]
            if not lines:
                return None

            fp.seek(0)
            fp.write(os.linesep.join(lines[1:]))
            fp.truncate()

            line = lines[0].strip()
            with open('jobs/{}.json'.format(line)) as job_fp:
                j = json.loads(job_fp.read())
                j['secret'] = line
                return j


@app.route('/job/pop/<token>', methods=['GET'])
def pop_build(token: str):
    if not token:
        flask.abort(400)

    job = Queue.pop()
    if job is None:
        return ''

    return flask.jsonify(job)


@ws.route('/job/write')
def write_build(socket: GeventWebSocketClient):
    with app.request_context(socket.environ):
        args = flask.request.args
        secret = args['secret'] if args['secret'] else None

    if not secret:
        socket.close()

    handler = SocketHandler(socket)
    file_listener = FileListener(log_file_path(secret))
    handler.add_listener(file_listener)
    handler.receive()


@app.route('/job/status/<secret>', methods=['PUT'])
def update_build_status(secret: str):
    with open(status_file_path(secret), 'w') as fd:
        js = flask.request.get_json()
        print(js['status'], file=fd)

    return flask.make_response('', 200)
