import logging
from typing import Optional

import requests

from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus

LOG = logging.getLogger('piper-lxd')


class Connection:

    def __init__(self, core_base_url: str) -> None:
        self._core_base_url = core_base_url

    def fetch_job(self, token: str) -> Optional[Job]:
        url = self.fetch_job_url(token)
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            LOG.warning('Job fetch from {} failed. Connection error.'.format(url))
            return None

        if not response.content:
            return None

        job = Job(response.json())

        return job

    def report(self, secret: str, status: RequestJobStatus, log: Optional[str]=None) -> ResponseJobStatus:
        url = self.report_url(secret, status)
        LOG.debug('Reporting status {} to {}'.format(status, url))
        response = requests.post(url, headers={'content-type': 'text/plain'}, data=log)  # type: ignore
        js = response.json()

        return ResponseJobStatus[js['status']]

    @property
    def core_base_url(self) -> str:
        return self._core_base_url

    def fetch_job_url(self, token: str) -> str:
        return '{}/jobs/queue/{}'.format(self.core_base_url, token)

    def report_url(self, secret: str, status: RequestJobStatus) -> str:
        return '{}/jobs/report/{}?status={}'.format(self.core_base_url, secret, status.value)
