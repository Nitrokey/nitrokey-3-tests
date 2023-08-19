# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0
import os
import random
import string
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest
from pexpect import spawn

from utils.ssh import (
    SSH_KEY_TYPES, SSH_USER, authorized_key, keygen, keypair, ssh_command
)
from utils.upgrade import UpgradeTest


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
