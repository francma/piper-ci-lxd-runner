import uuid
import pylxd
import requests
import logging
import os

from time import sleep

from piper_lxd.websocket_handler import WebSocketHandler
from piper_lxd.async_command import AsyncCommand
from piper_lxd.job import Job


class Runner:

    def __init__(
            self,
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
                # FIXME report
                sleep(self._runner_interval)
                continue

            if type(job['commands']) is not list:
                # FIXME report
                sleep(self._runner_interval)
                continue

            if 'config' not in job:
                # FIXME report
                sleep(self._runner_interval)
                continue

            if type(job['config']) is not dict:
                # FIXME report
                sleep(self._runner_interval)
                continue

            if 'image' not in job['config']:
                # FIXME report
                sleep(self._runner_interval)
                continue

            commands = job['commands']
            env = job['config']['env'] if 'env' in job['config'] else {}
            image = job['config']['image']

            _job = Job(
                commands=commands,
                secret=secret,
                env=env,
                image=image
            )

            self._execute(_job)

    def _execute(self, job: Job):
        # prepare container
        container_name = 'PIPER' + uuid.uuid4().hex
        container_config = {
            'name': container_name,
            'profiles': self.lxd_profiles,
            'source': job.lxd_source,
        }
        container = self._client.containers.create(container_config, wait=True)
        container.start(wait=True)

        # execute script
        handler = WebSocketHandler(self.ws_base_url, self.ws_write_resource(job.secret))
        command = AsyncCommand(container, ['/bin/ash', '-c', job.script], job.env, handler, handler).wait()
        handler.close(command.return_code)

        # delete container
        container.stop(wait=True)
        container.delete()

    @property
    def ws_base_url(self):
        return '{}://{}'.format('wss' if self._driver_secure else 'ws', self._driver_endpoint)

    @property
    def base_url(self):
        return '{}://{}'.format('https' if self._driver_secure else 'http', self._driver_endpoint)

    @property
    def fetch_job_url(self):
        return '{}/job/pop/{}'.format(self.base_url, self._runner_token)

    def fail_job_url(self, secret):
        return '{}/job/fail/{}'.format(self.base_url, secret)

    def ws_write_url(self, secret):
        return '{}{}'.format(self.ws_base_url, self.ws_write_resource(secret))

    def ws_write_resource(self, secret):
        return '/job/write?secret={}'.format(secret)

    @property
    def lxd_profiles(self):
        return self._lxd_profiles