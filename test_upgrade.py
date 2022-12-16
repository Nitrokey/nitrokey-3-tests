# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import pytest
from utils.device import spawn_device
from utils.fido2 import Fido2


pytestmark = pytest.mark.skipif("not config.getoption('upgrade')")


@pytest.mark.virtual
def test_upgrade_fido2(serial: str, ifs: str) -> None:
    with spawn_device(serial=serial, ifs=ifs, suffix="old") as device:
        fido2 = Fido2(device.hidraw)
        credential = fido2.register(b"user_id", "A. User")
    with spawn_device(serial=serial, ifs=ifs, provision=False) as device:
        fido2 = Fido2(device.hidraw)
        fido2.authenticate([credential])
