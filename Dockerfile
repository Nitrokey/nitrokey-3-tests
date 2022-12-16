# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

FROM debian:stable

RUN apt-get update
RUN apt-get install --yes git kmod make openssh-client openssh-server python3 python3-venv usbip usbutils

RUN useradd --create-home --user-group user

ENV VENV=/venv
COPY requirements.txt .
COPY dev-requirements.txt .

RUN python3 -m venv /venv
RUN /venv/bin/pip install --upgrade pip --progress-bar off
RUN /venv/bin/pip install --requirement requirements.txt --progress-bar off
RUN /venv/bin/pip install --requirement dev-requirements.txt --progress-bar off

COPY entrypoint /

WORKDIR /app
ENTRYPOINT ["/entrypoint"]
CMD []
