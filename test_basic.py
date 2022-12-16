# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

from contextlib import contextmanager
from pexpect import spawn
from utils.fido2 import Fido2
from utils.subprocess import check_output
from utils.upgrade import ExecUpgradeTest


def test_lsusb(device) -> None:
    devices = check_output(["lsusb", "-d", "20a0:42b2"]).splitlines()
    assert len(devices) == 1


def test_list(device) -> None:
    p = spawn("nitropy nk3 list")
    p.expect("'Nitrokey 3' keys")
    p.expect(f"/dev/{device.hidraw}: Nitrokey 3 {device.serial}")
    # TODO: assert that there are no other keys


class TestFido2(ExecUpgradeTest):
    # TODO:
    # - Test server with non-registered client
    # - Test client with non-registered server
    # - Test with multiple credentials

    @contextmanager
    def context(self, device):
        yield Fido2(device.hidraw)

    def prepare(self, fido2):
        return fido2.register(b"user_id", "A. User")

    def verify(self, fido2, credential):
        fido2.authenticate([credential])
