#!/usr/bin/env python3
"""
BrambleGate Cairo Stage-1 Mobile Boot Manager
Interactive OLED bootloader for Google Pixel 4a (5G) (bramble / SM7250)
Powered by Linux DRM / KMS and Cairo 2D Vector Rendering Engine.
"""

import os
import sys
import time
import math
import select
import struct
import mmap
import fcntl
import ctypes
import subprocess

# Check if disabled via config file or kernel command line
CONFIG_FILE = "/etc/default/bramblegate"
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as cf:
            for line in cf:
                if line.strip().startswith("ENABLED=0") or line.strip().startswith("ENABLED=false"):
                    print("⏩ [BrambleGate] Disabled via /etc/default/bramblegate. Handing over directly to desktop...", flush=True)
                    sys.exit(0)
    except Exception:
        pass

if os.path.exists("/proc/cmdline"):
    try:
        with open("/proc/cmdline", "r") as kf:
            cmdline = kf.read()
            if "nobramblegate" in cmdline or "bramblegate=0" in cmdline:
                print("⏩ [BrambleGate] Disabled via kernel cmdline. Handing over directly to desktop...", flush=True)
                sys.exit(0)
    except Exception:
        pass

print("🚀 [BrambleGate] Starting Cairo Stage-1 Mobile Boot Manager...", flush=True)

# ---------------------------------------------------------
# C Library Bindings: libdrm & libcairo
# ---------------------------------------------------------
libdrm = ctypes.CDLL('libdrm.so.2', use_errno=True)
cairo = ctypes.CDLL('libcairo.so.2', use_errno=True)

# Cairo Structures & Functions
class cairo_text_extents_t(ctypes.Structure):
    _fields_ = [
        ('x_bearing', ctypes.c_double),
        ('y_bearing', ctypes.c_double),
        ('width', ctypes.c_double),
        ('height', ctypes.c_double),
        ('x_advance', ctypes.c_double),
        ('y_advance', ctypes.c_double),
    ]

cairo.cairo_image_surface_create_for_data.restype = ctypes.c_void_p
cairo.cairo_image_surface_create_for_data.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
]
cairo.cairo_create.restype = ctypes.c_void_p
cairo.cairo_create.argtypes = [ctypes.c_void_p]
cairo.cairo_destroy.argtypes = [ctypes.c_void_p]
cairo.cairo_surface_destroy.argtypes = [ctypes.c_void_p]
cairo.cairo_surface_flush.argtypes = [ctypes.c_void_p]

cairo.cairo_select_font_face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
cairo.cairo_set_font_size.argtypes = [ctypes.c_void_p, ctypes.c_double]
cairo.cairo_text_extents.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(cairo_text_extents_t)]
cairo.cairo_set_source_rgb.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double, ctypes.c_double]
cairo.cairo_set_source_rgba.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
cairo.cairo_set_line_width.argtypes = [ctypes.c_void_p, ctypes.c_double]
cairo.cairo_move_to.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double]
cairo.cairo_line_to.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double]
cairo.cairo_arc.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
cairo.cairo_new_sub_path.argtypes = [ctypes.c_void_p]
cairo.cairo_close_path.argtypes = [ctypes.c_void_p]
cairo.cairo_stroke.argtypes = [ctypes.c_void_p]
cairo.cairo_fill.argtypes = [ctypes.c_void_p]
cairo.cairo_paint.argtypes = [ctypes.c_void_p]
cairo.cairo_show_text.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# DRM Structures
class drm_mode_create_dumb(ctypes.Structure):
    _fields_ = [
        ("height", ctypes.c_uint32), ("width", ctypes.c_uint32),
        ("bpp", ctypes.c_uint32), ("flags", ctypes.c_uint32),
        ("handle", ctypes.c_uint32), ("pitch", ctypes.c_uint32),
        ("size", ctypes.c_uint64)
    ]

