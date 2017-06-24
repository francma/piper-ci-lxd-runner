# PIPER CI LXD Runner

[![Build Status](https://travis-ci.org/francma/piper-ci-lxd-runner.svg?branch=master)](https://travis-ci.org/francma/piper-ci-lxd-runner)

Runner for [piper-ci-core](https://github.com/francma/piper-ci-driver) using Linux kernel containment features.

## Requirements (non-pipy)

- [lxd](https://github.com/lxc/lxd)
- Python >= 3.5

## Installation

Installation from GIT:
`pip install git+https://github.com/francma/piper-ci-lxd-runner.git`

## Configuration

Via command line: `piper-lxc --help`

Via config file: `/config.ini.example`

Command line arguments have higher priority.