class PiperException(Exception):
    pass


class LxdException(PiperException):
    pass


class CloneException(PiperException):
    pass


class JobException(PiperException):

    def __init__(self, secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret = secret


class ReportStatusFail(PiperException):
    pass