class drm_mode_map_dumb(ctypes.Structure):
    _fields_ = [
        ("handle", ctypes.c_uint32), ("pad", ctypes.c_uint32), ("offset", ctypes.c_uint64)
    ]

class drmModeModeInfo(ctypes.Structure):
    _fields_ = [
        ("clock", ctypes.c_uint32),
        ("hdisplay", ctypes.c_uint16), ("hsync_start", ctypes.c_uint16),
        ("hsync_end", ctypes.c_uint16), ("htotal", ctypes.c_uint16), ("hskew", ctypes.c_uint16),
        ("vdisplay", ctypes.c_uint16), ("vsync_start", ctypes.c_uint16),
        ("vsync_end", ctypes.c_uint16), ("vtotal", ctypes.c_uint16), ("vscan", ctypes.c_uint16),
        ("vrefresh", ctypes.c_uint32), ("flags", ctypes.c_uint32),
        ("type", ctypes.c_uint32), ("name", ctypes.c_char * 32)
    ]

class drmModeConnector(ctypes.Structure):
    _fields_ = [
        ("connector_id", ctypes.c_uint32), ("encoder_id", ctypes.c_uint32),
        ("connector_type", ctypes.c_uint32), ("connector_type_id", ctypes.c_uint32),
        ("connection", ctypes.c_uint32), ("mmWidth", ctypes.c_uint32), ("mmHeight", ctypes.c_uint32),
        ("subpixel", ctypes.c_uint32), ("count_modes", ctypes.c_int),
        ("modes", ctypes.POINTER(drmModeModeInfo))
    ]

libdrm.drmModeGetConnector.restype = ctypes.POINTER(drmModeConnector)
libdrm.drmModeGetConnector.argtypes = [ctypes.c_int, ctypes.c_uint32]
libdrm.drmSetMaster.argtypes = [ctypes.c_int]
libdrm.drmDropMaster.argtypes = [ctypes.c_int]
libdrm.drmModeObjectSetProperty.argtypes = [
    ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint64
]
libdrm.drmModeAddFB.argtypes = [
    ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint8,
    ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)
]
libdrm.drmModeSetCrtc.argtypes = [
    ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.POINTER(drmModeModeInfo)
]
libdrm.drmModeDirtyFB.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]

# ---------------------------------------------------------
# Display Initialization
# ---------------------------------------------------------
WIDTH, HEIGHT = 1080, 2340

# 1. Backlight
try:
    with open("/sys/class/backlight/panel0-backlight/brightness", "w") as f:
        f.write("1023\n")
    print("Backlight set to 1023", flush=True)
except Exception as e:
    print(f"Backlight warning: {e}", flush=True)

# 2. Open DRM device
fd = os.open("/dev/dri/card0", os.O_RDWR)
print(f"Opened /dev/dri/card0 (fd={fd})", flush=True)

# Set Master
ret_master = libdrm.drmSetMaster(fd)
print(f"drmSetMaster: {ret_master}", flush=True)

# Set autorefresh=1, DPMS=0 on Connector 29
libdrm.drmModeObjectSetProperty(fd, 29, 0xc0c0c0c0, 37, ctypes.c_uint64(1)) # autorefresh
libdrm.drmModeObjectSetProperty(fd, 29, 0xc0c0c0c0, 2, ctypes.c_uint64(0))   # DPMS On

# 3. Create Dumb Framebuffer
creq = drm_mode_create_dumb(HEIGHT, WIDTH, 32, 0, 0, 0, 0)
fcntl.ioctl(fd, 0xc02064b2, creq)
print(f"Dumb buffer created: handle={creq.handle}, pitch={creq.pitch}, size={creq.size}", flush=True)

fb_id = ctypes.c_uint32(0)
libdrm.drmModeAddFB(fd, WIDTH, HEIGHT, 24, 32, creq.pitch, creq.handle, ctypes.byref(fb_id))
print(f"Framebuffer registered: fb_id={fb_id.value}", flush=True)

