# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import os
import os.path
import shutil
from contextlib import contextmanager
from pexpect import spawn
from typing import Generator, Optional, Tuple


SSH_KEY_TYPES = ["ecdsa", "ed25519"]
SSH_USER = "user"


def keygen(
    d: str, type: str, resident: bool = False, pin: Optional[str] = None
) -> Tuple[bytes, bytes]:
    key = os.path.join(d, type)
    pubkey = key + ".pub"
    command = "ssh-keygen"
    args = ["-t", type, "-f", key, "-C", "fido", "-P", ""]
    if resident:
        args += ["-O", "resident"]
    p = spawn(command, args)
    if pin:
        p.expect("Enter PIN for authenticator")
        p.sendline(pin)
    p.expect("public key has been saved")
    with open(key, "rb") as keyfile:
        with open(pubkey, "rb") as pubkeyfile:
            return (keyfile.read(), pubkeyfile.read())


def keypair(d: str, key: bytes, pubkey: bytes) -> Tuple[str, str]:
    key_path = os.path.join(d, "key")
    pubkey_path = key_path + ".pub"
    with open(key_path, "wb") as f:
        f.write(key)
    with open(pubkey_path, "wb") as f:
        f.write(pubkey)
    return (key_path, pubkey_path)


@contextmanager
def authorized_key(pubkey: bytes) -> Generator[None, None, None]:
    ssh_dir = os.path.join(os.path.expanduser("~" + SSH_USER), ".ssh")
    if not os.path.exists(ssh_dir):
        os.mkdir(ssh_dir, mode=0o700)
        shutil.chown(ssh_dir, SSH_USER, SSH_USER)
    ssh_authorized_keys = os.path.join(ssh_dir, "authorized_keys")
    with open(ssh_authorized_keys, "wb") as f:
        f.write(pubkey)
    shutil.chown(ssh_authorized_keys, SSH_USER, SSH_USER)
    try:
        yield
    finally:
        os.remove(ssh_authorized_keys)


def ssh_command(pubkey: str, cmd: str) -> str:
    return f"ssh -i '{pubkey}' -o UserKnownHostsFile=/dev/null " \
           f"-o StrictHostKeyChecking=no {SSH_USER}@localhost {cmd}"
