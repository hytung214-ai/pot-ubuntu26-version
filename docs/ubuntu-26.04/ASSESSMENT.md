# Ubuntu 26.04 compatibility assessment and implementation plan

Baseline: Pot 3.0.7, commit d05a436c9f426a94c38e176f096aeca04c3bf06a.
Branch: compat/ubuntu-26.04. Original tag is unchanged.

## Evidence (2026-11-03)
- Ubuntu 26.04 LTS, amd64; Wayland session with XWayland available.
- Installed GTK 3.24.52, WebKitGTK 4.1 / JavaScriptCore 2.52.6,
  libsoup 3.6.6, Ayatana AppIndicator 0.5.94.
- Locked Tauri 1.8.1, tauri-build 1.5.5, runtime-wry 0.14.10,
  Wry 0.24.11, Tao 0.16.10, webkit2gtk 0.18.2 / sys 0.18.0.
- That WebKit binding probes webkit2gtk-4.0 and uses libsoup 2.
  Ubuntu repositories offer WebKitGTK 4.1 development files, not 4.0.
  Changing deb dependency names cannot change the binary ABI.
- Existing Linux CI builds inside rust:bullseye and installs WebKitGTK 4.0;
  it does not represent a native Ubuntu 26.04 build.
- Rust/C/C++/Node and several development packages are absent in this sandbox.
- /mnt/data-drive is read-only inside the sandbox. User authorized working in
  /home/huanyu/Documents/Codex/pot_modify instead.

## Plan, before modifying application/framework code
1. Preserve original tag and lock files; establish a branch and change log.
2. Extract supported Ubuntu 26.04 build tools/development packages locally;
   do not install old libraries, remount disks, or modify system configuration.
3. Capture an original locked-build failure.
4. First evaluate a bounded Tauri 1 backport: keep GTK 0.15 and application
   APIs, use soup3 0.2 (same GLib 0.15 generation), and patch the WebKit,
   JavaScriptCore and Wry integration consistently. Audit changed C signatures
   and removed API; do not merely rename libraries or dependencies.
5. If that approach requires extensive unsafe or unsupported framework work,
   migrate Tauri 2 in a separate commit, preserving business logic.
6. Build frontend and Rust incrementally, log each failure and correction.
7. Verify loaded ELF libraries and deb dependencies; test translation, OCR,
   clipboard, tray and shortcuts; distinguish tested/failed/blocked results.
8. Produce a native amd64 deb only after a successful release build.

## Tauri 2 fallback scope
Feasible, medium-sized migration; several days to two weeks is an estimate,
not a commitment. Frontend imports include HTTP in 37 files and shell in 32.
Changes: invoke/api/core; Window/WebviewWindow builders and accessors;
HTTP (fetch/Response semantics), fs, clipboard, shortcut, shell, notification,
process and updater plugins; six Rust plugins; tray/menu implementation;
configuration/capabilities; event handling; existing store/SQLite compatibility.
Wayland screenshot/selection/global shortcut behavior needs separate validation;
framework migration alone does not guarantee native Wayland support.

Sources:
- https://github.com/pot-app/pot-desktop/tree/3.0.7
- https://github.com/tauri-apps/wry/blob/wry-v0.24.11/Cargo.toml
- https://tauri.app/blog/tauri-2-0-0-alpha-3/
- https://v2.tauri.app/start/migrate/from-tauri-1/
