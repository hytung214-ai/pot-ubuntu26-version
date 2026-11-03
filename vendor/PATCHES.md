# WebKitGTK 4.1 compatibility backport

The four subdirectories were copied from the exact registry archives locked by
Pot Desktop 3.0.7. Their original content is preserved in commit `888cecb`.
Licenses and upstream attribution are included in each crate.

| Crate | Original archive SHA256 |
| --- | --- |
| wry 0.24.11 | c55c80b12287eb1ff7c365fc2f7a5037cb6181bd44c9fce81c8d1cf7605ffad6 |
| webkit2gtk 0.18.2 | b8f859735e4a452aeb28c6c56a852967a8a76c8eb1cc32dbf931ad28a13d6370 |
| webkit2gtk-sys 0.18.0 | 4d76ca6ecc47aeba01ec61e480139dda143796abcae6f83bcddf50d6b5b1dcf3 |
| javascriptcore-rs-sys 0.4.0 | 905fbb87419c5cde6e3269537e4ea7d46431f3008c5d057e915ef3f115e7793c |

Changes are restricted to:

- Wry and WebKit use `soup3` instead of `soup2`. The new crate retains the Rust
  library name `soup`, but it genuinely binds to libsoup 3, using its refcounted
  MessageHeaders implementation. It is not an alias for the old ABI.
- WebKit sys uses `soup3-sys` and imports `soup3_sys`. Cookie and headers pointers
  in its C signatures now have the matching libsoup 3 types.
- Both sys crates probe and explicitly link the 4.1 WebKit/JavaScriptCore ABI.
- Cargo.toml.orig files match the corresponding build-manifest changes.

GTK/GLib remain at 0.15, the generation supported by soup3 0.2. The updated
application lockfile locks soup3 and soup3-sys to 0.2.3. All other application
dependency versions are preserved.

The C probe in scripts/probe-webkit41.c verifies the actual system API and
MessageHeaders ownership. Final validation also needs the application ELF
dependency tree and runtime feature tests; compiling alone is insufficient.

This is a local downstream backport, not an upstream-supported Tauri 1 option.
The old distribution CI still targets WebKitGTK 4.0 and should not be used for
this branch's Linux packages. Use scripts/build-ubuntu-26.04.sh on Ubuntu 26.04.
