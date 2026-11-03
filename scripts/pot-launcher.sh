#!/bin/sh
# Tao 0.16 implements global shortcuts only on X11. In a Wayland session,
# select XWayland for this app when DISPLAY is available. Keep session metadata
# intact so Pot's screenshot/selection code can still use Wayland portals.
if [ -z "${GDK_BACKEND:-}" ] && [ -n "${DISPLAY:-}" ]; then
    export GDK_BACKEND=x11
fi
POT_EXEC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$POT_EXEC_DIR/../lib/pot/pot" "$@"
