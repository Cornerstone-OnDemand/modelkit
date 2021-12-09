#!/bin/bash

set -ux

if [[ $OS_NAME == "ubuntu-latest" ]]; then
    export ENABLE_TF_SERVING_TEST=True
    export ENABLE_TF_TEST=True
    export ENABLE_REDIS_TEST=True
    export ENABLE_S3_TEST=True
    export ENABLE_GCS_TEST=True
    export ENABLE_AZ_TEST=True
    nox --error-on-missing-interpreters -s "coverage-${PYTHON_VERSION}"
else
    nox --error-on-missing-interpreters -s "test-${PYTHON_VERSION}"
fi
