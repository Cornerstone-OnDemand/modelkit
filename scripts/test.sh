#!/usr/bin/env bash

set -e
set -x

coverage run -m pytest
coverage report -m
coverage xml