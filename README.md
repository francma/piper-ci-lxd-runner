# PIPER CI LXD Runner

[![Build Status](https://travis-ci.org/francma/piper-ci-lxd-runner.svg?branch=master)](https://travis-ci.org/francma/piper-ci-lxd-runner)
[![Coverage Status](https://coveralls.io/repos/github/francma/piper-ci-lxd-runner/badge.svg?branch=dev)](https://coveralls.io/github/francma/piper-ci-lxd-runner?branch=master)

Runner for [piper-ci-core](https://github.com/francma/piper-ci-driver) using Linux kernel containment features.

## Requirements (non-pipy)

- [lxd](https://github.com/lxc/lxd)
- Python >= 3.5
- git >= 2.3.0
- ssh

## Installation

`pip install git+https://github.com/francma/piper-ci-lxd-runner.git`

## Configuration

see `/config.example.yml` and `/piper_lxd/schemas/config.py`

## Developer guide

### Setup Python environment

1. Install Python virtual environment

   `pip3 install virtualenv virtualenvwrapper`

2. Clone repository

   `git clone https://github.com/francma/piper-ci-lxd-runner.git`

3. Change working directory into project

   `cd piper-ci-lxd-runner`

4. Create new virtual environment named `piper-lxd`

   `mkvirtualenv piper-lxd`

5. Install dependencies

   `pip install -e ".[dev]"`

### Setup LXD

1. Run LXD initialization

   `lxd init`

2. Configure `piper-ci` LXD profile

   `profile copy default piper-ci`

   `...`

3. Setup authentication

   `openssl genrsa 2048 > client.key`

   `openssl req -new -x509 -nodes -sha1 -days 365 -key client.key -out client.crt -subj "/C=CZ/ST=Czech Republic/L=Prague/O=TEST/OU=IT Department/CN=example.com`

   `lxc config trust add client.crt`

4. Move keys

   `mkdir -p ~/.config/lxc-client`

   `mv client.* ~/.config/lxc-client/.`

### Tests

Run tests in `tests/` directory:

`pytest` or `tox -e py`

Check PEP8:

`flake8` or `tox -e pep8`

Check types:

`mypy piper_lxd/run.py` or `tox -e mypy`

Run for specific python version:

`tox -e py35-mypy` or `tox -e py36`

Run all:

`tox`
