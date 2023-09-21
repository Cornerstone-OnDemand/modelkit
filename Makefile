SHELL := /bin/bash
.SHELLFLAGS := -e -x -c -o pipefail
.PHONY: setup setup_lint lint tests coverage ci_tests requirements upgrade

setup_lint:
	pip install --upgrade pip pre-commit
	pre-commit install

lint:
	pre-commit run --all-files

tests:
	export ENABLE_TF_SERVING_TEST=True; \
	export ENABLE_TF_TEST=True; \
	export ENABLE_REDIS_TEST=True; \
	export ENABLE_S3_TEST=True; \
	export ENABLE_GCS_TEST=True; \
	export ENABLE_AZ_TEST=True; \
	pytest

coverage:
	export ENABLE_TF_SERVING_TEST=True; \
	export ENABLE_TF_TEST=True; \
	export ENABLE_REDIS_TEST=True; \
	export ENABLE_S3_TEST=True; \
	export ENABLE_GCS_TEST=True; \
	export ENABLE_AZ_TEST=True; \
	coverage run -m pytest; \
	coverage report -m; \
	coverage xml

setup:
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pip install -e .[lint,tensorflow,cli,api,assets-s3,assets-gcs,assets-az]
	pre-commit install

ci_tests:
	pip install --upgrade pip nox
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

upgrade:
	pip install --upgrade pip pip-tools pre-commit
	pre-commit autoupdate
	pip-compile --upgrade --extra=dev --output-file=requirements-dev.txt
	pip install -r requirements-dev.txt
