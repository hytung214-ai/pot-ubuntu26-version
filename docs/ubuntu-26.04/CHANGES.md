# Change record

## 2026-11-03 — baseline and local build setup
- Checked out unmodified upstream 3.0.7 in an independent compatibility branch.
- Added assessment/plan and this record before application source changes.
- Ignore work/ so downloaded toolchains, build caches and diagnostic logs do
  not enter source control. These are local build artifacts, not shipped code.
- System package installation and system configuration changes are avoided.
