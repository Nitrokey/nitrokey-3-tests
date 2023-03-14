#!/bin/sh
# Copyright (C) 2023 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

set -o errexit

if [ \( $# -eq 0 \) -o \( $# -gt 2 \) ]
then
	echo "Usage: $0 tag [upgrade_from]" >&2
	echo "" >&2
	echo "Download the usbip runner for the given release and execute the " >&2
	echo "tests using it." >&2
	echo "If upgrade_from is set, also execute upgrade tests using the given release" >&2
	echo "as the baseline." >&2
	exit 1
fi

tag=$1

mkdir -p bin

runner=`echo $tag | grep --quiet alpha && echo alpha || echo runner`
curl --fail --show-error --silent --location "https://github.com/Nitrokey/nitrokey-3-firmware/releases/download/$tag/usbip-$runner-$tag" --output bin/usbip-runner
curl --fail --show-error --silent --location "https://github.com/Nitrokey/nitrokey-3-firmware/releases/download/$tag/usbip-provisioner-$tag" --output bin/usbip-provisioner

if [ $# -eq 2 ]
then
	upgrade_from=$2

	runner=`echo $upgrade_from | grep --quiet alpha && echo alpha || echo runner`
	curl --fail --show-error --silent --location "https://github.com/Nitrokey/nitrokey-3-firmware/releases/download/$upgrade_from/usbip-$runner-$upgrade_from" --output bin/usbip-runner-old
	curl --fail --show-error --silent --location "https://github.com/Nitrokey/nitrokey-3-firmware/releases/download/$upgrade_from/usbip-provisioner-$upgrade_from" --output bin/usbip-provisioner-old

	export PYTEST_FLAGS="--upgrade"
fi

make run-docker
