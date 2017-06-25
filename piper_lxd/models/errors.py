import requests.exceptions


class PException(Exception):
    pass


class PCloneException(PException):
    pass


class PStopException(PException):
    pass


class PConnectionException(PException):
    pass


class PConnectionInvalidResponseError(PConnectionException):
    pass


class PConnectionRequestError(PConnectionException, requests.exceptions.RequestException):
    pass


class PScriptException(PException):
    pass
