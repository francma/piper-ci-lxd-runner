import uuid
import pylxd
import pylxd.exceptions
import requests
import logging
import os
from enum import Enum
from time import sleep
from datetime import timedelta

from piper_lxd.websocket_handler import WebSocketHandler
from piper_lxd.async_command import AsyncCommand
from piper_lxd.job import Job
from piper_lxd.models.git import *


class JobStatus(Enum):
    COMPLETED = 'COMPLETED'
    RUNNING = 'RUNNING'
    STARTED = 'STARTED'
    ERROR_NO_COMMANDS = 'ERROR_NO_COMMANDS'
    ERROR_COMMANDS_NOT_LIST = 'ERROR_COMMANDS_NOT_LIST'
    ERROR_CONFIG_MISSING = 'ERROR_CONFIG_MISSING'
    ERROR_CONFIG_NOT_DICT = 'ERROR_CONFIG_NOT_DICT'
    ERROR_NO_IMAGE = 'ERROR_NO_IMAGE'
    ERROR_IMAGE_NOT_STR = 'ERROR_IMAGE_NOT_STR'
    ERROR_AFTER_FAILURE_NOT_LIST = 'ERROR_AFTER_FAILURE_NOT_LIST'
    ERROR_IMAGE_NOT_FOUND = 'ERROR_IMAGE_NOT_FOUND'
    ERROR_REPOSITORY_NOT_FOUND = 'ERROR_REPOSITORY_NOT_FOUND'
    ERROR_REPOSITORY_NOT_DICT = 'ERROR_REPOSITORY_NOT_DICT'
    ERROR_REPOSITORY_NO_ORIGIN = 'ERROR_REPOSITORY_NO_ORIGIN'
    ERROR_REPOSITORY_NO_REF = 'ERROR_REPOSITORY_NO_REF'
    ERROR_REPOSITORY_NO_ID = 'ERROR_REPOSITORY_NO_ID'
    ERROR_REPOSITORY_NO_KEY = 'ERROR_REPOSITORY_NO_KEY'
    ERROR_REPOSITORY_ORIGIN_NOT_STR = 'ERROR_REPOSITORY_ORIGIN_NOT_STR'
    ERROR_REPOSITORY_REF_NOT_STR = 'ERROR_REPOSITORY_REF_NOT_STR'
    ERROR_REPOSITORY_ID_NOT_STR = 'ERROR_REPOSITORY_ID_NOT_STR'
    ERROR_REPOSITORY_KEY_NOT_STR = 'ERROR_REPOSITORY_KEY_NOT_STR'


class PiperException(Exception):
    pass


class ImageNotFoundException(PiperException):
    pass


