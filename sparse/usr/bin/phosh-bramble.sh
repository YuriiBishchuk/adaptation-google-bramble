#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export WLR_BACKENDS=drm,libinput
export WLR_DRM_DEVICES=/dev/dri/card0
export WLR_NO_HARDWARE_CURSORS=1
export WLR_RENDERER=vulkan
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.json
export TU_DEBUG=kgsl
export LD_PRELOAD="/usr/lib/libfix_drm_formats.so /usr/lib/libfix_bionic_tls.so"
export LIBSEAT_BACKEND=noop
export GDK_BACKEND=wayland
export GSK_RENDERER=ngl
export XDG_CURRENT_DESKTOP=Phosh:GNOME
export DESKTOP_SESSION=phosh
export XDG_SESSION_TYPE=wayland

exec /usr/bin/phosh-session "$@"
