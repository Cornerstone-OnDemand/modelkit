#!/bin/bash
set -e

black modelkit tests bin --check
isort modelkit tests bin --check-only
flake8 modelkit tests bin 
mypy modelkit bin

