# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

# Tests in this module may not use the device fixture!

import pytest
from utils.upgrade import ExecUpgradeTest
from typing import Type


pytestmark = pytest.mark.skipif(
    "not config.getoption('upgrade')",
    reason="--upgrade not set",
)


@pytest.mark.parametrize("test", ExecUpgradeTest.__subclasses__())
@pytest.mark.virtual
def test(test: Type[ExecUpgradeTest], serial: str, ifs: str) -> None:
    test().run_upgrade(serial, ifs)
