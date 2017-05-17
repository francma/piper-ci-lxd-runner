import json

import pytest

from piper_lxd.models.job import Job
from piper_lxd.models.exceptions import JobException


def load_dict(job_name):
    with open('tests/jobs/{}.json'.format(job_name)) as fd:
        return json.load(fd)


def test_no_commands():
    with pytest.raises(JobException):
        Job(load_dict('no_commands'))


def test_commands_not_list():
    with pytest.raises(JobException):
        Job(load_dict('commands_not_list'))


def test_no_image():
    with pytest.raises(JobException):
        Job(load_dict('no_image'))


def test_image_not_str():
    with pytest.raises(JobException):
        Job(load_dict('image_not_str'))


def test_image_not_str():
    with pytest.raises(JobException):
        Job(load_dict('image_not_str'))


def test_after_failure_not_list():
    with pytest.raises(JobException):
        Job(load_dict('after_failure_not_list'))
