#
# CIP-Core Xfce Desktop Edition
# Debian Bookworm and Trixie / AMD64
#

require cip-core-image.inc

DESCRIPTION = "CIP-Core Xfce Desktop Edition"

IMAGE_INSTALL += "customizations"

# Use GRUB for the standard x86 Trixie desktop layout.
X86_UEFI_DEFAULT_WKS = "${@'xfce-trixie-grub.wks' if d.getVar('DISTRO') == 'cip-core-trixie' else 'x86_64-generic.wks'}"
XFCE_GRUB_IMAGE = "${@'1' if d.getVar('WKS_FILE') == 'xfce-trixie-grub.wks' else '0'}"
IMAGE_PREINSTALL += "${@'memtest86+' if d.getVar('XFCE_GRUB_IMAGE') == '1' else ''}"
IMAGER_INSTALL:wic:append = "${@' ' + d.getVar('GRUB_BOOTLOADER_INSTALL') if d.getVar('XFCE_GRUB_IMAGE') == '1' else ''}"
do_image_wic[file-checksums] += "${@d.getVar('LAYERDIR_cip-core') + '/wic/xfce-trixie-grub.cfg:True' if d.getVar('XFCE_GRUB_IMAGE') == '1' else ''}"

CIP_IMAGE_OPTIONS ?= ""
require ${CIP_IMAGE_OPTIONS}

IMAGE_PREINSTALL += " \
    xfce4 \
    xfce4-goodies \
    xfce4-power-manager \
    xfce4-power-manager-plugins \
    xfce4-session \
    pipewire-audio \
    pavucontrol \
    alsa-utils \
    tango-icon-theme \
    hicolor-icon-theme \
    adwaita-icon-theme \
    librsvg2-common \
    lightdm \
    upower \
    systemd-timesyncd \
    lightdm-gtk-greeter \
    xorg \
    dbus-x11 \
    dbus-user-session \
    network-manager \
    network-manager-gnome \
    sudo \
    curl \
    wget \
    git \
    nano \
    vim \
    htop \
    gvfs \
    thunar-archive-plugin \
    tumbler \
    tumbler-plugins-extra \
    ffmpegthumbnailer \
    file-roller \
    ufw \
    gufw \
    apparmor \
    apparmor-utils \
    ca-certificates \
    lm-sensors \
    smartmontools \
    pciutils \
    usbutils \
    eject \
    exfatprogs \
"

IMAGE_PREINSTALL += "${@bb.utils.contains('DISTRO', 'cip-core-trixie', 'xfce4-screensaver', '', d)}"

IMAGE_PREINSTALL += "${@bb.utils.contains('DISTRO', 'cip-core-trixie', 'evince blueman gnome-disk-utility chromium unattended-upgrades', '', d)}"

# Dedicated Xfce desktop user
USERS += "cipuser"
USER_cipuser[home] = "/home/cipuser"
USER_cipuser[shell] = "/bin/bash"
USER_cipuser[groups] = "audio video"
USER_cipuser[password] = "!"
USER_cipuser[flags] = "create-home"

# CIP-Core wireless and hardware support
IMAGE_PREINSTALL += " firmware-iwlwifi firmware-realtek firmware-atheros firmware-amd-graphics wireless-regdb wpasupplicant bluez rfkill nvme-cli iw "

IMAGE_INSTALL += "cip-core-installer"

IMAGE_PREINSTALL += "mokutil"

IMAGE_PREINSTALL += "iproute2"

# NVMe over Fabrics requires a matching kernel transport and site configuration.
CIP_XFCE_NVME_OF ?= "0"
ROOTFS_POSTPROCESS_COMMAND:append = " cip_xfce_configure_nvme_of"

cip_xfce_configure_nvme_of() {
    case "${CIP_XFCE_NVME_OF}" in
        1) return 0 ;;
        0) ;;
        *) bbfatal "CIP_XFCE_NVME_OF must be 0 or 1" ;;
    esac

    for unit in nvmf-autoconnect.service nvmefc-boot-connections.service nvmf-connect@.service; do
        run_privileged ln -sfn /dev/null "${ROOTFSDIR}/etc/systemd/system/$unit"
    done
}

# The CIP kernel trusts the upstream wireless regulatory database signers.
ROOTFS_POSTPROCESS_COMMAND:append = " cip_xfce_select_wireless_regdb"
cip_xfce_select_wireless_regdb() {
    run_privileged update-alternatives --root "${ROOTFSDIR}" \
        --set regulatory.db /lib/firmware/regulatory.db-upstream
}

