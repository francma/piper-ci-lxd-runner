class PiperException(Exception):
    pass


class LxdException(PiperException):
    pass


class LxdContainerCreateException(LxdException):
    pass


class GitException(PiperException):
    pass


class GitCloneException(GitException):
    pass
