# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

from .basic import TestFido2, TestFido2Resident


def test_fido2(touch_device):
    TestFido2().run(touch_device)


def test_fido2_resident(touch_device):
    TestFido2Resident().run(touch_device)
