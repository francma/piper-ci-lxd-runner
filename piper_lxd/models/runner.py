import logging
import os
import time
import multiprocessing
from typing import Dict, Any, Optional, List
from datetime import timedelta
from pathlib import Path

import pylxd
import pylxd.exceptions
import requests
from pykwalify.errors import SchemaError

from piper_lxd.models.script import Script, ScriptStatus
from piper_lxd.models import git
from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus
from piper_lxd.models.exceptions import *


LOG = logging.getLogger('piper-lxd')


class Runner(multiprocessing.Process):

    def __init__(
            self,
            runner_repository_dir: Path,
            runner_token: str,
            runner_endpoint: str,
            lxd_profiles: List[str],
            runner_interval: timedelta,
            lxd_key: Path,
            lxd_endpoint: str,
            lxd_cert: Path,
            lxd_verify: bool,
            **kwargs
    ) -> None:
        cert = (str(lxd_cert.expanduser()), str(lxd_key.expanduser())) if lxd_key and lxd_cert else None
        self._client = pylxd.Client(cert=cert, endpoint=lxd_endpoint, verify=lxd_verify)
        self._driver_endpoint = runner_endpoint
        self._runner_token = runner_token
        self._lxd_profiles = lxd_profiles
        self._runner_token = runner_token
        self._runner_interval = runner_interval
        self._runner_repository_dir = runner_repository_dir
        super().__init__()

    def run(self) -> None:
        while True:
            data = self._fetch_job()
            if not data:
                time.sleep(self._runner_interval.total_seconds())
                continue

            try:
                try:
                    job = Job(data)
                except SchemaError as e:
                    LOG.error(str(e))
                    if 'secret' in job:
                        self._report_status(job['secret'], RequestJobStatus.ERROR)
                    time.sleep(self._runner_interval.total_seconds())
                    continue

                clone_dir = self._runner_repository_dir / job.secret
                clone_dir.mkdir(parents=True)

                try:
                    git.clone(job.origin, job.branch, job.commit, clone_dir)
                except CloneException:
                    self._report_status(job.secret, RequestJobStatus.ERROR)
                    time.sleep(self._runner_interval.total_seconds())
                    continue

                with Script(job, clone_dir, self._client, self._lxd_profiles) as script:
                    status = None
                    while script.status is ScriptStatus.RUNNING:
                        script.poll(self._runner_interval)
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
            except pylxd.exceptions.LXDAPIException as e:
                self._report_status(job.secret, RequestJobStatus.ERROR)
                LOG.error('LXD error: {}'.format(e))

    def _fetch_job(self) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(self.fetch_job_url)
        except requests.exceptions.ConnectionError:
            LOG.warning('Job fetch from {} failed. Connection error.'.format(self.driver_endpoint))
            return None

        if not response.content:
            LOG.debug('No job available from {}.'.format(self.driver_endpoint))
            return None

        return response.json()

    def _report_status(self, secret: str, status: RequestJobStatus, data=None) -> ResponseJobStatus:
        url = self.job_status_url(secret, status)
        for x in range(8):
            try:
                LOG.debug('Reporting status {} to {}'.format(status, url))
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
    def driver_endpoint(self) -> str:
        return self._driver_endpoint

    @property
    def fetch_job_url(self) -> str:
        return '{}/jobs/queue/{}'.format(self.driver_endpoint, self._runner_token)

    def job_status_url(self, secret: str, status: RequestJobStatus) -> str:
        return '{}/jobs/report/{}?status={}'.format(self.driver_endpoint, secret, status.value)