# 4. Map Dumb Buffer
mreq = drm_mode_map_dumb(creq.handle, 0, 0)
fcntl.ioctl(fd, 0xc01064b3, mreq)
buf = mmap.mmap(fd, creq.size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=mreq.offset)
buf_arr = (ctypes.c_uint8 * creq.size).from_buffer(buf)

# 5. Modeset CRTC
conn = libdrm.drmModeGetConnector(fd, 29)
if conn and conn.contents.count_modes > 0:
    mode = conn.contents.modes[0]
    conn_id = ctypes.c_uint32(29)
    ret_crtc = libdrm.drmModeSetCrtc(fd, 105, fb_id.value, 0, 0, ctypes.byref(conn_id), 1, ctypes.byref(mode))
    print(f"drmModeSetCrtc: {ret_crtc} (mode={mode.hdisplay}x{mode.vdisplay}@{mode.vrefresh}Hz)", flush=True)
else:
    print("Warning: could not get modes for connector 29", flush=True)

# 6. Initialize Cairo Surface over DRM buffer
# CAIRO_FORMAT_RGB24 = 1
surf = cairo.cairo_image_surface_create_for_data(
    ctypes.cast(buf_arr, ctypes.c_void_p), 1, WIDTH, HEIGHT, creq.pitch
)
cr = cairo.cairo_create(surf)

def flush_screen():
    cairo.cairo_surface_flush(surf)
    try:
        libdrm.drmModeDirtyFB(fd, fb_id.value, None, 0)
    except Exception:
        pass

# ---------------------------------------------------------
# Cairo Drawing Primitives
# ---------------------------------------------------------
def draw_rounded_rect(cr, x, y, w, h, r):
    deg = math.pi / 180.0
    cairo.cairo_new_sub_path(cr)
    cairo.cairo_arc(cr, x + w - r, y + r, r, -90 * deg, 0 * deg)
    cairo.cairo_arc(cr, x + w - r, y + h - r, r, 0 * deg, 90 * deg)
    cairo.cairo_arc(cr, x + r, y + h - r, r, 90 * deg, 180 * deg)
    cairo.cairo_arc(cr, x + r, y + r, r, 180 * deg, 270 * deg)
    cairo.cairo_close_path(cr)

def draw_text_centered(cr, text_str, y, font_name, size, is_bold, r, g, b):
    cairo.cairo_select_font_face(cr, font_name.encode('utf-8'), 0, 1 if is_bold else 0)
    cairo.cairo_set_font_size(cr, size)
    cairo.cairo_set_source_rgb(cr, r, g, b)
    ext = cairo_text_extents_t()
    cairo.cairo_text_extents(cr, text_str.encode('utf-8'), ctypes.byref(ext))
    x = (WIDTH - ext.width) / 2.0 - ext.x_bearing
    cairo.cairo_move_to(cr, x, y)
    cairo.cairo_show_text(cr, text_str.encode('utf-8'))

