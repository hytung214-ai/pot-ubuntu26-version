# Source this file from the repository root after bootstrap-local.py succeeds.
# All downloaded tools and Cargo caches remain inside work/.
POT_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
POT_SYSROOT="$POT_ROOT/work/sysroot"
export PATH="$POT_SYSROOT/usr/bin:$POT_SYSROOT/usr/lib/cargo/bin:$POT_SYSROOT/usr/lib/rust-1.93/bin:$PATH"
export LD_LIBRARY_PATH="$POT_SYSROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBRARY_PATH="$POT_SYSROOT/usr/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
export PKG_CONFIG_PATH="$POT_SYSROOT/usr/lib/x86_64-linux-gnu/pkgconfig:$POT_SYSROOT/usr/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export CARGO_HOME="$POT_ROOT/work/cargo-home"
export CC="$POT_SYSROOT/usr/bin/gcc"
export CXX="$POT_SYSROOT/usr/bin/g++"
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="$CC"
export LIBCLANG_PATH=/usr/lib/x86_64-linux-gnu
export TESSDATA_PREFIX="$POT_SYSROOT/usr/share/tesseract-ocr/5/tessdata"
