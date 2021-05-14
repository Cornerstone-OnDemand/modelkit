#!/bin/bash

if [[ $JOB_NAME == "ubuntu-latest" ]]; then
    ENABLE_TF_SERVING=True
    ENABLE_REDIS=True
    ENABLE_S3=True
fi

nox -s test