# Only freshly built Xfce images should offer unauthenticated local enrollment.
ROOTFS_POSTPROCESS_COMMAND:append = " cip_xfce_seed_first_user"
cip_xfce_seed_first_user() {
    run_privileged install -d -m 0700 "${ROOTFSDIR}/var/lib/cip-core" || return 1
    for account in root cipuser; do
        run_in_chroot "${ROOTFSDIR}" /usr/sbin/usermod --password '!' "$account" || return 1
    done
    run_privileged install -m 0600 /dev/null "${ROOTFSDIR}/var/lib/cip-core/first-user-pending" || return 1
    printf '%s\n' admin-required |
        run_privileged tee "${ROOTFSDIR}/var/lib/cip-core/first-user-pending" >/dev/null || return 1
    if [ "${DISTRO}" = cip-core-trixie ]; then
        printf '%s\n' 'CIP-Core Xfce' |
            run_privileged tee "${ROOTFSDIR}/etc/issue" >/dev/null || return 1
    fi
}

CIP_XFCE_VIRTUALBOX ?= "0"
IMAGE_FULLNAME:append = "${@bb.utils.contains('CIP_XFCE_VIRTUALBOX', '1', '-virtualbox', '', d)}"
CIP_XFCE_OFFLINE_INSTALLER ?= "0"
IMAGE_PREINSTALL += "${@bb.utils.contains('CIP_XFCE_OFFLINE_INSTALLER', '1', 'bmap-tools', '', d)}"
IMAGE_FULLNAME:append = "${@bb.utils.contains('CIP_XFCE_OFFLINE_INSTALLER', '1', '-offline-installer', '', d)}"
ROOTFS_PACKAGE_SUFFIX = "${IMAGE_FULLNAME}"

# Debian's postinst initializes the LightDM home but not its shared data directory.
ROOTFS_POSTPROCESS_COMMAND:append = " cip_xfce_initialize_lightdm_data"
cip_xfce_initialize_lightdm_data() {
    printf '%s\n' 'd /var/lib/lightdm/data 0755 root root -' |
        run_privileged tee "${ROOTFSDIR}/usr/lib/tmpfiles.d/cip-core-lightdm.conf" >/dev/null
    run_privileged install -d -m 0755 -o 0 -g 0 "${ROOTFSDIR}/var/lib/lightdm/data"
}

IMAGE_PREINSTALL += "${@bb.utils.contains('CIP_XFCE_INTEL_AUDIO', '1', 'firmware-sof-signed alsa-ucm-conf', '', d)}"

# The base image includes development credentials and a root SSH policy.
ROOTFS_POSTPROCESS_COMMAND:append = " cip_xfce_mask_ssh"
cip_xfce_mask_ssh() {
    run_privileged install -d "${ROOTFSDIR}/etc/systemd/system"
    for unit in ssh.service ssh.socket ssh@.service; do
        run_privileged ln -sfn /dev/null "${ROOTFSDIR}/etc/systemd/system/$unit"
    done
}

# Built-in SOF needs the modular HDA codecs available during early probing.
ROOTFS_CONFIGURE_COMMAND:append = "${@bb.utils.contains('CIP_XFCE_INTEL_AUDIO', '1', ' cip_xfce_preload_hda_codecs', '', d)}"
cip_xfce_preload_hda_codecs() {
    run_privileged install -d -m 0755 "${ROOTFSDIR}/usr/share/initramfs-tools/modules.d"
    printf '%s\n' snd-hda-codec-realtek snd-hda-codec-hdmi |
        run_privileged tee "${ROOTFSDIR}/usr/share/initramfs-tools/modules.d/cip-xfce-hda" >/dev/null
}

# Mount the parent /dev before /dev/pts in the generated mount table.
image_configure_fstab:append() {
    awk '$2 == "/dev/pts" { pts = $0; next } { print } END { if (pts) print pts }' \
        "${IMAGE_ROOTFS}/etc/fstab" > "${WORKDIR}/xfce-fstab"
    run_privileged install -m 0644 "${WORKDIR}/xfce-fstab" "${IMAGE_ROOTFS}/etc/fstab"
}

CIP_XFCE_BROAD_GPU ?= "0"
require ${@bb.utils.contains("CIP_XFCE_BROAD_GPU", "1", "cip-xfce-broad-gpu.inc", "", d)}

# Broad Wi-Fi adds Trixie firmware for the MediaTek and Broadcom modules.
CIP_XFCE_BROAD_WIFI ?= "0"
IMAGE_PREINSTALL += "${@'firmware-mediatek firmware-brcm80211' if d.getVar('DISTRO') == 'cip-core-trixie' and d.getVar('CIP_XFCE_BROAD_WIFI') == '1' else ''}"
IMAGE_FULLNAME:append = "${@bb.utils.contains('CIP_XFCE_BROAD_WIFI', '1', '-broad-wifi', '', d)}"
