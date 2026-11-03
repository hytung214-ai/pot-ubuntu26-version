#!/usr/bin/env python3
"""Download/extract Ubuntu build dependencies without installing system packages."""
import concurrent.futures
import hashlib
import base64
import io
import json
import pathlib
import re
import subprocess
import urllib.request
import urllib.parse
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
CACHE = WORK / "debs"
PREFIX = WORK / "sysroot"
PACKAGES = [
    "gcc", "g++", "make", "rustc", "cargo", "dpkg-dev",
    "libwebkit2gtk-4.1-dev", "libssl-dev", "libxdo-dev", "libclang1-21",
    "libayatana-appindicator3-dev", "libxcb1-dev", "libxrandr-dev", "desktop-file-utils",
    "tesseract-ocr", "tesseract-ocr-eng", "patchelf",
]


def download(item):
    url, name, size, checksum = item
    dest = CACHE / name
    algorithm, expected = checksum.split(":", 1)
    algorithm = algorithm.lower().removesuffix("sum")
    if not dest.exists() or hashlib.new(algorithm.lower(), dest.read_bytes()).hexdigest() != expected:
        url = re.sub(r"^http:", "https:", url)
        with urllib.request.urlopen(url, timeout=180) as response:
            data = response.read()
        if len(data) != int(size) or hashlib.new(algorithm.lower(), data).hexdigest() != expected:
            raise RuntimeError(f"Package verification failed: {name}")
        dest.write_bytes(data)
    print(f"Verified {name}", flush=True)
    return dest


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    PREFIX.mkdir(parents=True, exist_ok=True)
    command = ["apt-get", "--print-uris", "--yes", "--download-only",
               "--no-install-recommends", "install", *PACKAGES]
    result = subprocess.run(command, text=True, check=True, capture_output=True)
    (WORK / "apt-download-plan.txt").write_text(result.stdout)
    items = re.findall(r"^'([^']+)'\s+(\S+)\s+(\d+)\s+(\S+)$", result.stdout, re.M)
    if not items:
        raise RuntimeError("No apt download URIs; inspect work/apt-download-plan.txt")
    metadata = subprocess.run(
        ["apt-cache", "show", *sorted({item[1].split("_")[0] for item in items})],
        text=True, check=True, capture_output=True,
    ).stdout
    hashes = {}
    for stanza in metadata.split("\n\n"):
        fields = dict(re.findall(r"^(Filename|SHA256): (.+)$", stanza, re.M))
        if "Filename" in fields and "SHA256" in fields:
            hashes[urllib.parse.unquote(pathlib.Path(fields["Filename"]).name)] = fields["SHA256"]
    items = [(url, name, size, "SHA256:" + hashes[urllib.parse.unquote(url.rsplit("/", 1)[1])])
             for url, name, size, _ in items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(download, items))
    for path in paths:
        subprocess.run(["dpkg-deb", "-x", str(path), str(PREFIX)], check=True)
    # Relocate only extracted pkg-config metadata; host .pc files stay unchanged.
    for pc in PREFIX.rglob("*.pc"):
        if not pc.is_symlink():
            text = pc.read_text()
            text = re.sub(r"(?m)^prefix=/usr$", f"prefix={PREFIX}/usr", text)
            text = re.sub(r"(?m)^exec_prefix=/usr$", f"exec_prefix={PREFIX}/usr", text)
            pc.write_text(text)
    # Dev packages link to runtime SONAMEs already provided by the host.
    for link in (PREFIX / "usr/lib/x86_64-linux-gnu").glob("*.so"):
        if link.is_symlink() and not link.exists():
            host = pathlib.Path("/usr/lib/x86_64-linux-gnu") / link.readlink().name
            if host.exists():
                link.unlink()
                link.symlink_to(host)
    print(f"Extracted {len(paths)} supported Ubuntu packages to {PREFIX}")
    node_version = "22.22.1"
    node_name = f"node-v{node_version}-linux-x64"
    node_url = f"https://nodejs.org/dist/v{node_version}/"
    node_archive = WORK / f"{node_name}.tar.xz"
    sums = urllib.request.urlopen(node_url + "SHASUMS256.txt").read().decode()
    expected = next(line.split()[0] for line in sums.splitlines()
                    if line.split()[-1] == node_archive.name)
    if not node_archive.exists() or hashlib.sha256(node_archive.read_bytes()).hexdigest() != expected:
        node_archive.write_bytes(urllib.request.urlopen(node_url + node_archive.name).read())
    if hashlib.sha256(node_archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Node archive checksum mismatch")
    with tarfile.open(node_archive) as archive:
        archive.extractall(WORK, filter="data")
    metadata = json.load(urllib.request.urlopen("https://registry.npmjs.org/pnpm/9.15.9"))
    pnpm_data = urllib.request.urlopen(metadata["dist"]["tarball"]).read()
    if "sha512-" + base64.b64encode(hashlib.sha512(pnpm_data).digest()).decode() != metadata["dist"]["integrity"]:
        raise RuntimeError("pnpm archive integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(pnpm_data)) as archive:
        for member in archive.getmembers():
            member.name = member.name.removeprefix("package/")
            if member.name:
                archive.extract(member, WORK / "pnpm9", filter="data")
    bin_dir = WORK / "bin"
    bin_dir.mkdir(exist_ok=True)
    node_link = bin_dir / "node"
    if node_link.is_symlink():
        node_link.unlink()
    node_link.symlink_to(f"../{node_name}/bin/node")
    pnpm = bin_dir / "pnpm"
    pnpm.write_text('#!/bin/sh\nexec "$(dirname "$0")/node" "$(dirname "$0")/../pnpm9/bin/pnpm.cjs" "$@"\n')
    pnpm.chmod(0o755)
    print(f"Prepared Node {node_version} and pnpm 9.15.9 locally")


if __name__ == "__main__":
    main()
