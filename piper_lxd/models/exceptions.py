class PiperException(Exception):
    pass


class LxdException(PiperException):
    pass


class CloneException(PiperException):
    pass


class JobException(PiperException):

    def __init__(self, message, secret):
        super().__init__(message)
        self.secret = secret


class ReportStatusFail(PiperException):
    pass
