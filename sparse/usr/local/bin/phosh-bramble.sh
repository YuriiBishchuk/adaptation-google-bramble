#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export XDG_RUNTIME_DIR=/run/user/32011
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/32011/bus"
export WAYLAND_DISPLAY=wayland-0
export WLR_BACKENDS=drm,libinput
export WLR_DRM_DEVICES=/dev/dri/card0
export WLR_NO_HARDWARE_CURSORS=1
export WLR_RENDERER=vulkan
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.json
export TU_DEBUG=kgsl
export LD_PRELOAD="/usr/lib/libfix_drm_formats.so /usr/lib/libfix_bionic_tls.so"
export LIBSEAT_BACKEND=builtin
export SEATD_VTBOUND=0
export GDK_BACKEND=wayland
export GSK_RENDERER=ngl
export XDG_CURRENT_DESKTOP=Phosh:GNOME
export DESKTOP_SESSION=phosh
export XDG_SESSION_TYPE=wayland

# Clean up stale locks
rm -f /run/user/32011/wayland-0* 2>/dev/null || true

# Import environment to user session
systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true

exec /usr/bin/phosh-session "$@"
