DESCRIPTION = "CIP-Core installer preflight utility"
MAINTAINER = "CIP-Core Project <root@localhost>"

DEBIAN_DEPENDS = "util-linux, mount, fdisk, xfce4-terminal, adduser, passwd, kbd"
SRC_URI = "file://cip-core-installer file://cip-core-preflight.desktop file://first-user-setup file://cip-core-first-user.service"
S = "${WORKDIR}/src"

inherit dpkg-raw

# Trixie packages install system units under /usr on merged-/usr systems.
CIP_FIRST_USER_UNIT_DIR = "${@'usr/lib/systemd/system' if d.getVar('DISTRO') == 'cip-core-trixie' else 'lib/systemd/system'}"

do_install() {
    install -d "${D}/usr/sbin" "${D}/usr/share/applications"
    install -d "${D}/usr/lib/cip-core" "${D}/${CIP_FIRST_USER_UNIT_DIR}"
    install -m 0755 "${WORKDIR}/first-user-setup" "${D}/usr/lib/cip-core/first-user-setup"
    install -m 0644 "${WORKDIR}/cip-core-first-user.service" "${D}/${CIP_FIRST_USER_UNIT_DIR}/cip-core-first-user.service"
    install -m 0755 "${WORKDIR}/cip-core-installer" "${D}/usr/sbin/cip-core-installer"
    install -m 0644 "${WORKDIR}/cip-core-preflight.desktop" "${D}/usr/share/applications/cip-core-preflight.desktop"
}

do_prepare_build:append() {
    cat >> "${S}/debian/rules" <<'RULES'

override_dh_installsystemd:
	dh_installsystemd --no-start
RULES
}
