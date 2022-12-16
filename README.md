<!--
Copyright (C) 2022 Nitrokey GmbH
SPDX-License-Identifier: CC0-1.0
-->

# nitrokey-3-tests

## Quickstart

Make sure that the `vhci-hcd` kernel module is loaded:
```
# lsmod | grep vhci_hcd || modprobe vhci-hcd
```

Use the `test-local.sh` script to compile the usbip runner from a local Git checkout of the [`nitrokey-3-firmware`][] repository and to execute all tests for it:
```
$ ./test-local.sh ../nitrokey-3-firmware
```

If you have a clean Git checkout, you can also enable upgrade tests from an old commit:
```
$ ./test-local.sh ../nitrokey-3-firmware v1.3.0
```
This will build the new firmware from `HEAD` and the old firmware from the specified revision or tag.

[`nitrokey-3-firmware`]: https://github.com/Nitrokey/nitrokey-3-firmware

## Using the Makefile

If you want to use the Makefile to run the tests, you have to provide the `usbip-runner` and `usbip-provisioner` binaries in the `bin` directory, for example by building them from source.  See the `test-local.sh` script for insipration.  If you want to execute the upgrade tests, you also have to provide the `usbip-runner-old` and `usbip-provisioner-old` binaries for the firmware version to upgrade from.

These are the most useful targets in the Makefile:

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

### Upgrade tests

To enable upgrade tests, set the `--upgrade` flag.  This only works with virtual devices and requires the `usbip-runner-old` and `usbip-provisioner-old` binaries.

### Device selection

Per default, the tests use a usbip simulation of a Nitrokey 3 device.  If you want to use them with a real Nitrokey 3 device connected to your computer, set the `--use-usb-device [uuid]` option with the UUID of your device and disable the tests with the `virtual` mark with the `-m "not virtual"` option.
