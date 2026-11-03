#!/usr/bin/env python3
"""Download/extract Ubuntu build dependencies without installing system packages."""
import concurrent.futures
import hashlib
import pathlib
import re
import subprocess
import urllib.request
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
CACHE = WORK / "debs"
PREFIX = WORK / "sysroot"
PACKAGES = [
    "gcc", "g++", "make", "rustc", "cargo", "nodejs",
    "libwebkit2gtk-4.1-dev", "libssl-dev", "libxdo-dev", "libclang1-21",
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


if __name__ == "__main__":
    main()
