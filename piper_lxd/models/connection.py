from typing import Optional
from http import HTTPStatus
from datetime import timedelta

import requests
import requests.exceptions

from piper_lxd.models.job import Job, RequestJobStatus, ResponseJobStatus
from piper_lxd.models.errors import PConnectionRequestError, PConnectionInvalidResponseError


class Connection:

    _DEFAULT_TIMEOUT = timedelta(seconds=30)

    def __init__(self, core_base_url: str, timeout: Optional[timedelta]=None) -> None:
        self._timeout = self._DEFAULT_TIMEOUT if timeout is None else timeout
        self._core_base_url = core_base_url

    def fetch_job(self, token: str) -> Optional[Job]:
        """
        Fetches new Job from PiperCore if available, returns None otherwise.

        :raises PConnectionInvalidResponseError:
        :raises PConnectionRequestError:
        :raises pykwalify.errors.SchemaError: on invalid Job definition
        """
        url = self._fetch_job_url(token)
        try:
            response = requests.get(url, timeout=self._timeout.total_seconds())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise PConnectionRequestError(str(e))

        if not response.content:
            return None

        if response.status_code != HTTPStatus.OK:
            raise PConnectionRequestError('Expected {}, got {}.'.format(HTTPStatus.OK, response.status_code))

        try:
            js = response.json()
        except ValueError:
            raise PConnectionInvalidResponseError('Response is not valid JSON')

        job = Job(js)

        return job

    def report(self, secret: str, status: RequestJobStatus, log: Optional[str]=None) -> ResponseJobStatus:
        """
        Reports Job status to PiperCore with optional Streaming Log contents.
        Returns response status from PiperCore.

        :raises PConnectionRequestError:
        :raises PConnectionInvalidResponseError:
        """
        url = self._report_url(secret, status)
        try:
            response = requests.post(
                url,
                headers={'content-type': 'text/plain'},
                data=log.encode() if log else None,
                timeout=self._timeout.total_seconds()
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise PConnectionRequestError(e)

        if response.status_code != HTTPStatus.OK:
            raise PConnectionRequestError('Expected {}, got {}.'.format(HTTPStatus.OK, response.status_code))

        try:
            js = response.json()
        except ValueError:
            raise PConnectionInvalidResponseError('Response is not valid JSON')

        try:
            response_status = ResponseJobStatus[js['status']]
        except KeyError:
            raise PConnectionInvalidResponseError('Invalid status in JSON response')

        return response_status

    @property
    def core_base_url(self) -> str:
        return self._core_base_url

    def _fetch_job_url(self, token: str) -> str:
        return '{}/jobs/queue/{}'.format(self.core_base_url, token)

    def _report_url(self, secret: str, status: RequestJobStatus) -> str:
        return '{}/jobs/report/{}?status={}'.format(self.core_base_url, secret, status.value)
