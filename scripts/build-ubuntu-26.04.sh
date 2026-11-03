#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ "${1:-}" == "--local" ]]; then
    source scripts/local-env.sh
    shift
fi
mkdir -p work/logs
pkg-config --modversion gtk+-3.0 webkit2gtk-4.1 javascriptcoregtk-4.1 libsoup-3.0
pnpm install --frozen-lockfile
pnpm build
cargo build --manifest-path src-tauri/Cargo.toml --release --locked --features custom-protocol
python3 scripts/package-ubuntu.py "$@"
