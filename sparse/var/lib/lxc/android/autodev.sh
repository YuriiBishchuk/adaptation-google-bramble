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
[ -e kmsg ] || mknod kmsg c 1 11
chmod 666 binder hwbinder vndbinder ion kgsl-3d0 kmsg dri/* 2>/dev/null || true
mount --bind /dev/block "$LXC_ROOTFS_MOUNT/dev/block"
