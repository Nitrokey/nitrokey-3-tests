# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import subprocess
from pexpect import spawn


def test_lsusb(device) -> None:
    devices = subprocess.check_output(
        ["lsusb", "-d", "20a0:42b2"]
    ).splitlines()
    assert len(devices) == 1


def test_list(device) -> None:
    p = spawn("nitropy nk3 list")
    p.expect("'Nitrokey 3' keys")
    p.expect(f"/dev/{device.hidraw}: Nitrokey 3 {device.serial}")
    # TODO: assert that there are no other keys
