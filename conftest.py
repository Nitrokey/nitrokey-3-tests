# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import logging
import os
from abc import ABC, abstractmethod
from fido2.hid import open_device
from pytest import FixtureRequest, Parser, fixture
from typing import Generator, List, Optional


logger = logging.getLogger(__name__)


class Device(ABC):
    @property
    @abstractmethod
    def hidraw(self) -> str:
        pass

    @property
    @abstractmethod
    def serial(self) -> str:
        pass


class UsbDevice(Device):
    def __init__(self, hidraw: str, serial: str) -> None:
        self._hidraw = hidraw
        self._serial = serial

    @property
    def hidraw(self) -> str:
        return self._hidraw

    @property
    def serial(self) -> str:
        return self._serial

    @staticmethod
    def find(serial: str) -> "UsbDevice":
        devices = find_devices(0x20a0, 0x42b2)
        if len(devices) > 1:
            raise RuntimeError(f"{len(devices)} devices connected: {devices}")
        device = devices[0]
        device_serial = get_serial(device)
        if int(serial, 16) != int(device_serial, 16):
            raise RuntimeError(
                f"Expected device with serial {serial}, found {device_serial}"
            )
        return UsbDevice(device, device_serial)


def find_hidraw_device(path: str, subdirs: List[str]) -> Optional[str]:
    for subdir in subdirs:
        for root, dirs, files in os.walk(os.path.join(path, subdir)):
            if "device" not in dirs:
                continue
            subsystem = os.path.basename(os.path.dirname(root))
            if subsystem == "hidraw":
                return os.path.basename(root)
    return None


def find_devices(vid: int, pid: int) -> List[str]:
    devices = []
    for root, dirs, files in os.walk("/sys/devices"):
        if "dev" not in files:
            continue
        subdirs = dirs
        del dirs
        if "idVendor" not in files:
            continue
        if "idProduct" not in files:
            continue
        with open(os.path.join(root, "idVendor")) as f:
            current_vid = int(f.read(), 16)
        with open(os.path.join(root, "idProduct")) as f:
            current_pid = int(f.read(), 16)

        if current_vid == vid and current_pid == pid:
            device = find_hidraw_device(root, subdirs)
            if device:
                logger.debug(
                    f"found USB device: vid={current_vid:04x}, "
                    f"pid={current_pid:04x}, device={device}"
                )
                devices.append(device)
    return devices


def get_serial(device: str) -> str:
    ctaphid_device = open_device(f"/dev/{device}")
    serial = ctaphid_device.call(0x62)
    return serial.hex().upper()


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--use-usb-device", action="store",
    )


@fixture(scope="module")
def device(request: FixtureRequest) -> Generator[Device, None, None]:
    serial = request.config.getoption("--use-usb-device")
    if serial:
        yield UsbDevice.find(serial)
    else:
        raise RuntimeError("usbip not supported yet")
