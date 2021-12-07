#!/bin/bash
set -e

if [[ $1 == apply ]] ; then
    black modelkit tests bin 
    isort modelkit tests bin 
fi

black modelkit tests bin --check
isort modelkit tests bin --check-only
flake8 modelkit tests bin 
mypy modelkit bin