def draw_emblem(cr, cx, cy):
    # 1. Hexagonal Outer Shield
    r_outer = 110.0
    cairo.cairo_set_line_width(cr, 4.0)
    cairo.cairo_set_source_rgb(cr, 0.0, 0.94, 1.0) # #00F0FF Cyan
    cairo.cairo_new_sub_path(cr)
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = cx + r_outer * math.cos(angle)
        py = cy + r_outer * math.sin(angle)
        if i == 0:
            cairo.cairo_move_to(cr, px, py)
        else:
            cairo.cairo_line_to(cr, px, py)
    cairo.cairo_close_path(cr)
    cairo.cairo_stroke(cr)

    # Inner decorative glow hexagon
    cairo.cairo_set_line_width(cr, 1.5)
    cairo.cairo_set_source_rgba(cr, 0.0, 0.94, 1.0, 0.35)
    cairo.cairo_new_sub_path(cr)
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = cx + (r_outer - 12.0) * math.cos(angle)
        py = cy + (r_outer - 12.0) * math.sin(angle)
        if i == 0:
            cairo.cairo_move_to(cr, px, py)
        else:
            cairo.cairo_line_to(cr, px, py)
    cairo.cairo_close_path(cr)
    cairo.cairo_stroke(cr)

    # 2. Central Dual-Boot Fork (Y shape)
    # Stem (Root)
    cairo.cairo_set_line_width(cr, 8.0)
    cairo.cairo_set_source_rgb(cr, 0.47, 0.16, 0.79) # #7928CA Violet
    cairo.cairo_move_to(cr, cx, cy - 10.0)
    cairo.cairo_line_to(cr, cx, cy + 60.0)
    cairo.cairo_stroke(cr)

    # Left Branch (Cyan)
    cairo.cairo_set_source_rgb(cr, 0.0, 0.94, 1.0) # #00F0FF
    cairo.cairo_move_to(cr, cx, cy - 10.0)
    cairo.cairo_line_to(cr, cx - 45.0, cy - 55.0)
    cairo.cairo_stroke(cr)

    # Right Branch (Magenta)
    cairo.cairo_set_source_rgb(cr, 1.0, 0.0, 0.48) # #FF007A
    cairo.cairo_move_to(cr, cx, cy - 10.0)
    cairo.cairo_line_to(cr, cx + 45.0, cy - 55.0)
    cairo.cairo_stroke(cr)

    # Glowing node circles
    for px, py, r_col, g_col, b_col in [
        (cx - 45.0, cy - 55.0, 0.0, 0.94, 1.0),
        (cx + 45.0, cy - 55.0, 1.0, 0.0, 0.48),
        (cx, cy + 60.0, 0.47, 0.16, 0.79),
        (cx, cy - 10.0, 1.0, 1.0, 1.0)
    ]:
        cairo.cairo_arc(cr, px, py, 7.0, 0, 2 * math.pi)
        cairo.cairo_set_source_rgb(cr, r_col, g_col, b_col)
        cairo.cairo_fill(cr)

OPTIONS = [
    ("1. Droidian GNU/Linux", "Default System  •  Halium 12/13 + Phosh Mobile Shell"),
    ("2. LineageOS Recovery", "Stock Failsafe Recovery  •  Root ADB Diagnostics"),
    ("3. Fastbootd Console",  "Hardware Bootloader  •  Fastbootd Flashing Mode")
]

