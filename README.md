# 📱 Droidian Adaptation for Google Pixel 4a (5G) (`bramble`)

Community device adaptation metapackage and hardware configurations for running **Droidian GNU/Linux** (Debian Trixie / Next) natively on the **Google Pixel 4a (5G)** (`bramble` / Qualcomm Snapdragon 765G SM7250).

---

## 🚀 Key Features

* **⚡ Native 60 FPS GPU Acceleration**: Powered by custom **Mesa Turnip Vulkan 1.3** with downstream Qualcomm kernel driver (`/dev/kgsl-3d0`). Phoc Wayland compositor runs on `WLR_RENDERER=vulkan` and Phosh GTK4 shell on `GSK_RENDERER=ngl`.
* **🛡️ Protected Driver Stack**: Automated `apt-mark hold mesa-vulkan-drivers` in packaging prevents generic Debian upstream packages from breaking KGSL support during `apt upgrade`.
* **🔒 Clean DRM Master Arbitration**: Masks `android-composer.service` to prevent AIDL HWC2.4 contention on `/dev/dri/card0`.
* **🎨 BrambleGate Mobile Boot Manager**: Interactive Cairo 2D OLED Stage-1 bootloader integrated into systemd with hardware button navigation.
* **🔧 Dynamic Partition Vendor Firmware Auto-Mount**: Automatic parsing of `super` (`sda18`) to mount Android vendor partition (`dm-3`) on host root for Adreno 620 GPU microcode (`a650_sqe.fw`).

---

## 📊 Hardware Status

| Component | Status | Implementation Details |
|---|---|---|
| **Display** | ✅ **Working (60 FPS)** | OLED 1080x2340 @ 61.66 Hz, DRM KMS modesetting via `/dev/dri/card0` |
| **GPU Acceleration** | ✅ **Working** | Mesa 27.0.0-devel Turnip Vulkan 1.3 via `/dev/kgsl-3d0` |
| **Touchscreen** | ✅ **Working** | Focaltech FT5446 (`/dev/input/event2`) |
| **Desktop Shell** | ✅ **Working** | Phosh (GTK4 `ngl`) + Phoc (`vulkan`) |
| **Hardware Keys** | ✅ **Working** | Power, Volume Up, Volume Down (`event0`, `event1`) |
| **Stage-1 Bootloader** | ✅ **Working** | BrambleGate vector boot manager |
| **Networking** | ✅ **Working** | USB NCM gadget (`10.15.19.82` / `172.16.42.1`) + SSH |
| **Wi-Fi / BT / Audio** | ⏳ **In Progress** | LXC Android HAL binder bridge |

---

## 📦 Building the Package

This repository includes an automated GitHub Actions CI/CD workflow that builds `.deb` packages for ARM64 on every push and creates GitHub Releases on tags.

### Manual Local Build (via Docker/Podman):
```bash
docker run --rm --platform linux/arm64 \
  -v "$PWD:/build" -w /build \
  debian:trixie-slim /bin/bash -c "
    apt-get update && \
    apt-get install -y build-essential debhelper dpkg-dev && \
    dpkg-buildpackage -us -uc -b
  "
```

The output packages will be created in the parent directory:
* `adaptation-google-bramble-configs_<version>_arm64.deb`
* `adaptation-google-bramble_<version>_arm64.deb`

---

## 📲 Installation on Device

Transfer the `.deb` files to your Pixel 4a 5G running Droidian:
```bash
scp output/*.deb droidian@10.15.19.82:/tmp/
ssh droidian@10.15.19.82 "sudo dpkg -i /tmp/*.deb"
```

---

## 📜 License & Credits

* Maintained by [Yurii Bishchuk](https://github.com/YuriiBishchuk).
* Packaging configuration under GPL-3.0-or-later.
