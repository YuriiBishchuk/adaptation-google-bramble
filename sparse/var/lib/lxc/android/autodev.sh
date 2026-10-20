#!/bin/sh
cd "$LXC_ROOTFS_MOUNT/dev" || exit 1
ln -sf /dev/binderfs/binder binder
ln -sf /dev/binderfs/hwbinder hwbinder
ln -sf /dev/binderfs/vndbinder vndbinder
mkdir -p dri block
[ -e dri/card0 ] || mknod dri/card0 c 226 0
[ -e dri/renderD128 ] || mknod dri/renderD128 c 226 128
[ -e ion ] || mknod ion c 10 55
[ -e kgsl-3d0 ] || mknod kgsl-3d0 c 510 0
[ -e uio0 ] || mknod uio0 c 246 0
[ -e kmsg ] || mknod kmsg c 1 11
mknod sda2 b 8 2 2>/dev/null || true
mknod sdf1 b 8 81 2>/dev/null || true
mknod sdf2 b 8 82 2>/dev/null || true
mknod sdf3 b 8 83 2>/dev/null || true
mknod sdf4 b 8 84 2>/dev/null || true
mknod sdf5 b 8 85 2>/dev/null || true
chmod 660 sda* sdf* 2>/dev/null || true
chmod 666 binder hwbinder vndbinder ion kgsl-3d0 kmsg uio0 dri/* 2>/dev/null || true
mount --bind /dev/block "$LXC_ROOTFS_MOUNT/dev/block"
[ -e btpower ] || mknod btpower c 500 0
[ -e ttyHS0 ] || mknod ttyHS0 c 237 0
[ -e rfkill ] || mknod rfkill c 10 242
chmod 666 btpower ttyHS0 rfkill 2>/dev/null || true
[ -e null ] || mknod null c 1 3
[ -e zero ] || mknod zero c 1 5
[ -e full ] || mknod full c 1 7
[ -e random ] || mknod random c 1 8
[ -e urandom ] || mknod urandom c 1 9
[ -e ptmx ] || mknod ptmx c 5 2
chmod 666 null zero full random urandom ptmx 2>/dev/null || true
