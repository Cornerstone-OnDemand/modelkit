SHELL := /bin/bash
.SHELLFLAGS := -e -x -c -o pipefail
.PHONY: setup_lint lint setup_tests tests ci-tests setup_ci_tests requirements upgrade

setup_lint:
	pip install --upgrade pip pre-commit
	pre-commit install

lint: setup_lint
	pre-commit run --all-files

setup_tests:
	pip install --upgrade pip
	pip install -r requirements-dev.txt

tests: setup_tests
	coverage run -m pytest
	coverage report -m
	coverage xml

setup_ci_tests:
	pip install --upgrade pip nox

ci-tests: setup_ci_tests
	@if [ "$(OS_NAME)" = "ubuntu-latest" ]; then \
		export ENABLE_TF_SERVING_TEST=True; \
		export ENABLE_TF_TEST=True; \
		export ENABLE_REDIS_TEST=True; \
		export ENABLE_S3_TEST=True; \
		export ENABLE_GCS_TEST=True; \
		export ENABLE_AZ_TEST=True; \
		nox --error-on-missing-interpreters -s "coverage-$(PYTHON_VERSION)"; \
	else \
		nox --error-on-missing-interpreters -s "tests-$(PYTHON_VERSION)"; \
	fi

requirements:
	pip install --upgrade pip pip-compile
	pip-compile --extra=dev --output-file=requirements-dev.txt

upgrade: setup_lint
	pre-commit autoupdate
	pip-compile --upgrade --extra=dev --output-file=requirements-dev.txt
