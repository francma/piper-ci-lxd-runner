from wsgiref.simple_server import make_server
from threading import Thread, Lock

import pytest
import json

from piper_lxd.models.connection import Connection
from piper_lxd.models.job import RequestJobStatus, ResponseJobStatus
from piper_lxd.models.errors import PConnectionInvalidResponseError, PConnectionRequestError


def response_error(env, start_response):
    start_response('500 Internal Server Error', [])

    return []


def response_empty(env, start_response):
    start_response('204 No Content', [])

    return []


def response_invalid_http_code(env, start_response):
    start_response('201 Created', [])

    return []


def response_not_json(env, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    return [b'Hello']


def response_invalid_status(env, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    return [b'{"status": "INVALID STATUS"}']


def response_valid_job(env, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    with open('tests/jobs/ok.json', mode='rb') as fp:
        return [fp.read()]


def response_valid_status(env, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    return [json.dumps({'status': ResponseJobStatus.OK.value}).encode()]


def server(responses, lock):
    httpd = make_server('', 9999, lambda x, y: responses.pop(0)(x, y))
    lock.release()
    while len(responses):
        httpd.handle_request()


def test_one():
    lock = Lock()
    lock.acquire()

    responses = [
        response_empty,
        response_invalid_http_code,
        response_invalid_http_code,
        response_not_json,
        response_not_json,
        response_error,
        response_error,
        response_invalid_status,
        response_valid_status,
        response_valid_status,
        response_valid_job,
    ]

    th = Thread(target=server, args=(responses, lock))
    th.start()
    lock.acquire()

    connection = Connection('http://localhost:9999')

    # empty response
    job = connection.fetch_job('token')
    assert job is None

    # invalid http status
    with pytest.raises(PConnectionRequestError):
        connection.report('secret', RequestJobStatus.RUNNING)

    # invalid http status
    with pytest.raises(PConnectionRequestError):
        connection.fetch_job('token')

    # response not json
    with pytest.raises(PConnectionInvalidResponseError):
        connection.report('secret', RequestJobStatus.RUNNING)

    # response not json
    with pytest.raises(PConnectionInvalidResponseError):
        connection.fetch_job('token')

    # response error
    with pytest.raises(PConnectionRequestError):
        connection.fetch_job('token')

    # response error
    with pytest.raises(PConnectionRequestError):
        connection.report('secret', RequestJobStatus.RUNNING)

    # status unknown
    with pytest.raises(PConnectionInvalidResponseError):
        connection.report('secret', RequestJobStatus.RUNNING)

    # valid status
    connection.report('secret', RequestJobStatus.RUNNING)
    connection.report('secret', RequestJobStatus.RUNNING, 'LOG LOG LOG')

    # valid job
    connection.fetch_job('token')

    th.join()
