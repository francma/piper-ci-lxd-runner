#!/usr/bin/env python3
import flask
from flask_uwsgi_websocket import WebSocket
import os
import portalocker
import tempfile
import json

app = flask.Flask(__name__)
ws = WebSocket(app)

GLOBAL_SECRET = 'SECRET'
BUILD_LOG_FOLDER = os.path.join(tempfile.gettempdir(), os.environ['PIPER_TEST_KEY'], 'job')


class SocketHandler:

    def __init__(self, socket):
        self.socket = socket
        self.listeners = []

    def receive(self):
        while True:
            data = self.socket.receive()
            if data is not None:
                for listener in self.listeners:
                    listener.on_message(data.decode('utf-8'))
            else:
                for listener in self.listeners:
                    listener.on_close()
                return

    def add_listener(self, listener):
        self.listeners.append(listener)


class FileListener:

    def __init__(self, path):
        self.path = path
        self.fd = open(path, 'w')

    def on_message(self, data):
        self.fd.write(data)
        self.fd.flush()

    def on_close(self):
        self.fd.close()
        open(self.path + '-completed', 'w').close()


class Queue:

    QUEUE_FILE = os.path.join(tempfile.gettempdir(), os.environ['PIPER_TEST_KEY'], 'queue')

    @staticmethod
    def pop():
        with portalocker.Lock(Queue.QUEUE_FILE, timeout=5, mode='r+') as fp:
            lines = fp.readlines()
            if not lines:
                return None

            fp.write(os.linesep.join(lines[1:]))
            line = lines[0]
            with open('jobs/{}.json'.format(line)) as job_fp:
                j = json.loads(job_fp.read())
                j['secret'] = line
                return j


@app.route('/job/pop/<token>', methods=['GET'])
def pop_build(token):
    if not token:
        flask.abort(404)

    job = Queue.pop()
    if job is None:
        return ''

    return flask.jsonify(job)


@ws.route('/job/write')
def write_build(socket):
    with app.request_context(socket.environ):
        args = flask.request.args
        secret = args['secret'] if args['secret'] else None

    if not secret:
        socket.close('invalid secret')

    handler = SocketHandler(socket)
    file_listener = FileListener(os.path.join(BUILD_LOG_FOLDER, str(secret)))
    handler.add_listener(file_listener)
    handler.receive()


@app.route('/job/error/<secret>', methods=['POST'])
def build_fail(secret):
    path = os.path.join(BUILD_LOG_FOLDER, str(secret))
    with open(path, 'w') as fd:
        js = flask.request.get_json()
        fd.write(js['reason'])
    open(path + '-failed', 'w').close()
