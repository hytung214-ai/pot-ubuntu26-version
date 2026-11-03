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

## 2026-11-04 — release build, desktop tests and native packaging
- The optimized release build with custom-protocol completed successfully in
  13m49s. The actual ELF links WebKitGTK 4.1, JavaScriptCore 4.1 and libsoup 3;
  no WebKitGTK 4.0 or libsoup 2 is in its runtime dependency tree.
- Dependency audit: 807 package versions unchanged; only soup2/soup2-sys were
  replaced by soup3/soup3-sys 0.2.3. Frontend lock and application Rust source
  remain unchanged.
- Added strict native packaging from the newly compiled ELF. dpkg-shlibdeps
  generates ABI dependencies; runtime AppIndicator, libxdo3, libxrandr2 and
  Tesseract dependencies are explicitly retained for dynamically loaded/external
  functionality. libxdo-dev is replaced by its runtime package, not discarded.
- Native Wayland UI starts, but Tao 0.16 cannot register global shortcuts there
  (confirmed in actual runtime). A process-local launcher selects X11/XWayland
  when DISPLAY is available and GDK_BACKEND is unset. User overrides are honored;
  XDG_SESSION_TYPE and WAYLAND_DISPLAY are preserved for screenshot/selection.
- Added native C ABI probe and real-WebView smoke tests. Xvfb uses GLX disabled
  because the sandbox's NVIDIA EGL path crashed during its initialization.
- The disposable test D-Bus uses a private configuration with AppArmor mediation
  disabled only for that bus: the outer sandbox denies writes needed for kernel
  policy queries. No host bus/security configuration was modified.
- Corrected a local setup mistake: re-extracting the toolchain while check was
  running caused transient SIGBUS/invalid std metadata. After extraction finished,
  rerunning cargo check --locked passed. Bootstrap must run before builds.
- Initial tests passed UI, IPC, text clipboard, native OCR, screenshot capture,
  AppIndicator registration/menu activation, and shortcut-triggered window creation.
  Bing auth returned HTTP 404 and Google HTTP 429; these are recorded as failed
  external-service checks rather than claimed as successful translations.
