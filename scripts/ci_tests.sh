#!/bin/bash

if [[ $OS_NAME == "ubuntu-latest" ]]; then
    ENABLE_TF_SERVING_TEST=True
    ENABLE_REDIS_TEST=True
    ENABLE_S3_TEST=True
fi

nox -s test