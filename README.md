<!--
Copyright (C) 2022 Nitrokey GmbH
SPDX-License-Identifier: CC0-1.0
-->

# nitrokey-3-tests

## Quickstart

To be able to run the tests using usbip simulation, copy the `usbip-runner` binary from the `nitrokey-3-firmware` repository to this directory ([PR](https://github.com/Nitrokey/nitrokey-3-firmware/pull/135)) and make sure that the `vhci-hcd` kernel module is loaded.

- Lint the test code and run all tests in a docker container:
  ```
  $ make
  ```
- Run all tests in a docker container:
  ```
  $ make run-docker
  ```
- Run all tests locally (may require root privileges for usbip):
  ```
  $ make run
  ```
- Lint the test code:
  ```
  $ make check
  ```

## Configuration

The flags passed to `pytest` can be extended by setting the `PYTEST_FLAGS` environment variable.

### Device selection

Per default, the tests use a usbip simulation of a Nitrokey 3 device.  If you want to use them with a real Nitrokey 3 device connected to your computer, set the `--use-usb-device [uuid]` option with the UUID of your device.