def render_ui(selected_idx, countdown_sec, max_countdown=15, is_confirming=False):
    # Deep OLED True Black background
    cairo.cairo_set_source_rgb(cr, 0.03, 0.04, 0.06) # #080b10
    cairo.cairo_paint(cr)

    # 1. Vector Emblem
    draw_emblem(cr, WIDTH / 2.0, 380.0)

    # 2. Typography Header
    draw_text_centered(cr, "BRAMBLEGATE", 550.0, "Cantarell", 64.0, True, 0.0, 0.94, 1.0)
    draw_text_centered(cr, "STAGE-1 MOBILE GATEKEEPER", 605.0, "Cantarell", 26.0, False, 0.53, 0.57, 0.69)

    # 3. Device Badge Pill
    badge_w, badge_h = 440.0, 44.0
    badge_x = (WIDTH - badge_w) / 2.0
    badge_y = 640.0
    draw_rounded_rect(cr, badge_x, badge_y, badge_w, badge_h, 22.0)
    cairo.cairo_set_source_rgba(cr, 0.0, 1.0, 0.71, 0.08) # #00ffb4 tint
    cairo.cairo_fill(cr)
    draw_rounded_rect(cr, badge_x, badge_y, badge_w, badge_h, 22.0)
    cairo.cairo_set_line_width(cr, 1.5)
    cairo.cairo_set_source_rgba(cr, 0.0, 1.0, 0.71, 0.45)
    cairo.cairo_stroke(cr)
    draw_text_centered(cr, "PIXEL 4A 5G  •  SM7250 / ADRENO 620", 670.0, "Cantarell", 20.0, True, 0.0, 1.0, 0.71)

    # Divider Line
    cairo.cairo_set_line_width(cr, 1.0)
    cairo.cairo_set_source_rgba(cr, 0.15, 0.20, 0.30, 0.6)
    cairo.cairo_move_to(cr, 100.0, 725.0)
    cairo.cairo_line_to(cr, WIDTH - 100.0, 725.0)
    cairo.cairo_stroke(cr)

    # 4. Option Cards
    card_w = 880.0
    card_h = 145.0
    card_x = (WIDTH - card_w) / 2.0
    start_y = 770.0
    spacing = 175.0

    for idx, (title, desc) in enumerate(OPTIONS):
        cy = start_y + idx * spacing
        is_sel = (idx == selected_idx)

        draw_rounded_rect(cr, card_x, cy, card_w, card_h, 22.0)
        if is_sel:
            if is_confirming:
                # Flashing green/cyan confirm state
                cairo.cairo_set_source_rgba(cr, 0.0, 1.0, 0.71, 0.25)
                cairo.cairo_fill(cr)
                draw_rounded_rect(cr, card_x, cy, card_w, card_h, 22.0)
                cairo.cairo_set_line_width(cr, 3.5)
                cairo.cairo_set_source_rgb(cr, 0.0, 1.0, 0.71)
                cairo.cairo_stroke(cr)
            else:
                # Active Glowing Cyan Box
                cairo.cairo_set_source_rgba(cr, 0.0, 0.94, 1.0, 0.12)
                cairo.cairo_fill(cr)
                draw_rounded_rect(cr, card_x, cy, card_w, card_h, 22.0)
                cairo.cairo_set_line_width(cr, 3.0)
                cairo.cairo_set_source_rgb(cr, 0.0, 0.94, 1.0)
                cairo.cairo_stroke(cr)
        else:
            # Subtle Inactive Glass Card
            cairo.cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.03)
            cairo.cairo_fill(cr)
            draw_rounded_rect(cr, card_x, cy, card_w, card_h, 22.0)
            cairo.cairo_set_line_width(cr, 1.5)
            cairo.cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.10)
            cairo.cairo_stroke(cr)

        # Bullet indicator
        ind_cx = card_x + 55.0
        ind_cy = cy + card_h / 2.0
        if is_sel:
            cairo.cairo_arc(cr, ind_cx, ind_cy, 12.0, 0, 2 * math.pi)
            cairo.cairo_set_source_rgb(cr, 0.0, 0.94, 1.0)
            cairo.cairo_fill(cr)
            cairo.cairo_arc(cr, ind_cx, ind_cy, 5.0, 0, 2 * math.pi)
            cairo.cairo_set_source_rgb(cr, 1.0, 1.0, 1.0)
            cairo.cairo_fill(cr)
        else:
            cairo.cairo_arc(cr, ind_cx, ind_cy, 9.0, 0, 2 * math.pi)
            cairo.cairo_set_line_width(cr, 2.0)
            cairo.cairo_set_source_rgba(cr, 0.5, 0.6, 0.7, 0.5)
            cairo.cairo_stroke(cr)

        # Title text
        cairo.cairo_select_font_face(cr, b"Cantarell", 0, 1 if is_sel else 0)
        cairo.cairo_set_font_size(cr, 34.0)
        if is_sel:
            cairo.cairo_set_source_rgb(cr, 1.0, 1.0, 1.0)
        else:
            cairo.cairo_set_source_rgb(cr, 0.65, 0.72, 0.82)
        cairo.cairo_move_to(cr, card_x + 95.0, cy + 58.0)
        cairo.cairo_show_text(cr, title.encode('utf-8'))

        # Description text
        cairo.cairo_select_font_face(cr, b"Cantarell", 0, 0)
        cairo.cairo_set_font_size(cr, 22.0)
        if is_sel:
            cairo.cairo_set_source_rgb(cr, 0.40, 0.85, 1.0)
        else:
            cairo.cairo_set_source_rgb(cr, 0.42, 0.48, 0.58)
        cairo.cairo_move_to(cr, card_x + 95.0, cy + 105.0)
        cairo.cairo_show_text(cr, desc.encode('utf-8'))

    # 5. Countdown & Animated Progress Bar
    bar_y = 1380.0
    if is_confirming:
        draw_text_centered(cr, f"Booting: {OPTIONS[selected_idx][0]}...", bar_y, "Cantarell", 32.0, True, 0.0, 1.0, 0.71)
    elif is_paused:
        draw_text_centered(cr, "Auto-boot Paused (Manual Selection Active)", bar_y, "Cantarell", 26.0, True, 0.0, 0.94, 1.0)
    else:
        sec_text = f"Auto-booting in {countdown_sec}s (Default: Droidian)"
        draw_text_centered(cr, sec_text, bar_y, "Cantarell", 28.0, False, 1.0, 0.80, 0.0)

    # Progress bar
    bar_w = 880.0
    bar_h = 10.0
    bar_x = (WIDTH - bar_w) / 2.0
    draw_rounded_rect(cr, bar_x, bar_y + 30.0, bar_w, bar_h, 5.0)
    cairo.cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.12)
    cairo.cairo_fill(cr)

    if not is_paused:
        fill_pct = max(0.0, min(1.0, countdown_sec / float(max_countdown)))
        if fill_pct > 0.0:
            draw_rounded_rect(cr, bar_x, bar_y + 30.0, bar_w * fill_pct, bar_h, 5.0)
            cairo.cairo_set_source_rgb(cr, 0.0, 0.94, 1.0)
            cairo.cairo_fill(cr)
    else:
        # Full glowing cyan bar when paused
        draw_rounded_rect(cr, bar_x, bar_y + 30.0, bar_w, bar_h, 5.0)
        cairo.cairo_set_source_rgba(cr, 0.0, 0.94, 1.0, 0.5)
        cairo.cairo_fill(cr)

    # 6. Footer Controls & Status
    footer_y = 1680.0
    cairo.cairo_set_line_width(cr, 1.0)
    cairo.cairo_set_source_rgba(cr, 0.15, 0.20, 0.30, 0.6)
    cairo.cairo_move_to(cr, 100.0, footer_y)
    cairo.cairo_line_to(cr, WIDTH - 100.0, footer_y)
    cairo.cairo_stroke(cr)

    draw_text_centered(cr, "CONTROLS: [ Vol Up / Down: Navigate ]   [ Power: Select ]", footer_y + 50.0, "Cantarell", 22.0, True, 0.65, 0.72, 0.82)
    draw_text_centered(cr, "STATUS: USB NCM Active  •  IP: 10.15.19.82 (Root SSH)", footer_y + 90.0, "Cantarell", 20.0, False, 0.0, 0.94, 1.0)

    flush_screen()

