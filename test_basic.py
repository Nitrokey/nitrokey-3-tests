# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

from pexpect import spawn
from utils.fido2 import Fido2
from utils.subprocess import check_output


def test_lsusb(device) -> None:
    devices = check_output(["lsusb", "-d", "20a0:42b2"]).splitlines()
    assert len(devices) == 1


def test_list(device) -> None:
    p = spawn("nitropy nk3 list")
    p.expect("'Nitrokey 3' keys")
    p.expect(f"/dev/{device.hidraw}: Nitrokey 3 {device.serial}")
    # TODO: assert that there are no other keys


def test_fido2(device) -> None:
    fido2 = Fido2(device.hidraw)
    credential = fido2.register(b"user_id", "A. User")
    fido2.authenticate([credential])
    # TODO:
    # - Test server with non-registered client
    # - Test client with non-registered server
    # - Test with multiple credentials
