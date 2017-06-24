# PIPER CI LXD Runner

[![Build Status](https://travis-ci.org/francma/piper-ci-lxd-runner.svg?branch=master)](https://travis-ci.org/francma/piper-ci-lxd-runner)
[![Coverage Status](https://coveralls.io/repos/github/francma/piper-ci-lxd-runner/badge.svg?branch=dev)](https://coveralls.io/github/francma/piper-ci-lxd-runner?branch=master)

Runner for [piper-ci-core](https://github.com/francma/piper-ci-driver) using Linux kernel containment features.

## Requirements (non-pipy)

- [lxd](https://github.com/lxc/lxd)
- Python >= 3.5

## Installation

Installation from GIT:
`pip install git+https://github.com/francma/piper-ci-lxd-runner.git`

## Configuration

see `/config.example.yml` and `/piper_lxd/schemas/config.py`