# PIPER CI LXD Runner

[![Build Status](https://travis-ci.org/francma/piper-ci-lxd-runner.svg?branch=master)](https://travis-ci.org/francma/piper-ci-lxd-runner)
[![Coverage Status](https://coveralls.io/repos/github/francma/piper-ci-lxd-runner/badge.svg?branch=dev)](https://coveralls.io/github/francma/piper-ci-lxd-runner?branch=master)

Runner for [piper-ci-core](https://github.com/francma/piper-ci-driver) using Linux kernel containment features.

## Table of contents

- [Requirements](#requirements-non-pipy)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running](#running)
- [Developer guide](#developer-guide)

## Requirements (non-pipy)

- [lxd](https://github.com/lxc/lxd)
- Python >= 3.5
- git >= 2.3.0
- ssh

## Installation

1. [Install project dependencies (non-pipy)](#requirements-non-pipy)

2. Install project from github

    `pip install git+https://github.com/francma/piper-ci-lxd-runner.git`
    
3. Make sure LXD is properly configured 

    1. LXD needs to be set to listen on HTTPs (if you did not enabled this during `lxd init`)
    
        `lxc config set core.https_address [::]`
    
    2. Generate certificate and key and make them trusted by LXD
    
        ```
        openssl genrsa 2048 > client.key
        openssl req -new -x509 -nodes -sha1 -days 365 -key client.key -out client.crt -subj "/C=CZ/ST=Czech Republic/L=Prague/O=TEST/OU=IT Department/CN=example.com"
        lxc config trust add client.crt
        mkdir ~/.config/lxc-client
        mv client.* ~/.config/lxc-client/.
        ```
        
    3. Download some images to be used by LXD
    
        `lxc image copy images:alpine/3.5 local: --copy-aliases`

## Configuration

1. Copy example configuration

    `cp config.example.yml config.yml`

2. Edit your config to fit your needs

    `vim /config.example.yml`

## Running

`piper-lxd [path to your config file]`

## Developer guide

### Setup Python environment

1. Install Python virtual environment (via pip or your distribution package manager)

   `pip3 install virtualenv virtualenvwrapper`

2. Create new virtual environment named `piper-lxd`

   `mkvirtualenv piper-lxd`
   
3. [Install project](#installation)

4. Install dev dependencies

   `pip install -e ".[dev]"`
   
5. Deactivate virtualenv

    `deactivate`
    
6. Activate virtualenv

    `workon piper-lxd`

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
