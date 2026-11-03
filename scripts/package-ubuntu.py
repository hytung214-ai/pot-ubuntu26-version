#!/usr/bin/env python3
"""Package the newly linked native binary; derive Depends from its actual ELF ABI."""
import argparse
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "src-tauri/target/release/pot")
    parser.add_argument("--output", type=Path, default=ROOT / "work/packages")
    args = parser.parse_args()
    os_release = Path("/etc/os-release").read_text()
    if 'VERSION_ID="26.04"' not in os_release or 'ID=ubuntu' not in os_release:
        raise SystemExit("Build this Ubuntu-specific package on Ubuntu 26.04")
    arch = run(["dpkg", "--print-architecture"]).strip()
    if arch != "amd64":
        raise SystemExit("This port has only been validated for amd64")
    binary = args.binary.resolve(strict=True)
    dynamic = run(["readelf", "-d", str(binary)])
    linked = run(["ldd", str(binary)])
    if "not found" in linked:
        raise SystemExit("Unresolved ELF dependencies:\n" + linked)
    if re.search(r"lib(?:webkit2gtk-4\.0|javascriptcoregtk-4\.0|soup-2\.4)", dynamic + linked):
        raise SystemExit("Old WebKitGTK/libsoup ABI remains in the ELF dependency tree")
    for library in ["libwebkit2gtk-4.1.so", "libjavascriptcoregtk-4.1.so", "libsoup-3.0.so"]:
        if library not in linked:
            raise SystemExit("Expected runtime dependency missing: " + library)
    version = "3.0.7-0ubuntu26.04.1"
    stage = ROOT / "work/deb-stage"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "DEBIAN").mkdir(parents=True)
    (stage / "usr/bin").mkdir(parents=True)
    (stage / "usr/lib/pot").mkdir(parents=True)
    executable = stage / "usr/lib/pot/pot"
    shutil.copy2(binary, executable)
    run(["strip", "--strip-unneeded", str(executable)])
    launcher = stage / "usr/bin/pot"
    shutil.copy2(ROOT / "scripts/pot-launcher.sh", launcher)
    launcher.chmod(0o755)
    desktop = stage / "usr/share/applications/pot.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text("""[Desktop Entry]
Type=Application
Name=Pot
Comment=Text translation and optical character recognition
Exec=pot
Icon=pot
Terminal=false
Categories=Utility;
Keywords=Translation;OCR;
StartupWMClass=pot
""")
    run(["desktop-file-validate", str(desktop)])
    for size, filename in [(32, "32x32.png"), (128, "128x128.png"), (256, "128x128@2x.png")]:
        icon = stage / f"usr/share/icons/hicolor/{size}x{size}/apps/pot.png"
        icon.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "src-tauri/icons" / filename, icon)
    doc = stage / "usr/share/doc/pot"
    doc.mkdir(parents=True)
    license_file = next(p for p in [ROOT / "LICENSE", ROOT / "LICENSE.md"] if p.exists())
    shutil.copy2(license_file, doc / "copyright")
    shutil.copy2(ROOT / "docs/ubuntu-26.04/CHANGES.md", doc / "ubuntu-26.04-changes.md")
    for filename in ["README.zh-CN.md", "TEST-REPORT.zh-CN.md"]:
        shutil.copy2(ROOT / "docs/ubuntu-26.04" / filename, doc / filename)

    # dpkg-shlibdeps needs a source control stanza even for a standalone binary.
    source = ROOT / "work/shlibdeps"
    (source / "debian").mkdir(parents=True, exist_ok=True)
    (source / "debian/control").write_text("""Source: pot
Section: utils
Priority: optional
Maintainer: Local Ubuntu Compatibility Build <noreply@localhost>

Package: pot
Architecture: amd64
Description: Pot translation and OCR
""")
    env = os.environ.copy()
    sysroot = ROOT / "work/sysroot"
    if (sysroot / "usr/share/perl5").exists():
        env["PERL5LIB"] = str(sysroot / "usr/share/perl5")
    # libxdo is extracted locally in this sandbox, so supply its real shlibs
    # declaration from the supported Ubuntu package rather than ignoring errors.
    overrides = source / "debian/shlibs.local"
    xdo_packages = sorted((ROOT / "work/debs").glob("libxdo3_*.deb"))
    if xdo_packages:
        data = subprocess.run(["dpkg-deb", "--ctrl-tarfile", str(xdo_packages[-1])],
                              check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            shlibs = next(member for member in archive if member.name.removeprefix("./") == "shlibs")
            overrides.write_bytes(archive.extractfile(shlibs).read())
    command = ["dpkg-shlibdeps", "-O", "-e" + str(executable)]
    if overrides.exists():
        command += ["-L" + str(overrides)]
    if (sysroot / "usr/lib/x86_64-linux-gnu").exists():
        command += ["-l" + str(sysroot / "usr/lib/x86_64-linux-gnu")]
    result = subprocess.run(command, cwd=source, env=env, text=True, capture_output=True)
    (ROOT / "work/logs/deb-shlibdeps.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    deps = next(line.removeprefix("shlibs:Depends=") for line in result.stdout.splitlines()
                if line.startswith("shlibs:Depends="))
    # AppIndicator is dlopen'ed, and OCR launches tesseract as an external command.
    deps += ", libayatana-appindicator3-1, libxdo3, libxrandr2, xwayland, tesseract-ocr, tesseract-ocr-eng"
    if re.search(r"libwebkit2gtk-4\.0|libsoup2\.4", deps):
        raise SystemExit("Old ABI dependency was generated unexpectedly")
    installed_size = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file()) // 1024
    (stage / "DEBIAN/control").write_text(f"""Package: pot
Version: {version}
Section: utils
Priority: optional
Architecture: {arch}
Maintainer: Local Ubuntu Compatibility Build <noreply@localhost>
Installed-Size: {installed_size}
Depends: {deps}
Description: Pot translation and OCR for Ubuntu 26.04
 Pot Desktop 3.0.7 with a WebKitGTK 4.1 and libsoup 3 compatibility backport.
 Built natively on Ubuntu 26.04; the application retains its Tauri 1 APIs.
""")
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / f"pot_{version}_{arch}.deb"
    run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(output)])
    (ROOT / "work/logs/release-elf.txt").write_text(dynamic + "\n" + linked)
    print(output)
    print("Depends: " + deps)


if __name__ == "__main__":
    main()
