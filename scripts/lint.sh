#!/usr/bin/env bash

set -e
set -x

black modelkit tests bin --check
isort modelkit tests bin --check-only
flake8 modelkit tests bin 
mypy modelkit bin

