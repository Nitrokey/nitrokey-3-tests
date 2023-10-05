# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import os
import pytest
import random
import string
from contextlib import contextmanager
from pexpect import EOF, spawn
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
        p.expect("Current PIN")
        p.sendline(self.pin)
        return p

    def _list_and_get(self, i):
        p = self._spawn_with_pin("nitropy nk3 secrets list")
        output = p.read().decode("utf-8")
        assert "test_hotp" in output
        assert "test_totp" in output

        p = self._spawn_with_pin("nitropy nk3 secrets get test_hotp")
        if i == 0:
            p.expect("755224")
        else:
            p.expect("287082")

        p = self._spawn_with_pin(
            "nitropy nk3 secrets get test_totp --timestamp 59"
        )
        p.expect("287082")

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
            "nitropy nk3 secrets register --kind HOTP --protect-with-pin "
            "test_hotp GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        )
        p.expect(EOF)

        p = self._spawn_with_pin(
            "nitropy nk3 secrets register --kind TOTP --protect-with-pin "
            "test_totp GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        )
        p.expect(EOF)

        self._list_and_get(0)

    def verify(self, device, state):
        self._list_and_get(1)


def test_secrets(device) -> None:
    TestSecrets().run(device)


class TestSsh(UpgradeTest):
    __test__ = False

    def __init__(self, type: str):
        self.type = type

    @contextmanager
    def context(self, device):
        with TemporaryDirectory() as d:
            yield (device, d)

    def prepare(self, context):
        (device, d) = context
        return keygen(d, self.type)

    def verify(self, context, state):
        (device, d) = context
        (key, pubkey) = state
        (key_path, pubkey_path) = keypair(d, key, pubkey)
        with authorized_key(pubkey):
            p = spawn(ssh_command(pubkey_path, "whoami"))
            p.expect(SSH_USER)


@pytest.mark.parametrize("type", SSH_KEY_TYPES)
def test_ssh(device, type) -> None:
    TestSsh(type).run(device)


class TestSshResident(UpgradeTest):
    __test__ = False

    def __init__(self, type: str):
        self.type = type + "-sk"
        # TODO: PIN generation
        self.pin = "".join(random.choices(string.digits, k=8))

    @contextmanager
    def context(self, device):
        with TemporaryDirectory() as d:
            yield (device, d)

    def prepare(self, context):
        (device, d) = context
        device.set_pin(self.pin)
        return keygen(d, self.type, resident=True, pin=self.pin)

    def verify(self, context, state):
        (device, d) = context
        (key, pubkey) = state
        (key_path, pubkey_path) = keypair(d, key, pubkey)
        with authorized_key(pubkey):
            p = spawn(ssh_command(pubkey_path, "whoami"))
            p.expect(SSH_USER)

        filename = "id_" + self.type.replace('-', '_') + "_rk"
        download_dir = os.path.join(d, "download")
        os.mkdir(download_dir)
        pwd = os.getcwd()
        try:
            os.chdir(download_dir)
            p = spawn("ssh-keygen -K")
            p.expect("Enter PIN for authenticator")
            p.sendline(self.pin)
            p.expect("Enter passphrase")
            p.sendline("")
            p.expect("Enter same passphrase")
            p.sendline("")
            p.expect(filename)
            assert os.path.exists(filename)
            # TODO: check why the key is partially different
            # with open(filename, "rb") as f:
            #     assert f.read() == key
        finally:
            os.chdir(pwd)


@pytest.mark.parametrize("type", SSH_KEY_TYPES)
def test_ssh_resident(device, type) -> None:
    TestSshResident(type).run(device)
