#!/usr/bin/env bash

set -e
set -x

black modelkit tests bin
isort modelkit tests bin