class Runner:

    def __init__(
            self,
            runner_repository_dir: str,
            runner_token: str,
            driver_url: str,
            driver_secure=False,
            lxd_profiles=[],
            runner_interval=2,
            lxd_key=None,
            lxd_endpoint=None,
            lxd_cert=None,
            lxd_verify=False
    ):
        cert = (os.path.expanduser(lxd_cert), os.path.expanduser(lxd_key)) if lxd_key and lxd_cert else None
        self._client = pylxd.Client(cert=cert, endpoint=lxd_endpoint, verify=lxd_verify)
        self._driver_endpoint = driver_url
        self._driver_secure = driver_secure
        self._runner_token = runner_token
        self._lxd_profiles = lxd_profiles
        self._runner_token = runner_token
        self._runner_interval = runner_interval
        self._runner_repository_dir = runner_repository_dir

    def run(self):
        while True:
            try:
                response = requests.get(self.fetch_job_url)
            except requests.exceptions.ConnectionError:
                logging.warning('Job fetch from {} failed. Connection error.'.format(self.base_url))
                sleep(self._runner_interval)
                continue

            # empty response means no job available
            if not response.content or response.status_code != 200:
                sleep(self._runner_interval)
                continue

            job = response.json()

            # without secret we can't report failed build
            if 'secret' not in job:
                sleep(self._runner_interval)
                continue
            secret = job['secret']

            if 'commands' not in job:
                self._report_status(secret, JobStatus.ERROR_NO_COMMANDS)
                sleep(self._runner_interval)
                continue

            if type(job['commands']) is not list:
                self._report_status(secret, JobStatus.ERROR_COMMANDS_NOT_LIST)
                sleep(self._runner_interval)
                continue

            if 'config' not in job:
                self._report_status(secret, JobStatus.ERROR_CONFIG_MISSING)
                sleep(self._runner_interval)
                continue

            if type(job['config']) is not dict:
                self._report_status(secret, JobStatus.ERROR_CONFIG_NOT_DICT)
                sleep(self._runner_interval)
                continue

            if 'image' not in job['config']:
                self._report_status(secret, JobStatus.ERROR_NO_IMAGE)
                sleep(self._runner_interval)
                continue

            if type(job['config']['image']) is not str:
                self._report_status(secret, JobStatus.ERROR_IMAGE_NOT_STR)
                sleep(self._runner_interval)
                continue

            if 'after_failure' in job and type(job['after_failure']) is not list:
                self._report_status(secret, JobStatus.ERROR_AFTER_FAILURE_NOT_LIST)
                sleep(self._runner_interval)
                continue

            if 'repository' not in job['config']:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_NOT_FOUND)
                sleep(self._runner_interval)
                continue

            if type(job['config']['repository']) is not dict:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_NOT_DICT)
                sleep(self._runner_interval)
                continue

            if 'origin' not in job['config']['repository']:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_NO_ORIGIN)
                sleep(self._runner_interval)
                continue

            if type(job['config']['repository']['origin']) is not str:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_ORIGIN_NOT_STR)
                sleep(self._runner_interval)
                continue

            if 'ref' not in job['config']['repository']:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_NO_REF)
                sleep(self._runner_interval)
                continue

            if type(job['config']['repository']['ref']) is not str:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_REF_NOT_STR)
                sleep(self._runner_interval)
                continue

            if 'id' not in job['config']['repository']:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_NO_ID)
                sleep(self._runner_interval)
                continue

            if type(job['config']['repository']['id']) is not str:
                self._report_status(secret, JobStatus.ERROR_REPOSITORY_ID_NOT_STR)
                sleep(self._runner_interval)
                continue

            after_failure = job['after_failure'] if 'after_failure' in job else []
            commands = job['commands']
            env = job['config']['env'] if 'env' in job['config'] else {}
            image = job['config']['image']

            repository = Repository(job['config']['repository']['origin'])
            branch = Branch(job['config']['repository']['ref'], repository)
            commit = Commit(job['config']['repository']['id'], branch)

            _job = Job(
                commands=commands,
                secret=secret,
                env=env,
                image=image,
                after_failure=after_failure,
                commit=commit,
            )

            try:
                self._execute(_job)
            except ImageNotFoundException:
                self._report_status(secret, JobStatus.ERROR_IMAGE_NOT_FOUND)

    def _execute(self, job: Job):
        # clone git repository
        destination = os.path.join(self._runner_repository_dir, job.secret)
        os.makedirs(destination)
        job.commit.clone(destination)

        # prepare container
        container_name = 'PIPER' + uuid.uuid4().hex
        container_config = {
            'name': container_name,
            'profiles': self.lxd_profiles,
            'source': job.lxd_source,
            'devices': {
                'piper_repository': {
                    'type': 'disk',
                    'path': '/piper_repository',
                    'source': destination,
                }
            }
        }

        try:
            container = self._client.containers.create(container_config, wait=True)
        except pylxd.exceptions.LXDAPIException as e:
            # FIXME
            raise ImageNotFoundException

        container.start(wait=True)

        # execute script
        handler = WebSocketHandler(self.ws_base_url, self.ws_write_resource(job.secret))
        command = AsyncCommand(container, ['/bin/ash', '-c', 'cd /piper_repository; sleep 3; ' + job.script], job.env, handler, handler)
        while not command.wait(3 * 1000):
            self._report_status(secret=job.secret, status=JobStatus.RUNNING)
        self._report_status(secret=job.secret, status=JobStatus.COMPLETED)
        handler.close()

        # delete container
        container.stop(wait=True)
        container.delete()

    def _report_status(self, secret: str, status: JobStatus):
        js = {
            'status': status.value,
        }
        requests.put(self.job_status_url(secret), json=js)

    @property
    def ws_base_url(self):
        return '{}://{}'.format('wss' if self._driver_secure else 'ws', self._driver_endpoint)

    @property
    def base_url(self):
        return '{}://{}'.format('https' if self._driver_secure else 'http', self._driver_endpoint)

    @property
    def fetch_job_url(self):
        return '{}/job/pop/{}'.format(self.base_url, self._runner_token)

    def job_status_url(self, secret):
        return '{}/job/status/{}'.format(self.base_url, secret)

    def ws_write_url(self, secret):
        return '{}{}'.format(self.ws_base_url, self.ws_write_resource(secret))

    def ws_write_resource(self, secret):
        return '/job/write?secret={}'.format(secret)

    @property
    def lxd_profiles(self):
        return self._lxd_profiles