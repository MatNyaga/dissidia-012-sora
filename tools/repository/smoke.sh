#!/bin/bash
# Asset-free, offline smoke check in an isolated copy of committed files.
# Requires an already populated Cargo registry cache; never downloads dependencies.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
for command in git tar python3 cargo xdelta3; do
    command -v "$command" >/dev/null || { echo "Missing prerequisite: $command" >&2; exit 2; }
done
WORK=$(mktemp -d "${TMPDIR:-/tmp}/dissidia-smoke.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT
mkdir "$WORK/source"
git -C "$ROOT" archive HEAD | tar -x -C "$WORK/source"
cd "$WORK/source"
export CARGO_NET_OFFLINE=true
python3 tools/repository/check_source.py
cargo test --offline --locked --manifest-path tools/installer/Cargo.toml
bash tools/installer/tests/run_synthetic.sh "$WORK/fixtures"
echo 'PASS: committed source syntax, Rust unit tests, and synthetic installer cases. No game/GUI/runtime build tested.'
