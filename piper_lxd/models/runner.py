import logging
import os
import uuid
from enum import Enum
from time import sleep
from contextlib import contextmanager

import pylxd
import pylxd.exceptions
import requests

from piper_lxd.models.script import Script, ScriptStatus
from piper_lxd.models import git
from piper_lxd.models.job import Job
from piper_lxd.models.exceptions import *


class Status(Enum):
    COMPLETED = 'COMPLETED'
    RUNNING = 'RUNNING'
    ERROR = 'ERROR'


class Runner:

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
                continue

            try:
                job = Job(data)
            except JobException as e:
                self._report_status(e.secret, Status.ERROR)
                continue

            clone_dir = os.path.join(self._runner_repository_dir, job.secret)
            os.makedirs(clone_dir)

            try:
                git.clone(job.origin, job.branch, job.commit, clone_dir)
            except CloneException:
                self._report_status(job.secret, Status.ERROR)
                continue

            with self._execute(job, clone_dir) as script:
                while script.status is ScriptStatus.RUNNING:
                    script.poll(3000)
                    output = script.pop_output()
                    self._report_status(job.secret, Status.RUNNING, output)

                script.poll()
                output = script.pop_output()
                self._report_status(job.secret, Status.COMPLETED, output)

    def _fetch_job(self):
        try:
            response = requests.get(self.fetch_job_url)
        except requests.exceptions.ConnectionError:
            logging.warning('Job fetch from {} failed. Connection error.'.format(self.driver_endpoint))
            return None

        if not response.content:
            logging.debug('No job available from {}.'.format(self.driver_endpoint))
            return None

        return response.json()

    @contextmanager
    def _execute(self, job: Job, clone_dir):
        container = None
        container_name = 'piper' + uuid.uuid4().hex
        container_config = {
            'name': container_name,
            'profiles': self._lxd_profiles,
            'source': job.lxd_source,
            'devices': {
                'piper_repository': {
                    'type': 'disk',
                    'path': '/piper',
                    'source': clone_dir,
                }
            }
        }

        container = self._client.containers.create(container_config, wait=True)
        container.start(wait=True)
        command = Script(container, ['/bin/ash', '-c', job.script], job.env)
        yield command

        if container is not None:
            try:
                container.stop(wait=True)
            except pylxd.exceptions.LXDAPIException as e:
                logging.warning(e)

            container.delete()

    def _report_status(self, secret: str, status: Status, data=None):
        url = self.job_status_url(secret, status)
        requests.post(url, headers={'content-type': 'text/plain'}, data=data)

    @property
    def driver_endpoint(self):
        return self._driver_endpoint

    @property
    def fetch_job_url(self):
        return '{}/job-queue/{}'.format(self.driver_endpoint, self._runner_token)

    def job_status_url(self, secret: str, status: Status):
        return '{}/job-status/{}?status={}'.format(self.driver_endpoint, secret, status)
