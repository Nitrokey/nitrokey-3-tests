# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import logging
import os
import os.path
from pytest import Config, FixtureRequest, Parser, fixture
from typing import Generator
from utils.device import (
    Device, UsbDevice, generate_serial, state_dir, spawn_device
)
from utils.subprocess import check_output


logger = logging.getLogger(__name__)


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--keep-state", action="store_true",
    )
    parser.addoption(
        "--upgrade", action="store_true",
    )
    parser.addoption(
        "--use-usb-device", action="store",
    )


def pytest_report_header(config: Config) -> str:
    def get_version(binary: str) -> str:
        path = os.path.join("bin", binary)
        if os.path.exists(path):
            version = "v" + check_output([path, "--version"]).split()[1]
        else:
            version = "[missing]"
        return version

    runner_version = get_version("usbip-runner")
    provisioner_version = get_version("usbip-provisioner")
    if runner_version == provisioner_version:
        version = runner_version
    else:
        version = f"{runner_version}/{provisioner_version}"
    header = f"usbip-runner: {version}"

    if config.getoption("--upgrade"):
        runner_version = get_version("usbip-runner")
        provisioner_version = get_version("usbip-provisioner")
        if runner_version == provisioner_version:
            version = runner_version
        else:
            version = f"{runner_version}/{provisioner_version}"
        header += f" (old: {version})"

    return header


@fixture(scope="module")
def device(request: FixtureRequest) -> Generator[Device, None, None]:
    serial = request.config.getoption("--use-usb-device")
    if serial:
        yield UsbDevice.find(serial)
    else:
        keep_state = request.config.getoption("--keep-state")
        with state_dir(keep_state) as s:
            ifs = os.path.join(s, "ifs.bin")
            with spawn_device(ifs) as device:
                yield device


@fixture
def ifs(request: FixtureRequest) -> Generator[str, None, None]:
    keep_state = request.config.getoption("--keep-state")
    with state_dir(keep_state) as s:
        yield os.path.join(s, "ifs.bin")


@fixture
def serial() -> str:
    return generate_serial()
