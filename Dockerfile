# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

FROM debian:stable

SHELL ["/bin/bash", "-c"]

RUN apt-get update --fix-missing
RUN apt-get install --yes git kmod make openssh-client openssh-server python3 python3-venv usbip usbutils sq curl pcscd pkg-config nettle-dev libpcsclite-dev clang sqv

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rustup.sh
RUN sh rustup.sh -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN cargo install openpgp-card-tools --locked

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
