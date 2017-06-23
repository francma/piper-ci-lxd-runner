import logging
import multiprocessing
from datetime import timedelta
from functools import wraps
import tempfile
from pathlib import Path

import pylxd
import pylxd.exceptions
import requests

from piper_lxd.models.script import Script
from piper_lxd.models.connection import Connection
from piper_lxd.models.config import LxdConfig
from piper_lxd.models import git
from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus
from piper_lxd.models.exceptions import StopException, CloneException


LOG = logging.getLogger('piper-lxd')


def _catch(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        self = args[0]
        try:
            func(*args, **kwargs)
        except requests.RequestException:
            LOG.warning('Failed to report status')
        except pylxd.exceptions.LXDAPIException as e:
            self._report_status(self._job.secret, RequestJobStatus.ERROR)
            LOG.error(str(e))
        except CloneException:
            self._report_status(self._job.secret, RequestJobStatus.ERROR)
        except StopException:
            LOG.debug('Received status != ResponseJobStatus.OK from PiperCore, stopping container')

    return wrapped


class Executor(multiprocessing.Process):

    def __init__(self, connection: Connection, interval: timedelta, lxd_config: LxdConfig, job: Job, **kwargs) -> None:
        cert = (str(lxd_config.cert.expanduser()), str(lxd_config.key.expanduser()))
        self._client = pylxd.Client(cert=cert, endpoint=lxd_config.endpoint, verify=lxd_config.verify)
        self._lxd_config = lxd_config
        self._job = job
        self._interval = interval
        self._connection = connection
        super().__init__(**kwargs)

    @_catch
    def run(self) -> None:
        self._report_status(RequestJobStatus.RUNNING)

        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            git.clone(self._job.origin, self._job.branch, self._job.commit, path)

            with Script(self._job, path, self._client, self._lxd_config.profiles) as script:
                while script.status == 103:  # running
                    output = script.poll(self._interval)
                    self._report_status(RequestJobStatus.RUNNING, output)
                output = script.poll(self._interval)

                if script.status == 200:  # success
                    self._report_status(RequestJobStatus.COMPLETED, output)
                else:
                    self._report_status(RequestJobStatus.ERROR)

    def _report_status(self, status: RequestJobStatus, data=None) -> ResponseJobStatus:
        response = self._connection.report(self._job.secret, status, data)
        if response is not ResponseJobStatus.OK:
            raise StopException

        return response
