# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import copy
import logging
import pathlib
import os
import os.path
import secrets
from enum import Enum, auto
from functools import partial
from pytest import Config, FixtureRequest, Parser, fixture
from typing import Generator
from utils.device import (
    Device, UsbDevice, generate_serial, state_dir, spawn_device
)
from utils.subprocess import check_output

import pytest

from pynitrokey.cli import CliException
from pynitrokey.cli.nk3 import Context
from pynitrokey.nk3.secrets_app import Instruction, SecretsApp

CORPUS_PATH = "/tmp/corpus"


logger = logging.getLogger(__name__)
log = logger.debug


def _write_corpus(
    ins: Instruction, data: bytes, prefix: str = "", path: str = CORPUS_PATH
):
    corpus_name = f"{prefix}"
    corpus_path = f"{path}/{corpus_name}"
    if len(data) > 255:
        # Do not write records longer than 255 bytes
        return
    data = bytes([len(data)]) + data
    with open(corpus_path, "ba") as f:
        print(f"Writing corpus data to the path {corpus_path}")
        f.write(data)


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--keep-state", action="store_true",
    )
    parser.addoption(
        "--upgrade", action="store_true",
    )
    parser.addoption(
        "--use-usb-devices", action="store", nargs="*"
    )
    parser.addoption(
        "--generate-fuzzing-corpus",
        action="store_true",
        default=False,
        help="Enable generation of fuzzing corpus for the oath-authenticator.",
    )
    parser.addoption(
        "--fuzzing-corpus-path",
        type=pathlib.Path,
        default=CORPUS_PATH,
        help=f"Path to store the generated fuzzing corpus. Default: {CORPUS_PATH}.",
    )
    parser.addoption(
        "--model",
        action="store",
        default="nk3",
        help="Select nitrokey model.",
        choices=("nk3", "nkpk"),
    )
    parser.addoption(
        "--test-suite",
        action="store",
        default="basic",
        help="Select test suite.",
        choices=("basic", "normal", "full", "slow"),
    )
    parser.addoption(
        "--virtual", action="store_true", default=False,
        help="Enable virtual tests.",
    )
    parser.addoption(
        "--hil", action="store_true", default=False,
        help="Disable tests that should not be run on hil."
    )


def pytest_collection_modifyitems(config, items):
    virtual = config.getoption("--virtual")
    hil = config.getoption("--hil")
    model = config.getoption("--model")
    test_suite = config.getoption("--test-suite")

    skip_virtual = pytest.mark.skip(reason="need --virtual option to run")
    skip_hil = pytest.mark.skip(reason="does not run on hil")
    skip_nkpk = pytest.mark.skip(reason="does not run on model nkpk")
    skip_slow = pytest.mark.skip(reason="slow test-suite not selected")
    skip_full = pytest.mark.skip(reason="full test-suite not selected")
    skip_normal = pytest.mark.skip(reason="normal test-suite not selected")
    for item in items:
        if not virtual:
            if "virtual" in item.keywords:
                item.add_marker(skip_virtual)
        if hil:
            if "hil_skip" in item.keywords:
                item.add_marker(skip_hil)
        if model == "nkpk":
            if "nkpk_skip" in item.keywords:
                item.add_marker(skip_nkpk)
        if test_suite in ["basic", "normal", "full"]:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
        if test_suite in ["basic", "normal"]:
            if "full" in item.keywords:
                item.add_marker(skip_full)
        if test_suite == "basic":
            if "basic" not in item.keywords:
                item.add_marker(skip_normal)


def pytest_report_header(config: Config) -> str:
    def get_version(binary: str) -> str:
        path = os.path.join("bin", binary)
        if os.path.exists(path):
            version = "v" + check_output([path, "--version"]).split()[1]
        else:
            version = "[missing]"
        return version

    runner_version = get_version("usbip-runner")
    provisioner_version = get_version("usbip-provisioner")
    if runner_version == provisioner_version:
        version = runner_version
    else:
        version = f"{runner_version}/{provisioner_version}"
    header = f"usbip-runner: {version}"

    if config.getoption("--upgrade"):
        runner_version = get_version("usbip-runner")
        provisioner_version = get_version("usbip-provisioner")
        if runner_version == provisioner_version:
            version = runner_version
        else:
            version = f"{runner_version}/{provisioner_version}"
        header += f" (old: {version})"

    return header


@fixture(scope="module")
def device(request: FixtureRequest) -> Generator[Device, None, None]:
    serials = request.config.getoption("--use-usb-devices")
    if serials:
        yield UsbDevice.find(serials)
    else:
        keep_state = request.config.getoption("--keep-state")
        with state_dir(keep_state) as s:
            ifs = os.path.join(s, "ifs.bin")
            efs = os.path.join(s, "efs.bin")
            with spawn_device(ifs, efs) as device:
                yield device


