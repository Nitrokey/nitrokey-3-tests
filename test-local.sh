#!/bin/sh
# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

set -o errexit

if [ \( $# -eq 0 \) -o \( $# -gt 2 \) ]
then
	echo "Usage: $0 path [upgrade_from]" >&2
	echo "" >&2
	echo "Compile the usbip runner from the firmware repository at the given path" >&2
	echo "and execute the tests using it." >&2
	echo "If upgrade_from is set, also execute upgrade tests using the given revision" >&2
	echo "as the baseline.  This requires a clean working directory so that we can" >&2
	echo "checkout the old revision."
	exit 1
fi

path=$1
manifest=$path/runners/usbip/Cargo.toml
target_dir=${CARGO_TARGET_DIR:-$path/target}

mkdir -p bin

cargo build --release --manifest-path "$manifest"
cp --verbose "$target_dir"/release/usbip-runner bin/usbip-runner
cargo build --release --manifest-path "$manifest" --features provisioner
cp --verbose "$target_dir"/release/usbip-runner bin/usbip-provisioner

if [ $# -eq 2 ]
then
	upgrade_from=$2

	cd "$path"
	git diff-index --quiet HEAD || ( \
		echo "Firmware repository is not in a clean state -- aborting." >&2 ; \
		exit 1 )
	git checkout "$upgrade_from"
	cd -
	cargo build --release --manifest-path "$manifest"
	cp --verbose "$target_dir"/release/usbip-runner bin/usbip-runner-old
	cargo build --release --manifest-path "$manifest" --features provisioner
	cp --verbose "$target_dir"/release/usbip-runner bin/usbip-provisioner-old
	cd "$path"
	git checkout -
	cd -

	export PYTEST_FLAGS="--upgrade"
fi

make run-docker
