#!/bin/bash

black modelkit tests bin --check
isort modelkit tests bin --check-only
flake8 modelkit tests bin 
mypy modelkit bin

