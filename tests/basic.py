# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0
import logging
import os
import pytest
import random
import string
from contextlib import contextmanager, suppress
from pexpect import EOF, spawn, ExceptionPexpect, TIMEOUT
from tempfile import TemporaryDirectory
from utils.fido2 import Fido2
from utils.ssh import (
    SSH_KEY_TYPES, SSH_USER, authorized_key, keygen, keypair, ssh_command
)
from utils.subprocess import check_output
from utils.upgrade import UpgradeTest


def test_lsusb(device) -> None:
    devices = check_output(["lsusb", "-d", "20a0:42b2"]).splitlines()
    assert len(devices) == 1


def test_list(device) -> None:
    p = spawn("nitropy nk3 list")
    p.expect("'Nitrokey 3' keys")
    p.expect(f"/dev/{device.hidraw}: Nitrokey 3 {device.serial}")
    # TODO: assert that there are no other keys


class TestFido2(UpgradeTest):
    __test__ = False

    # TODO:
    # - Test server with non-registered client
    # - Test client with non-registered server
    # - Test with multiple credentials

    @contextmanager
    def context(self, device):
        yield Fido2(device)

    def prepare(self, fido2):
        return fido2.register(b"user_id", "A. User")

    def verify(self, fido2, credential):
        fido2.authenticate([credential])


def test_fido2(device):
    TestFido2().run(device)


class TestFido2Resident(UpgradeTest):
    __test__ = False

    def __init__(self):
        # TODO: PIN generation
        self.pin = "".join(random.choices(string.digits, k=8))

    @contextmanager
    def context(self, device):
        yield device

    def prepare(self, device):
        device.set_pin(self.pin)
        fido2 = Fido2(device, self.pin)
        return fido2.register(b"user_id", "A. User", resident_key=True)

    def verify(self, device, credential):
        fido2 = Fido2(device, self.pin)
        fido2.authenticate([credential])

        p = spawn("nitropy fido2 list-credentials")
        p.expect("provide pin")
        p.sendline(self.pin)
        p.expect(f"id: {credential.credential_id.hex()}")
        p.expect("user: A. User")

        p = spawn("nitropy fido2 delete-credential")
        p.expect("provide credential-id")
        p.sendline(credential.credential_id.hex())
        p.expect("provide pin")
        p.sendline(self.pin)
        p.expect("successfully deleted")


def test_fido2_resident(device):
    TestFido2Resident().run(device)


class TestSecrets(UpgradeTest):
    __test__ = False

    def __init__(self):
        # TODO: PIN generation
        self.pin = "".join(random.choices(string.digits, k=8))

    def _spawn_with_pin(self, s):
        p = spawn(s)
        with suppress(EOF, TIMEOUT):
            p.expect("Current PIN", timeout=5)
            p.sendline(self.pin)
        return p

    def _list_and_get(self, i):
        p = self._spawn_with_pin("nitropy nk3 secrets list")
        output = p.read().decode("utf-8")
        assert "test_hotp" in output
        assert "test_totp" in output

        p = self._spawn_with_pin("nitropy nk3 secrets get test_hotp")
        before_buf = p.before.decode("utf-8")
        logging.getLogger("main").debug(before_buf)
        otp_code = "755224" if i == 0 else "287082"
        assert otp_code in before_buf

        p = self._spawn_with_pin(
            "nitropy nk3 secrets get test_totp --timestamp 59"
        )
        before_buf = p.before.decode("utf-8")
        logging.getLogger("main").debug(before_buf)
        otp_code ="287082"
        assert otp_code in before_buf

    @contextmanager
    def context(self, device):
        yield device

    def prepare(self, device):
        p = spawn("nitropy nk3 secrets set-pin")
        p.expect("Password:")
        p.sendline(self.pin)
        p.expect("Repeat for confirmation:")
        p.sendline(self.pin)
        p.expect("Password set")

        p = self._spawn_with_pin(
            "nitropy nk3 secrets register --kind HOTP test_hotp "
            "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        )
        p.expect(EOF)

        p = self._spawn_with_pin(
            "nitropy nk3 secrets register --kind TOTP test_totp "
            "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        )
        p.expect(EOF)

        self._list_and_get(0)

    def verify(self, device, state):
        self._list_and_get(1)


def test_secrets(device) -> None:
    TestSecrets().run(device)

