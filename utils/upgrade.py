# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Generic, TypeVar
from .device import Device, spawn_device


Context = TypeVar("Context")
State = TypeVar("State")


class UpgradeTest(ABC, Generic[Context, State]):
    """
    A test case that can be executed in two steps:  a preparation step and a
    verification step.  The verification step does not have to be executed
    in the same session, making it possible to reboot or upgrade the device
    between the steps.  Both steps can use a context that is constructed
    from the device.

    The `run` and `run_upgrade` methods can be used to easily run the tests
    with a single device or with a firmware upgrade simulation.
    """
    @contextmanager
    @abstractmethod
    def context(self, device: Device) -> Generator[Context, None, None]:
        pass

    @abstractmethod
    def prepare(self, context: Context) -> State:
        pass

    @abstractmethod
    def verify(self, context: Context, state: State) -> None:
        pass

    def run(self, device: Device) -> None:
        with self.context(device) as context:
            state = self.prepare(context)
            self.verify(context, state)

    def run_upgrade(self, serial: str, ifs: str) -> None:
        with spawn_device(serial=serial, ifs=ifs, suffix="old") as device:
            with self.context(device) as context:
                state = self.prepare(context)
        with spawn_device(serial=serial, ifs=ifs, provision=False) as device:
            with self.context(device) as context:
                self.verify(context, state)


class ExecUpgradeTest(UpgradeTest[Context, State]):
    """
    An upgrade test that can be executed automatically because it does not need
    additional fixtures or paremeters.  Subclasses of this class are
    automatically executed in the declaring module using a single device, and
    in the test_upgrade module simulating a firmware upgrade between the
    preparation and verification steps.
    """
    def test(self, device: Device) -> None:
        self.run(device)
