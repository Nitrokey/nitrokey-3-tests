# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import subprocess


def call(cmd: list[str], timeout: int = 5) -> None:
    subprocess.call(cmd, timeout=timeout)


def check_call(cmd: list[str], timeout: int = 5) -> None:
    subprocess.check_call(cmd, timeout=timeout)


def check_output(cmd: list[str], timeout: int = 5, *args, **kwargs) -> str:
    print(cmd)
    r = subprocess.check_output(cmd, encoding="utf-8", timeout=timeout, *args, **kwargs)
    print(r)
    return r
