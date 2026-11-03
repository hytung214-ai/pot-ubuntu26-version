# Change record

## 2026-11-03 — baseline and local build setup
- Checked out unmodified upstream 3.0.7 in an independent compatibility branch.
- Added assessment/plan and this record before application source changes.
- Ignore work/ so downloaded toolchains, build caches and diagnostic logs do
  not enter source control. These are local build artifacts, not shipped code.
- System package installation and system configuration changes are avoided.

## WebKitGTK 4.1 backport (experimental until runtime tests pass)
- Original cargo check --locked reproduced a soup2-sys failure: libsoup-2.4.pc
  is absent. Full log: work/logs/baseline-cargo-check.log.
- Vendored exactly four crates from the original lockfile. Original archives
  were verified against their Cargo.lock SHA256 checksums, then committed
  unchanged separately so framework edits are directly reviewable.
- Wry and WebKit bindings now use the real soup3/soup3-sys crates (GLib 0.15),
  not an alias or symlink to libsoup 2. Soup interaction is limited to opaque
  Cookie and MessageHeaders pointers and matching headers methods. Soup3's
  Shared/refcounted MessageHeaders wrapper handles libsoup 3 ownership.
- WebKit/JavaScriptCore pkg-config metadata AND explicit FFI link attributes
  target 4.1. No build dependency checks are bypassed.
- Frontend lockfile and application code remain unchanged; frontend build passes.
- Local build fixes: add relocated compiler executable/multiarch include paths;
  limit Cargo jobs to 2; use project-era pnpm 9.15.9 with bundled Node 24.22.1.
  Extracted Ubuntu Node cannot run relocated because it has hardcoded /usr/share
  JS module paths. No host Node files were changed.
