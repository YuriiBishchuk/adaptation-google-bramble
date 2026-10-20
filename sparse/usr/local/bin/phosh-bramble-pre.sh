#!/bin/bash
# Pre-start hardware & device preparation (runs as root)

# Ensure CPU governor is performance
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$g" 2>/dev/null || true
done

# Ensure device nodes exist and have proper permissions
[ -e /dev/ion ]            || mknod /dev/ion c 10 55 2>/dev/null || true
[ -e /dev/kgsl-3d0 ]       || mknod /dev/kgsl-3d0 c 510 0 2>/dev/null || true
[ -e /dev/dri/card0 ]      || mknod /dev/dri/card0 c 226 0 2>/dev/null || true
[ -e /dev/dri/renderD128 ] || mknod /dev/dri/renderD128 c 226 128 2>/dev/null || true
[ -e /dev/input/event0 ]   || mknod /dev/input/event0 c 13 64 2>/dev/null || true
[ -e /dev/input/event1 ]   || mknod /dev/input/event1 c 13 65 2>/dev/null || true
[ -e /dev/input/event2 ]   || mknod /dev/input/event2 c 13 66 2>/dev/null || true
[ -e /dev/ttyHS0 ]         || mknod /dev/ttyHS0 c 237 0 2>/dev/null || true
[ -e /dev/btpower ]        || mknod /dev/btpower c 500 0 2>/dev/null || true
[ -e /dev/uinput ]         || mknod /dev/uinput c 10 223 2>/dev/null || true

chmod 666 /dev/ion /dev/kgsl-3d0 /dev/dri/card0 /dev/dri/renderD128 /dev/uinput /dev/ttyHS0 /dev/btpower 2>/dev/null || true
chmod 666 /dev/input/event0 /dev/input/event1 /dev/input/event2 2>/dev/null || true

# Synthetic udev database for libinput
mkdir -p /run/udev/data
# Touchscreen
cat << "UDEV_TS" > /run/udev/data/c13:66
I:1000
E:SUBSYSTEM=input
E:DEVNAME=/dev/input/event2
E:ID_INPUT=1
E:ID_INPUT_TOUCHSCREEN=1
E:ID_INPUT_WIDTH_MM=66
E:ID_INPUT_HEIGHT_MM=144
E:WL_OUTPUT=DSI-1
G:seat
Q:seat
V:1
UDEV_TS

# Power button
cat << "UDEV_PWR" > /run/udev/data/c13:64
I:1000
E:SUBSYSTEM=input
E:DEVNAME=/dev/input/event0
E:ID_INPUT=1
E:ID_INPUT_KEY=1
G:seat
Q:seat
V:1
UDEV_PWR

# Volume buttons
cat << "UDEV_VOL" > /run/udev/data/c13:65
I:1000
E:SUBSYSTEM=input
E:DEVNAME=/dev/input/event1
E:ID_INPUT=1
E:ID_INPUT_KEY=1
G:seat
Q:seat
V:1
UDEV_VOL

# Ensure panel backlight
echo 1023 > /sys/class/backlight/panel0-backlight/brightness 2>/dev/null || true

# Stop Android recovery so it does not hold DRM master
stop recovery 2>/dev/null || true
setprop ctl.stop recovery init.svc.recovery stopped 2>/dev/null || true
for i in 1 2 3; do
    pkill -9 -x recovery 2>/dev/null || true
    sleep 0.2
done

# Ensure /run/user/32011 directory exists with correct ownership
mkdir -p /run/user/32011
chown -R droidian:droidian /run/user/32011
chmod 700 /run/user/32011
rm -f /run/user/32011/wayland-0* 2>/dev/null || true

exit 0
