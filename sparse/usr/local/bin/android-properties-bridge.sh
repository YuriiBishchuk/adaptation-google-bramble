#!/bin/bash

# 1. Wait up to 5 seconds for Android container PID
PID=""
for i in $(seq 1 25); do
    PID=$(lxc-info -n android -p 2>/dev/null | awk '{print $2}')
    if [ -n "$PID" ] && lxc-info -n android -s 2>/dev/null | grep -q RUNNING; then
        break
    fi
    sleep 0.2
done

# 2. Run init second_stage for 1 second to create property mmap workspace if not already present
if [ ! -f /dev/__properties__/properties_serial ]; then
    timeout 1 lxc-attach -n android -- /system/bin/init second_stage 2>/dev/null || true
fi

# 3. Bind mount properties to container dev if needed
if [ -n "$PID" ] && [ -d "/proc/$PID/root/dev" ]; then
    mkdir -p "/proc/$PID/root/dev/__properties__"
    mountpoint -q "/proc/$PID/root/dev/__properties__" || mount --bind /dev/__properties__ "/proc/$PID/root/dev/__properties__" 2>/dev/null || true
fi

# 4. Patch hwservicemanager.ready = true directly into property memory map
python3 -c '
for p in ["/dev/__properties__/u:object_r:hwservicemanager_prop:s0"]:
    try:
        with open(p, "r+b") as f:
            d = bytearray(f.read())
            idx = d.find(b"hwservicemanager.ready")
            if idx != -1:
                val_idx = idx - 92
                d[val_idx - 1] = 4
                d[val_idx:val_idx+6] = b"true\x00\x00"
                f.seek(0)
                f.write(d)
                f.flush()
    except Exception:
        pass
' 2>/dev/null || true

# 5. Touchscreen udev rule for Focaltech FT5446 (event2 -> minor 66)
mkdir -p /run/udev/data
cat << 'UDEV' > /run/udev/data/c13:66
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
UDEV

# 6. Turn on display backlight to max
echo 1023 > /sys/class/backlight/panel0-backlight/brightness 2>/dev/null || true

exit 0
