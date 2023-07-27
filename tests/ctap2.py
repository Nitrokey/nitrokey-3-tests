# Copyright (C) 2023 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

import glob
import re
from sys import stderr

import pytest
from pexpect import spawn


PROMPT_REBOOT = "Please replug the device, then hit enter."
PROMPT_TOUCH = "Please touch your security key!"
OUTPUT_RESULTS = "RESULTS"
PATTERNS = [PROMPT_REBOOT, PROMPT_TOUCH, OUTPUT_RESULTS]


def detect_tests() -> list[str]:
    regex = re.compile("BaseTest\\(\\s*\"(\\w+)\"")
    tests = []
    for fname in glob.glob("./external/CTAP2-test-tool/src/tests/*.cc"):
        with open(fname) as f:
            text = f.read()
        tests.extend(regex.findall(text))
    return tests


@pytest.mark.parametrize("test", detect_tests())
@pytest.mark.virtual
def test_ctap2(touch_device, test) -> None:
    cmd = "bazel --output_user_root /app/cache/bazel run " \
        f"//:fido2_conformance -- --token_path=/dev/{touch_device.hidraw} " \
        f"--test_ids={test}"
    p = spawn(
        cmd,
        cwd="./external/CTAP2-test-tool",
        encoding="utf-8",
        logfile=stderr,
        timeout=60,
    )

    while True:
        i = p.expect(PATTERNS)
        if PATTERNS[i] == PROMPT_REBOOT:
            touch_device.reboot()
            p.sendline()
        elif PATTERNS[i] == PROMPT_TOUCH:
            touch_device.confirm_user_presence()
        elif PATTERNS[i] == OUTPUT_RESULTS:
            break
        else:
            raise Exception(f"Unexpected pattern index {i}")
