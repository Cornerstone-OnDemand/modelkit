#!/bin/bash

if [[ $OS_NAME == "ubuntu-latest" ]]; then
    export ENABLE_TF_SERVING_TEST=True
    export ENABLE_REDIS_TEST=True
    export ENABLE_S3_TEST=False
fi

nox -s test