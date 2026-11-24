#!/bin/sh
# SPDX-License-Identifier: MIT
# Run inside the booted CIP-Core Xfce image.
set -eu

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

[ "$(uname -m)" = x86_64 ] || fail "Expected an x86-64 guest"
[ -d /sys/firmware/efi ] || fail "Guest did not boot using UEFI"

kernel=$(uname -r)
case "$kernel" in
    *cip*) ;;
    *) fail "Expected a CIP kernel, running $kernel" ;;
esac
if [ "$#" -gt 0 ] && [ "$kernel" != "$1" ]; then
    fail "Expected kernel $1, running $kernel"
fi

for package in xfce4-session lightdm; do
    status=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null) ||
        fail "$package is missing"
    [ "$status" = installed ] || fail "$package is not installed"
done

systemctl is-active --quiet graphical.target ||
    fail "systemd did not reach graphical.target"
systemctl is-active --quiet display-manager.service ||
    fail "The display manager is not active"

printf 'PASS: x86-64 UEFI, CIP kernel %s, Xfce packages, and active display manager\n' "$kernel"
