# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

FROM debian:stable

RUN apt-get update && apt-get install --yes curl git gnupg kmod make openssh-client openssh-server python3 python3-venv usbip usbutils

# Install bazel for CTAP2-test-tool
RUN curl -fsSL https://bazel.build/bazel-release.pub.gpg | gpg --dearmor > bazel.gpg
RUN mv bazel.gpg /etc/apt/trusted.gpg.d/
RUN echo "deb [arch=amd64] https://storage.googleapis.com/bazel-apt stable jdk1.8" | tee /etc/apt/sources.list.d/bazel.list
RUN apt-get update && apt-get install --yes bazel libudev-dev autotools-dev autoconf automake libtool g++

RUN useradd --create-home --user-group user

ENV VENV=/venv
COPY requirements.txt .
COPY dev-requirements.txt .

RUN python3 -m venv /venv
RUN /venv/bin/pip install --upgrade pip --progress-bar off
RUN /venv/bin/pip install --requirement requirements.txt --progress-bar off
RUN /venv/bin/pip install --requirement dev-requirements.txt --progress-bar off
RUN /venv/bin/pip install --force "oscrypto @ git+https://github.com/wbond/oscrypto.git@1547f535001ba568b239b8797465536759c742a3" --progress-bar off

COPY entrypoint /

WORKDIR /app
ENTRYPOINT ["/entrypoint"]
CMD []
