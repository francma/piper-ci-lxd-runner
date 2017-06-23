import logging
import multiprocessing
from datetime import timedelta
from pathlib import Path
from functools import wraps
import tempfile

import pylxd
import pylxd.exceptions
import requests

from piper_lxd.models.script import Script, ScriptStatus
from piper_lxd.models.connection import Connection
from piper_lxd.models.config import LxdConfig
from piper_lxd.models import git
from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus
from piper_lxd.models.exceptions import *


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

    return wrapped


class Executor(multiprocessing.Process):

    def __init__(self, connection: Connection, interval: timedelta, lxd_config: LxdConfig, job: Job) -> None:
        cert = (str(lxd_config.cert.expanduser()), str(lxd_config.key.expanduser()))
        self._client = pylxd.Client(cert=cert, endpoint=lxd_config.endpoint, verify=lxd_config.verify)
        self._lxd_config = lxd_config
        self._job = job
        self._interval = interval
        self._connection = connection
        super().__init__()

    @_catch
    def run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            git.clone(self._job.origin, self._job.branch, self._job.commit, td)

            with Script(self._job, td, self._client, self._lxd_config.profiles) as script:
                status = None
                while script.status is ScriptStatus.RUNNING:
                    script.poll(self._interval)
                    output = script.pop_output()
                    status = self._report_status(RequestJobStatus.RUNNING, output)
                    if status is not ResponseJobStatus.OK:
                        LOG.info('Job(secret = {}) received status = {}, stopping'.format(self._job.secret, status))
                        break
                script_status = script.status
                output = script.pop_output()

        if status is ResponseJobStatus.OK:
            if script_status is ScriptStatus.ERROR:
                self._report_status(RequestJobStatus.ERROR)
            elif script_status is ScriptStatus.COMPLETED:
                self._report_status(RequestJobStatus.COMPLETED, output)

    def _report_status(self, status: RequestJobStatus, data=None) -> ResponseJobStatus:
        response = self._connection.report(self._job.secret, status, data)

        return response

