#!/bin/bash
# Run a pspdev toolchain command inside the dissidia-pspdev container.
#   tools/dlc/pspenv.sh psp-gcc --version
#   tools/dlc/pspenv.sh make -C tools/dlc/probe
# Toolchain: pspdev v20261001 (pspdev-ubuntu-latest-x86_64.tar.gz, sha256 a86efe62…acd) unpacked at
# the PSPDEV_HOST directory (host glibc 2.35 is too old, hence the container). Project mounted at /work (same layout).
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
: "${PSPDEV_HOST:?Set PSPDEV_HOST to your extracted pspdev toolchain}"
exec docker run --rm -u "$(id -u):$(id -g)" -v "$PSPDEV_HOST":/usr/local/pspdev:ro -v "$ROOT":/work \
     -w /work dissidia-pspdev:1 "$@"
