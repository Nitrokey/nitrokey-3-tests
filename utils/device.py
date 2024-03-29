# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import enum
import logging
import os
import os.path
import random
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from fido2.hid import open_device
from pexpect import spawn
from signal import SIGUSR1
from subprocess import Popen
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Generator, List, Optional, Sequence
from .subprocess import check_call, check_output


logger = logging.getLogger(__name__)


VID_NITROKEY = 0x20a0
PID_NK3 = 0x42b2
PID_NKPK = 0x42f3
PIDS = [PID_NK3, PID_NKPK]


class Model(Enum):
    NK3 = enum.auto()
    NKPK = enum.auto()

    @property
    def name(self) -> str:
        if self == Model.NK3:
            return "Nitrokey 3"
        if self == Model.NKPK:
            return "Nitrokey Passkey"
        raise ValueError(f"Unsupported model: {self}")

    @property
    def command(self) -> str:
        if self == Model.NK3:
            return "nk3"
        if self == Model.NKPK:
            return "nkpk"
        raise ValueError(f"Unsupported model: {self}")

    @staticmethod
    def from_vid_pid(vid: int, pid: int) -> "Model":
        if vid == VID_NITROKEY:
            if pid == PID_NK3:
                return Model.NK3
            if pid == PID_NKPK:
                return Model.NKPK
        raise ValueError(f"Unsupported model: {vid:04x}:{pid:04x}")


@dataclass
class DeviceData:
    hidraw: str
    vid: int
    pid: int


class Device(ABC):
    def __init__(self, data: DeviceData) -> None:
        self.data = data

    @property
    def hidraw(self) -> str:
        return self.data.hidraw

    @property
    def vid(self) -> int:
        return self.data.vid

    @property
    def pid(self) -> int:
        return self.data.pid

    @property
    def model(self) -> Model:
        return Model.from_vid_pid(self.vid, self.pid)

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

    def confirm_user_presence(self) -> None:
        pass

    def reboot(self) -> None:
        pass


@dataclass
class UsbipState:
    ifs: str
    efs: str
    serial: str
    user_presence: bool
    pin: Optional[str] = None


class UsbipDevice(Device):
    def __init__(
        self,
        binary: str,
        data: DeviceData,
        state: UsbipState,
        runner: Popen[bytes],
    ):
        super().__init__(data)
        self._binary = binary
        self._state = state
        self._runner = runner

    @property
    def serial(self) -> str:
        return self._state.serial

    @property
    def pin(self) -> Optional[str]:
        return self._state.pin

    def set_pin(self, pin: str) -> None:
        set_pin(self._state.pin, pin)
        self._state.pin = pin

    def confirm_user_presence(self) -> None:
        if not self._state.user_presence:
            raise Exception(
                "confirm_user_presence called but user presence not enabled"
            )
        self._runner.send_signal(SIGUSR1)

    def reboot(self) -> None:
        if self._runner:
            self._runner.terminate()

        (self._runner, self.data) = _spawn(self._binary, self._state)

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

        (runner, device) = _spawn(binary, state)

        return UsbipDevice(binary, device, state, runner)


def _spawn(binary: str, state: UsbipState) -> tuple[Popen[bytes], DeviceData]:
    env = os.environ.copy()
    if "RUST_LOG" not in env:
        env["RUST_LOG"] = "info"
    user_presence = "accept-all"
    if state.user_presence:
        user_presence = "signal"
    runner = Popen(
        [
            binary, "--ifs", state.ifs, "--efs", state.efs,
            "--serial", "0x" + state.serial,
            "--user-presence", user_presence,
        ],
        env=env,
    )
    logger.debug(
        f"{binary} spawned: pid={runner.pid}, ifs={state.ifs}, "
        f", efs={state.efs}, serial={state.serial})"
    )

    host = "localhost"
    check_call(["usbip", "list", "-r", host])
    check_call(["usbip", "attach", "-r", host, "-b", "1-1"])
    check_call(["usbip", "attach", "-r", host, "-b", "1-1"])

    for i in range(5):
        if not find_devices(VID_NITROKEY, PIDS):
            time.sleep(1)
        else:
            break
    device = find_device(VID_NITROKEY, PIDS)

    for i in range(5):
        if not os.path.exists(f"/dev/{device.hidraw}"):
            time.sleep(1)
        else:
            break
    if not os.path.exists(f"/dev/{device.hidraw}"):
        raise RuntimeError(f"hidraw device {device.hidraw} does not show up")

    return (runner, device)


device_pin: Optional[str] = None


class UsbDevice(Device):
    def __init__(self, data: DeviceData, serial: str) -> None:
        super().__init__(data)
        self._serial = serial

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
    def find(serials: List[str]) -> "UsbDevice":
        device = find_device(VID_NITROKEY, PIDS)
        device_serial = get_serial(device.hidraw)
        if int(device_serial, 16) not in map(lambda x: int(x, 16), serials):
            raise RuntimeError(
                "Expected device with any of these UUIDs: "
                f"{','.join(serials)}, found {device_serial}"
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


def find_devices(vid: int, pids: Sequence[int]) -> List[DeviceData]:
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

        if current_vid == vid and current_pid in pids:
            device = find_hidraw_device(root, subdirs)
            if device:
                logger.debug(
                    f"found USB device: vid={current_vid:04x}, "
                    f"pid={current_pid:04x}, device={device}"
                )
                data = DeviceData(
                    hidraw=device,
                    vid=current_vid,
                    pid=current_pid,
                )
                devices.append(data)
    return devices


def find_device(vid: int, pids: Sequence[int]) -> DeviceData:
    devices = find_devices(vid, pids)
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
    efs: str,
    serial: Optional[str] = None,
    user_presence: bool = False,
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

    state = UsbipState(
        ifs=ifs, efs=efs, serial=serial, user_presence=user_presence
    )
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
