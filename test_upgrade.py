# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import pytest
from conftest import spawn_device
from utils.fido2 import Fido2


pytestmark = pytest.mark.skipif("not config.getoption('upgrade')")


@pytest.mark.virtual
def test_upgrade_fido2(ifs: str) -> None:
    with spawn_device(ifs, suffix="old") as device:
        fido2 = Fido2(device.hidraw)
        credential = fido2.register(b"user_id", "A. User")
    with spawn_device(ifs, provision=False) as device:
        fido2 = Fido2(device.hidraw)
        fido2.authenticate([credential])
