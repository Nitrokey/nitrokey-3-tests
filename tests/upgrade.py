# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

# Tests in this module may not use the device fixture!

import pytest
import tests.basic
from utils.upgrade import ExecUpgradeTest
from utils.ssh import SSH_KEY_TYPES
from typing import Type


pytestmark = pytest.mark.skipif(
    "not config.getoption('upgrade')",
    reason="--upgrade not set",
)


@pytest.mark.parametrize("test", ExecUpgradeTest.__subclasses__())
@pytest.mark.virtual
def test(test: Type[ExecUpgradeTest], serial: str, ifs: str, efs: str) -> None:
    test().run_upgrade(serial, ifs, efs)


@pytest.mark.virtual
def test_fido2(serial: str, ifs: str, efs: str) -> None:
    tests.default.basic.TestFido2().run_upgrade(serial, ifs, efs)


@pytest.mark.virtual
def test_fido2_resident(serial: str, ifs: str, efs: str) -> None:
    tests.default.basic.TestFido2Resident().run_upgrade(serial, ifs, efs)


@pytest.mark.virtual
def test_secrets(serial: str, ifs: str, efs: str) -> None:
    tests.default.basic.TestSecrets().run_upgrade(serial, ifs, efs)


@pytest.mark.virtual
@pytest.mark.parametrize("type", SSH_KEY_TYPES)
def test_ssh(serial: str, ifs: str, efs: str, type: str) -> None:
    tests.default.basic.TestSsh(type).run_upgrade(serial, ifs, efs)


@pytest.mark.virtual
@pytest.mark.parametrize("type", SSH_KEY_TYPES)
def test_ssh_resident(serial: str, ifs: str, efs: str, type: str) -> None:
    tests.default.basic.TestSshResident(type).run_upgrade(serial, ifs, efs)
