<!--
Copyright (C) 2022 Nitrokey GmbH
SPDX-License-Identifier: CC0-1.0
-->

# nitrokey-3-tests

## Quickstart

To be able to run the tests, copy the `usbip-runner` binary from the `nitrokey-3-firmware` repository to this directory.

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
