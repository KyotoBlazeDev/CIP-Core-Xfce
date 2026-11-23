# SPDX-License-Identifier: MIT
# AMD firmware and X.Org are already in the Xfce image recipe.
IMAGE_PREINSTALL += "firmware-intel-graphics firmware-nvidia-graphics libgl1-mesa-dri mesa-vulkan-drivers mesa-va-drivers intel-media-va-driver mesa-utils vulkan-tools vainfo"
IMAGE_FULLNAME:append = "-broad-gpu"

XFCE_GPU_HOOK = "${LAYERDIR_cip-core}/recipes-core/images/files/cip-xfce-gpu-initramfs"
do_rootfs_install[file-checksums] += "${XFCE_GPU_HOOK}:True"
ROOTFS_CONFIGURE_COMMAND:append = " cip_xfce_install_gpu_hook"

cip_xfce_install_gpu_hook() {
    if [ "${DISTRO}" != cip-core-trixie ] || [ "${XFCE_GRUB_IMAGE}" != 1 ]; then
        bbfatal "Broad GPU Xfce requires the Trixie GRUB layout for its larger initramfs"
    fi
    run_privileged install -D -m 0755 "${XFCE_GPU_HOOK}" \
        "${ROOTFSDIR}/usr/share/initramfs-tools/hooks/cip-xfce-gpu"
}
