# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

TAG := nitrokey-3-tests
DOCKER ?= docker
VENV ?= venv

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