@fixture(scope="module")
def touch_device(request: FixtureRequest) -> Generator[Device, None, None]:
    serials = request.config.getoption("--use-usb-devices")
    if serials:
        yield UsbDevice.find(serials)
    else:
        keep_state = request.config.getoption("--keep-state")
        with state_dir(keep_state) as s:
            ifs = os.path.join(s, "ifs.bin")
            efs = os.path.join(s, "efs.bin")
            with spawn_device(ifs, efs, user_presence=True) as device:
                yield device


@fixture
def ifs(request: FixtureRequest) -> Generator[str, None, None]:
    keep_state = request.config.getoption("--keep-state")
    with state_dir(keep_state) as s:
        yield os.path.join(s, "ifs.bin")


@fixture
def efs(request: FixtureRequest) -> Generator[str, None, None]:
    keep_state = request.config.getoption("--keep-state")
    with state_dir(keep_state) as s:
        yield os.path.join(s, "efs.bin")


@fixture
def serial() -> str:
    return generate_serial()

# extra secrets tests fixtures


@fixture(scope="session")
def generate_corpus_args(request: FixtureRequest):
    return request.config.getoption(
        "--generate-fuzzing-corpus"
    ), request.config.getoption("--fuzzing-corpus-path")


@fixture(scope="function")
def corpus_func(request: FixtureRequest, generate_corpus_args):
    """
    This fixture has to be function-scoped, to get different prefix "pre" for the per-test output
    """
    generate_corpus, corpus_path = generate_corpus_args
    if generate_corpus:
        print(f"\n*** Generating corpus for Secrets App fuzzing at {corpus_path}")
        pathlib.Path(corpus_path).mkdir(exist_ok=True)
        # Add some random suffix to have separate outputs for parametrized test cases
        pre = secrets.token_bytes(4).hex()
        pre = f"{request.function.__name__}-{pre}"
        return partial(_write_corpus, prefix=pre, path=corpus_path)
    return None


@fixture(scope="session")
def dev():
    ctx = Context(None)
    try:
        return ctx.connect_device()
    except CliException as e:
        if "No Nitrokey 3 device found" in str(e):
            pytest.skip(f"Cannot connect to the Nitrokey 3 device. Error: {e}")


class CredEncryptionType(Enum):
    # This requires providing PIN for encryption to work
    PinBased = auto()
    # Standard encryption
    HardwareBased = auto()


@fixture(scope="function")
def secretsAppRaw(corpus_func, dev) -> SecretsApp:
    """
    Create Secrets App client with or without corpus files generations.
    No other functional alterations.
    """
    app = SecretsApp(dev, logfn=log)
    app.write_corpus_fn = corpus_func
    return app


@fixture(
    scope="function",
    params=[
        CredEncryptionType.HardwareBased,
        CredEncryptionType.PinBased,
    ],
    ids=lambda x: f"Key{str(x).split('.')[-1]}",
)
def secretsApp(request, secretsAppRaw) -> SecretsApp:
    """
    Create Secrets App client in two forms, w/ or w/o PIN-based encryption
    """
    app = copy.deepcopy(secretsAppRaw)

    credentials_type: CredEncryptionType = request.param
    app.verify_pin_raw_always = app.verify_pin_raw
    if credentials_type == CredEncryptionType.PinBased:
        # Make all credentials registered with the PIN-based encryption
        # Leave verify_pin_raw() working
        app.register = partial(app.register, pin_based_encryption=True)
    elif credentials_type == CredEncryptionType.HardwareBased:
        # Make all verify_pin_raw() calls dormant
        # All credentials should register themselves as not requiring PIN
        app.verify_pin_raw = lambda x: secretsAppRaw.logfn(
            "Skipping verify_pin_raw() call due to fixture configuration"
        )
    else:
        raise RuntimeError("Wrong param value")

    app._metadata["fixture_type"] = credentials_type

    return app


@fixture(scope="function")
def secretsAppResetLogin(secretsApp) -> SecretsApp:
    secretsApp.reset()
    secretsApp.set_pin_raw(PIN)
    secretsApp.verify_pin_raw(PIN)
    return secretsApp


@fixture(scope="function")
def secretsAppNoLog(secretsApp) -> SecretsApp:
    return secretsApp


FEATURE_BRUTEFORCE_PROTECTION_ENABLED = False
DELAY_AFTER_FAILED_REQUEST_SECONDS = 2
CREDID = "CRED ID"
CREDID2 = "CRED ID2"
SECRET = b"00" * 20
DIGITS = 6
CHALLENGE = 1000
HOTP_WINDOW_SIZE = 9
PIN = "12345678"
PIN2 = "123123123"
PIN_ATTEMPT_COUNTER_DEFAULT = 8
FEATURE_CHALLENGE_RESPONSE_ENABLED = False
CHALLENGE_RESPONSE_COMMANDS = {Instruction.Validate, Instruction.SetCode}
CALCULATE_ALL_COMMANDS = {Instruction.CalculateAll}
