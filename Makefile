# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

TAG := nitrokey-3-tests
DOCKER ?= docker
VENV ?= venv

.PHONY: all
all: check run-docker

.PHONY: check
check: venv
	"$(VENV)"/bin/flake8 *.py
	"$(VENV)"/bin/mypy --strict conftest.py
	"$(VENV)"/bin/reuse lint

.PHONY: run
run: $(VENV) usbip-runner
	. "$(VENV)"/bin/activate ; pytest --color yes --log-level debug $(PYTEST_FLAGS)

.PHONY: build-docker
build-docker:
	$(DOCKER) build . --tag $(TAG) --quiet

.PHONY: run-docker
run-docker: build-docker
	$(DOCKER) run --privileged --interactive --rm \
		--volume "$(PWD):/app" \
		--env PYTEST_FLAGS \
		$(TAG) make run

$(VENV):
	python3 -m venv "$(VENV)"
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt

.PHONY: update-venv
update-venv: $(VENV)
	"$(VENV)"/bin/pip install --requirement requirements.txt
	"$(VENV)"/bin/pip install --requirement dev-requirements.txt

usbip-runner:
	$(error missing usbip-runner: copy the binary from nitrokey-3-firmware)
