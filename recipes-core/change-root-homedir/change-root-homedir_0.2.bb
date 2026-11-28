#
# CIP Core, generic profile
#
# Copyright (c) Siemens AG, 2021-2025
#
# Authors:
#  Henning Schild <henning.schild@siemens.com>
#
# SPDX-License-Identifier: MIT

inherit dpkg-raw

MAINTAINER = "cip-dev <cip-dev@lists.cip-project.org>"

DESCRIPTION = "Move roots homedir to /home for read-only rootfs"

SRC_URI = "file://postinst"
SRC_URI:append:trixie = " file://provision.conf"

do_install:append:trixie() {
    install -D -m 0644 "${WORKDIR}/provision.conf" "${D}/etc/tmpfiles.d/provision.conf"
}

do_prepare_build:append:separate-home-part() {
    # The provision.conf override already creates /home/root on trixie.
    if [ ! -f "${WORKDIR}/provision.conf" ]; then
        echo "d /home/root 0700 root root -" > "${S}/debian/${BPN}.tmpfiles"
    fi
}
