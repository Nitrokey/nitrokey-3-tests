# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import logging
import os
import os.path
import random
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from fido2.hid import open_device
from pexpect import spawn
from subprocess import Popen
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Generator, List, Optional
from .subprocess import check_call, check_output


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

    @property
    @abstractmethod
    def pin(self) -> Optional[str]:
        pass

    @abstractmethod
    def set_pin(self, pin: str) -> None:
        pass


@dataclass
class UsbipState:
    ifs: str
    serial: str
    pin: Optional[str] = None


class UsbipDevice(Device):
    def __init__(self, hidraw: str, state: UsbipState, runner: Popen[bytes]):
        self._hidraw = hidraw
        self._state = state
        self._runner = runner

    @property
    def hidraw(self) -> str:
        return self._hidraw

    @property
    def serial(self) -> str:
        return self._state.serial

    @property
    def pin(self) -> Optional[str]:
        return self._state.pin

    def set_pin(self, pin: str) -> None:
        set_pin(self._state.pin, pin)
        self._state.pin = pin

    def __enter__(self) -> "UsbipDevice":
        return self

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        if self._runner:
            self._runner.terminate()

    def provision(self) -> None:
        logger.debug("Provisioning usbip-runner")
        check_call(
            [
                "nitropy",
                "nk3",
                "provision",
                "fido2",
                "--cert",
                "data/fido.cert",
                "--key",
                "data/fido.key",
            ],
        )

    @staticmethod
    def spawn(binary: str, state: UsbipState) -> "UsbipDevice":
        mods = check_output(["lsmod"])
        mod_lines = mods.splitlines()
        if not any([line.startswith("vhci_hcd") for line in mod_lines]):
            raise RuntimeError(
                "vhci-hcd kernel module missing -- please run "
                "`modprobe vhci-hcd`"
            )

        env = os.environ.copy()
        if "RUST_LOG" not in env:
            env["RUST_LOG"] = "info"
        runner = Popen(
            [binary, "--ifs", state.ifs, "--serial", "0x" + state.serial],
            env=env,
        )
        logger.debug(
            f"{binary} spawned: pid={runner.pid}, ifs={state.ifs}, "
            f"serial={state.serial})"
        )

        host = "localhost"
        check_call(["usbip", "list", "-r", host])
        check_call(["usbip", "attach", "-r", host, "-b", "1-1"])
        check_call(["usbip", "attach", "-r", host, "-b", "1-1"])

        for i in range(5):
            if not find_devices(0x20a0, 0x42b2):
                time.sleep(1)
            else:
                break
        hidraw = find_device(0x20a0, 0x42b2)

        for i in range(5):
            if not os.path.exists(f"/dev/{hidraw}"):
                time.sleep(1)
            else:
                break
        if not os.path.exists(f"/dev/{hidraw}"):
            raise RuntimeError(f"hidraw device {hidraw} does not show up")

        return UsbipDevice(hidraw, state, runner)


device_pin: Optional[str] = None


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

    @property
    def pin(self) -> Optional[str]:
        global device_pin
        return device_pin

    def set_pin(self, pin: str) -> None:
        global device_pin
        set_pin(device_pin, pin)
        device_pin = pin

    @staticmethod
    def find(serial: str) -> "UsbDevice":
        device = find_device(0x20a0, 0x42b2)
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


def find_device(vid: int, pid: int) -> str:
    devices = find_devices(vid, pid)
    if not devices:
        raise RuntimeError("no matching device found")
    if len(devices) > 1:
        raise RuntimeError(f"{len(devices)} devices connected: {devices}")
    return devices[0]


def get_serial(device: str) -> str:
    ctaphid_device = open_device(f"/dev/{device}")
    serial = ctaphid_device.call(0x62)
    return serial.hex().upper()


def generate_serial() -> str:
    return random.randbytes(16).hex().upper()


def set_pin(old_pin: Optional[str], new_pin: str) -> None:
    if old_pin:
        p = spawn("nitropy fido2 change-pin")
        p.expect("enter old pin")
        p.sendline(old_pin)
    else:
        p = spawn("nitropy fido2 set-pin")
    p.expect("enter new pin")
    p.sendline(new_pin)
    p.expect("confirm new pin")
    p.sendline(new_pin)
    p.expect("done")


@contextmanager
def spawn_device(
    ifs: str,
    serial: Optional[str] = None,
    provision: bool = True,
    suffix: Optional[str] = None,
) -> Generator[Device, None, None]:
    runner = "usbip-runner"
    provisioner = "usbip-provisioner"
    if suffix:
        runner += "-" + suffix
        provisioner += "-" + suffix

    bin_dir = "./bin"
    runner_binary = os.path.join(bin_dir, runner)
    provisioner_binary = os.path.join(bin_dir, provisioner)
    if not os.path.exists(runner_binary):
        raise RuntimeError(f"{runner} binary is missing")
    if provision and not os.path.exists(provisioner_binary):
        raise RuntimeError(f"{provisioner} binary is missing")

    if not serial:
        serial = generate_serial()

    state = UsbipState(ifs=ifs, serial=serial)
    if provision:
        with UsbipDevice.spawn(provisioner_binary, state) as device:
            device.provision()
    with UsbipDevice.spawn(runner_binary, state) as device:
        yield device


@contextmanager
def state_dir(keep_state: bool) -> Generator[str, None, None]:
    if keep_state:
        if not os.path.exists("./state"):
            os.mkdir("./state")
        yield mkdtemp(dir="./state")
    else:
        with TemporaryDirectory() as d:
            yield d
