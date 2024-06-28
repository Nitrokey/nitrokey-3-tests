# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

TAG := nitrokey-3-tests
DOCKER ?= docker
VENV ?= venv

NK_MODEL ?= nk3
TEST_SUITE ?= basic

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
	. "$(VENV)"/bin/activate ; pytest --color yes --log-level debug $(PYTEST_FLAGS) --model $(NK_MODEL) --test-suite $(TEST_SUITE)

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
		--env NK_MODEL \
		--env TEST_SUITE \
		$(TAG) make run

.PHONY: run-hw run-hw-report
run-hw: build-docker
	$(MAKE) run-docker PYTEST_FLAGS="--use-usb-devices $(ALLOWED_UUIDS) --model $(NK_MODEL) --test-suite $(TEST_SUITE) $(PYTEST_EXTRA)"

run-hw-report:
	$(MAKE) run-hw PYTEST_EXTRA="--template=html1/index.html --report report.html --junitxml=report-junit.xml $(PYTEST_EXTRA)"

$(VENV):
	python3 -m venv "$(VENV)"
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt

.PHONY: update-venv
update-venv: $(VENV)
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt
