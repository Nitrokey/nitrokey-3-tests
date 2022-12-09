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
	"$(VENV)"/bin/mypy --strict *.py
	"$(VENV)"/bin/reuse lint

.PHONY: run
run: $(VENV) usbip-runner
	"$(VENV)"/bin/pytest --color yes

.PHONY: build-docker
build-docker:
	$(DOCKER) build . --tag $(TAG) --quiet

.PHONY: run-docker
run-docker: build-docker
	$(DOCKER) run --interactive --rm --volume "$(PWD):/app" $(TAG) make run

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
