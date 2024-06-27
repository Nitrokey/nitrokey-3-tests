# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

TAG := nitrokey-3-tests
DOCKER ?= docker
VENV ?= venv

# put UUIDs which shall be allowed for testing into
# ALLOWED_UUIDS inside 'variables.mk'
# (seperate them by whitespace)
-include variables.mk

.PHONY: all
all: check run-docker

.PHONY: check
check: venv
	"$(VENV)"/bin/flake8 *.py **/*.py
	"$(VENV)"/bin/mypy --strict conftest.py utils
	"$(VENV)"/bin/reuse lint

.PHONY: run
run: export PYNK_DEBUG=10
run: $(VENV)
	. "$(VENV)"/bin/activate ; pytest --color yes --log-level debug $(PYTEST_FLAGS)

.PHONY: build-docker
build-docker:
	$(DOCKER) build . --tag $(TAG) --quiet

.PHONY: run-docker
run-docker: build-docker
	$(DOCKER) run --privileged --interactive --rm \
		--volume /dev:/dev \
		--volume "$(PWD):/app" \
		--env RUST_LOG \
		--env PYTEST_FLAGS \
		$(TAG) make run

.PHONY: run-hw run-hw-report
run-hw: build-docker
	$(MAKE) run-docker PYTEST_FLAGS="--use-usb-devices $(ALLOWED_UUIDS) -m 'not virtual' $(PYTEST_EXTRA)"

run-hw-report:
	$(MAKE) run-hw PYTEST_EXTRA="--template=html1/index.html --report report.html --junitxml=report-junit.xml"

run-extra-secrets-tests:
	$(MAKE) run-docker PYTEST_FLAGS="-v tests/extra/secrets_app_tests.py --durations=0  -m 'not slow' -o log_cli=false -o log_cli_level=debug -W ignore::DeprecationWarning --template=html1/index.html --report report-secrets.html --junitxml=report-junit-secrets.xml"

run-extra-secrets-tests-slow:
	$(MAKE) run-docker PYTEST_FLAGS="-v tests/extra/secrets_app_tests.py --durations=0 -o log_cli=false -o log_cli_level=debug -W ignore::DeprecationWarning --template=html1/index.html --report report-secrets-full.html --junitxml=report-junit-secrets-full.xml"

$(VENV):
	python3 -m venv "$(VENV)"
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt

.PHONY: update-venv
update-venv: $(VENV)
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt
