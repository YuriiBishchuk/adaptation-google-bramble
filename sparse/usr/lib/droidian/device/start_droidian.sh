#!/bin/bash
# ==============================================================================
# start_droidian.sh: Complete Droidian Phoc + Phosh Mobile Launcher with Touch
# GPU: Turnip Vulkan (Adreno 620 via /dev/kgsl-3d0) + wlroots DRM backend.
# ==============================================================================
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/tmp
export TEMP=/tmp
export TMP=/tmp
export XDG_RUNTIME_DIR=/tmp/run-user-0
export SEATD_VTBOUND=0
export LIBSEAT_BACKEND=builtin
export LD_PRELOAD="/usr/lib/libfix_drm_formats.so /usr/lib/libfix_bionic_tls.so"
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/libhybris-gl:/usr/lib/aarch64-linux-gnu/libhybris-egl:/usr/lib/aarch64-linux-gnu
export HYBRIS_LD_LIBRARY_PATH=/var/lib/hybris_libs:/vendor/lib64/egl:/vendor/lib64:/system/lib64:/apex/com.android.runtime/lib64/bionic
export WLR_DRM_DEVICES=/dev/dri/card0
export WLR_NO_HARDWARE_CURSORS=1
export WLR_RENDERER=vulkan
export GDK_BACKEND=wayland
export GSK_RENDERER=ngl
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.aarch64.json
export TU_DEBUG=kgsl
export NO_AT_BRIDGE=1
export XDG_CURRENT_DESKTOP=Phosh:GNOME
export DESKTOP_SESSION=phosh

# Performance boost
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$g" 2>/dev/null || true
done

mkdir -p /tmp/run-user-0 /run/udev/data /run/dbus /dev/shm
chmod 700 /tmp/run-user-0
chmod 1777 /dev/shm 2>/dev/null || true
mountpoint -q /dev/shm || mount -t tmpfs tmpfs /dev/shm -o rw,nosuid,nodev,mode=1777 2>/dev/null || true

# --- GPU firmware (/vendor) MUST be mounted before anything touches kgsl ---
# kgsl requests firmware 'a650_sqe.fw' (unified a6xx SQE fw). It lives in the
# Android vendor partition, which is INSIDE the 'super' dynamic partition
# (/dev/block/sda18). If /vendor isn't mounted, kgsl probe fails with
#   request_firmware(a650_sqe.fw) failed: -2
# and the Adreno 620 never initialises -> Turnip finds no GPU -> phoc dies with
#   Could not retrieve physical devices: ERROR_INITIALIZATION_FAILED
# NOTE: the partition->dm index mapping is system=dm-0, product=dm-1,
# system_ext=dm-2, vendor=dm-3 (do NOT assume vendor=dm-0).
if [ ! -e /vendor/firmware/a650_sqe.fw ]; then
    if [ -x /usr/sbin/parse-android-dynparts ] && [ -b /dev/block/sda18 ]; then
        OLD_IFS="$IFS"; IFS=';'
        for part in $(/usr/sbin/parse-android-dynparts /dev/block/sda18); do
            IFS=','
            set -- $part
            pname="$1"; ptable="$5"
            [ -n "$pname" ] && [ -n "$ptable" ] && \
                dmsetup create "$pname" --table "$ptable" --readonly 2>/dev/null || true
            IFS=';'
        done
        IFS="$OLD_IFS"
        for i in 0 1 2 3; do
            [ -e /dev/dm-$i ] || mknod /dev/dm-$i b 253 $i 2>/dev/null || true
        done
    fi
    mkdir -p /vendor
    # vendor is the 4th dynamic partition (dm-3); fall back to scanning blkid.
    if mountpoint -q /vendor || ! mount -t ext4 -o ro /dev/dm-3 /vendor 2>/dev/null; then
        for d in /dev/dm-*; do
            if blkid "$d" 2>/dev/null | grep -q 'vendor'; then
                mount -t ext4 -o ro "$d" /vendor 2>/dev/null && break
            fi
        done
    fi
fi

# --- Required device nodes (NOT auto-created in the Halium chroot) ---
# /dev/ion: misc minor 55 (see /proc/misc). Turnip needs it for
#   VK_KHR_external_memory_fd / VK_EXT_external_memory_dma_buf. Without it the
#   renderer logs "Unable to open neither /dev/dma_heap/system nor /dev/ion" and
#   the notification shade / any dma-buf overlay crashes the compositor.
[ -e /dev/ion ]            || mknod /dev/ion c 10 55 2>/dev/null || true
[ -e /dev/kgsl-3d0 ]       || mknod /dev/kgsl-3d0 c 510 0 2>/dev/null || true
[ -e /dev/dri/card0 ]      || mknod /dev/dri/card0 c 226 0 2>/dev/null || true
[ -e /dev/dri/renderD128 ] || mknod /dev/dri/renderD128 c 226 128 2>/dev/null || true
[ -e /dev/input/event2 ]   || mknod /dev/input/event2 c 13 66 2>/dev/null || true
chmod 666 /dev/ion /dev/kgsl-3d0 /dev/dri/card0 /dev/dri/renderD128 /dev/input/event2 2>/dev/null || true

# Udev entry for Focaltech FT5446 Touchscreen
echo "I:1000" > /run/udev/data/c13:66
echo "E:SUBSYSTEM=input" >> /run/udev/data/c13:66
echo "E:DEVNAME=/dev/input/event2" >> /run/udev/data/c13:66
echo "E:ID_INPUT=1" >> /run/udev/data/c13:66
echo "E:ID_INPUT_TOUCHSCREEN=1" >> /run/udev/data/c13:66
echo "E:ID_INPUT_WIDTH_MM=66" >> /run/udev/data/c13:66
echo "E:ID_INPUT_HEIGHT_MM=144" >> /run/udev/data/c13:66
echo "E:WL_OUTPUT=DSI-1" >> /run/udev/data/c13:66
echo "G:seat" >> /run/udev/data/c13:66
echo "Q:seat" >> /run/udev/data/c13:66
echo "V:1" >> /run/udev/data/c13:66

# Backlight on
echo 1023 > /sys/class/backlight/panel0-backlight/brightness 2>/dev/null || true

# DBus
pgrep -x dbus-daemon >/dev/null || dbus-daemon --system --fork 2>/dev/null || true

# Session bus on standard socket
rm -f /tmp/run-user-0/bus
dbus-daemon --session --address=unix:path=/tmp/run-user-0/bus --fork --nopidfile 2>/dev/null || true
export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/run-user-0/bus

# --- Release DRM master from the Android recovery UI -------------------------
# bramble is a system-as-root device, so the Halium ramdisk boots Android's
# `recovery` (recovery-as-boot). That process opens /dev/dri/card0 and keeps DRM
# master, so Phoc fails with:
#   Could not make device fd drm master: Invalid argument
#   Swapchain for output 'DSI-1' failed test
# init respawns recovery, so we must both `stop` the service and reap the pid.
# Use `stop`/`setprop ctl.stop` (Android init builtin), never plain kill alone.
stop recovery 2>/dev/null || true
setprop ctl.stop recovery init.svc.recovery stopped 2>/dev/null || true
for i in 1 2 3 4 5; do
    pkill -9 -x recovery 2>/dev/null || true
    # does anything still hold card0?
    holder=
    for p in /proc/[0-9]*; do
        if ls -l "$p/fd" 2>/dev/null | grep -q 'dri/card0'; then
            c=$(cat "$p/comm" 2>/dev/null)
            [ "$c" != "phoc" ] && holder="$c"
        fi
    done
    [ -z "$holder" ] && break
    sleep 1
done

killall -9 phoc phosh squeekboard 2>/dev/null || true
sleep 1

echo "[start_droidian] Launching Phoc + Phosh (Turnip Vulkan)..."

cat << "EOSH" > /tmp/run_phosh_session.sh
#!/bin/sh
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export WAYLAND_DISPLAY=wayland-0
export GDK_BACKEND=wayland
export GSK_RENDERER=ngl
export XDG_RUNTIME_DIR=/tmp/run-user-0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/run-user-0/bus
export TMPDIR=/tmp
export LD_PRELOAD="/usr/lib/libfix_drm_formats.so /usr/lib/libfix_bionic_tls.so"

while [ ! -e "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; do
    sleep 0.2
done
sleep 1.5

(
    sleep 2
    which squeekboard >/dev/null 2>&1 && squeekboard &
) &

exec /usr/libexec/phosh -U
EOSH
chmod +x /tmp/run_phosh_session.sh

exec phoc -v -S -C /etc/phosh/phoc.ini -E /tmp/run_phosh_session.sh