# ---------------------------------------------------------
# Interactive Key Input Loop
# ---------------------------------------------------------
# event0: qpnp_pon -> VolDown (114), Power (116)
# event1: gpio-keys -> VolUp (115)
input_fds = {}
for ev_dev in ["/dev/input/event0", "/dev/input/event1"]:
    try:
        ifd = os.open(ev_dev, os.O_RDONLY | os.O_NONBLOCK)
        input_fds[ifd] = ev_dev
        print(f"Opened input device: {ev_dev} (fd={ifd})", flush=True)
    except Exception as e:
        print(f"Could not open input device {ev_dev}: {e}", flush=True)

selected_idx = 0
MAX_COUNTDOWN = 60
countdown = MAX_COUNTDOWN
is_paused = False
last_sec = time.time()
running = True
confirmed = False

print("🎨 Rendering initial UI...", flush=True)
render_ui(selected_idx, countdown, MAX_COUNTDOWN)
try:
    cairo.cairo_surface_write_to_png.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    cairo.cairo_surface_write_to_png(surf, b"/tmp/bramblegate_live.png")
    print("Saved preview to /tmp/bramblegate_live.png", flush=True)
except Exception as e:
    print(f"PNG preview warning: {e}", flush=True)

print("⚡ BrambleGate is LIVE! Listening for physical button events...", flush=True)

