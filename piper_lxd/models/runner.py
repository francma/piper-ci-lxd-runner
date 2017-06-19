import logging
import os
import time
import multiprocessing

import pylxd
import pylxd.exceptions
import requests

from piper_lxd.models.script import Script, ScriptStatus
from piper_lxd.models import git
from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus
from piper_lxd.models.exceptions import *


LOG = logging.getLogger(__name__)


class Runner(multiprocessing.Process):

    def __init__(
            self,
            runner_repository_dir: str,
            runner_token: str,
            driver_endpoint: str,
            lxd_profiles=None,
            runner_interval=2,
            lxd_key=None,
            lxd_endpoint=None,
            lxd_cert=None,
            lxd_verify=False
    ):
        super().__init__()
        cert = (os.path.expanduser(lxd_cert), os.path.expanduser(lxd_key)) if lxd_key and lxd_cert else None
        self._client = pylxd.Client(cert=cert, endpoint=lxd_endpoint, verify=lxd_verify)
        self._driver_endpoint = driver_endpoint
        self._runner_token = runner_token
        self._lxd_profiles = lxd_profiles if type(lxd_profiles) is list else []
        self._runner_token = runner_token
        self._runner_interval = runner_interval
        self._runner_repository_dir = runner_repository_dir

    def run(self):
        while True:
            data = self._fetch_job()
            if not data:
                time.sleep(self._runner_interval)
                continue

            try:
                try:
                    job = Job(data)
                except JobException as e:
                    self._report_status(e.secret, RequestJobStatus.ERROR)
                    time.sleep(self._runner_interval)
                    continue

                clone_dir = os.path.join(self._runner_repository_dir, job.secret)
                os.makedirs(clone_dir)

                try:
                    git.clone(job.origin, job.branch, job.commit, clone_dir)
                except CloneException:
                    self._report_status(job.secret, RequestJobStatus.ERROR)
                    time.sleep(self._runner_interval)
                    continue

                with Script(job, clone_dir, self._client, self._lxd_profiles) as script:
                    status = None
                    while script.status is ScriptStatus.RUNNING:
                        script.poll(3000)
                        output = script.pop_output()
                        status = self._report_status(job.secret, RequestJobStatus.RUNNING, output)
                        if status is not ResponseJobStatus.OK:
                            LOG.info('Job(secret = {}) received status = {}, stopping'.format(job.secret, status))
                            break
                    script_status = script.status
                    output = script.pop_output()

                if status is ResponseJobStatus.OK:
                    if script_status is ScriptStatus.ERROR:
                        self._report_status(job.secret, RequestJobStatus.ERROR)
                    elif script_status is ScriptStatus.COMPLETED:
                        self._report_status(job.secret, RequestJobStatus.COMPLETED, output)
            except ReportStatusFail:
                LOG.warning('Giving up reporting status to {} '.format(self.driver_endpoint))

    def _fetch_job(self):
        try:
            response = requests.get(self.fetch_job_url)
        except requests.exceptions.ConnectionError:
            LOG.warning('Job fetch from {} failed. Connection error.'.format(self.driver_endpoint))
            return None

        if not response.content:
            LOG.debug('No job available from {}.'.format(self.driver_endpoint))
            return None

        return response.json()

    def _report_status(self, secret: str, status: ScriptStatus, data=None) -> ResponseJobStatus:
        url = self.job_status_url(secret, status)
        for x in range(8):
            try:
                LOG.debug('Reporting status %s to %s' % status, url)
                response = requests.post(url, headers={'content-type': 'text/plain'}, data=data)
                break
            except requests.RequestException as e:
                LOG.warning('Report status to {} failed. Error: {}'.format(self.driver_endpoint, e))
                if x != 8:
                    time.sleep(1)
                else:
                    raise ReportStatusFail

        js = response.json()

        return ResponseJobStatus[js['status']]

    @property
    def driver_endpoint(self):
        return self._driver_endpoint

    @property
    def fetch_job_url(self):
        return '{}/jobs/queue/{}'.format(self.driver_endpoint, self._runner_token)

    def job_status_url(self, secret: str, status: ScriptStatus):
        return '{}/jobs/report/{}?status={}'.format(self.driver_endpoint, secret, status.value)