while running:
    # Non-blocking poll (50ms timeout)
    r_list, _, _ = select.select(list(input_fds.keys()), [], [], 0.05)
    for ifd in r_list:
        try:
            raw_data = os.read(ifd, 24 * 16)
            for chunk_idx in range(0, len(raw_data), 24):
                chunk = raw_data[chunk_idx:chunk_idx+24]
                if len(chunk) == 24:
                    sec, usec, etype, ecode, evalue = struct.unpack("qqHHi", chunk)
                    # EV_KEY = 1, evalue == 1 (key down)
                    if etype == 1 and evalue == 1:
                        print(f"Hardware Key Event: code={ecode}", flush=True)
                        if ecode == 115: # KEY_VOLUMEUP
                            selected_idx = (selected_idx - 1) % len(OPTIONS)
                            is_paused = True # Pause countdown on user interaction!
                            print(f"▲ KEY_VOLUMEUP -> Selected [{selected_idx}]: {OPTIONS[selected_idx][0]}", flush=True)
                            render_ui(selected_idx, countdown, MAX_COUNTDOWN)
                        elif ecode == 114: # KEY_VOLUMEDOWN
                            selected_idx = (selected_idx + 1) % len(OPTIONS)
                            is_paused = True # Pause countdown on user interaction!
                            print(f"▼ KEY_VOLUMEDOWN -> Selected [{selected_idx}]: {OPTIONS[selected_idx][0]}", flush=True)
                            render_ui(selected_idx, countdown, MAX_COUNTDOWN)
                        elif ecode == 116: # KEY_POWER
                            print(f"★ KEY_POWER -> Confirmed [{selected_idx}]: {OPTIONS[selected_idx][0]}", flush=True)
                            confirmed = True
                            running = False
                            break
        except Exception as e:
            pass

    if not running:
        break

    now = time.time()
    if now - last_sec >= 1.0:
        last_sec = now
        if not is_paused:
            countdown -= 1
            if countdown % 5 == 0 or countdown <= 5:
                print(f"⏱ Countdown: {countdown}s", flush=True)
            render_ui(selected_idx, max(0, countdown), MAX_COUNTDOWN)
            if countdown <= 0:
                print("Countdown expired. Auto-booting default...", flush=True)
                running = False
                break

# Show confirmation state
render_ui(selected_idx, 0, MAX_COUNTDOWN, is_confirming=True)
print(f"🎉 Final Target: {OPTIONS[selected_idx][0]}", flush=True)
time.sleep(1.5)

# ---------------------------------------------------------
# Clean Handover / Boot Target Execution
# ---------------------------------------------------------
# Close input fds
for ifd in input_fds:
    try:
        os.close(ifd)
    except Exception:
        pass

# Destroy Cairo and Surface
cairo.cairo_destroy(cr)
cairo.cairo_surface_destroy(surf)

if selected_idx == 0:
    # 1. Droidian GNU/Linux
    print("🚀 Handing over DRM to Droidian Phosh Desktop...", flush=True)
    # Release DRM Master so Phoc / Compositor can take over cleanly
    libdrm.drmDropMaster(fd)
    os.close(fd)
    # Ensure phosh or display manager is started
    os.system("echo 1234 | sudo -S systemctl start phosh.service &")
    sys.exit(0)

elif selected_idx == 1:
    # 2. LineageOS Recovery
    print("🚨 Rebooting to LineageOS Stock Recovery...", flush=True)
    libdrm.drmDropMaster(fd)
    os.close(fd)
    os.system("echo 1234 | sudo -S reboot recovery")
    sys.exit(0)

elif selected_idx == 2:
    # 3. Fastbootd Console
    print("⚡ Rebooting to Fastbootd Console...", flush=True)
    libdrm.drmDropMaster(fd)
    os.close(fd)
    os.system("echo 1234 | sudo -S reboot bootloader")
    sys.exit(0)
