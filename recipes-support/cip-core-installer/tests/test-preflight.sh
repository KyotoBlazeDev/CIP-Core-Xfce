#!/bin/sh
set -eu

script=$(CDPATH='' cd -- "$(dirname -- "$0")/../files" && pwd)/cip-core-installer
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
trap 'exit 1' HUP INT TERM
bin=$fixture/bin
sysfs=$fixture/sys
mkdir -p "$bin" "$sysfs/firmware/efi" "$sysfs/class/power_supply"
export CIP_PREFLIGHT_SYSFS="$sysfs"

stub() {
    printf '#!/bin/sh\n%s\n' "$2" > "$bin/$1"
    chmod +x "$bin/$1"
}

run() {
    expected=$1
    shift
    actual=0
    PATH="$bin" /bin/sh "$script" "$@" > "$fixture/output" 2>&1 || actual=$?
    if [ "$actual" != "$expected" ]; then
        printf 'Expected exit %s, got %s\n' "$expected" "$actual" >&2
        cat "$fixture/output" >&2
        exit 1
    fi
}

expect() {
    if ! grep -Fq -- "$1" "$fixture/output"; then
        printf 'Missing output: %s\n' "$1" >&2
        cat "$fixture/output" >&2
        exit 1
    fi
}

for command in cat lscpu free lsblk lspci lsusb ip systemctl; do
    stub "$command" 'exit 0'
done
stub uname 'echo x86_64'
stub mokutil 'echo "SecureBoot enabled"'
stub udevadm 'echo ID_INPUT_TOUCHPAD=1'
stub readlink 'exec /usr/bin/readlink "$@"'
mkdir -p "$sysfs/class/input/event0/device/id" "$sysfs/class/net/wlan0/wireless" "$sysfs/class/net/wlan0/device"
printf "%s\n" "Fixture Touchpad" > "$sysfs/class/input/event0/device/name"
printf "%s\n" 04f3 > "$sysfs/class/input/event0/device/id/vendor"
printf "%s\n" 317c > "$sysfs/class/input/event0/device/id/product"
ln -s /drivers/hid-multitouch "$sysfs/class/input/event0/device/driver"
ln -s /drivers/iwlwifi "$sysfs/class/net/wlan0/device/driver"

stub awk 'exec /usr/bin/awk "$@"'
stub findmnt '
case "$*" in
    "-rn -o MAJ:MIN,FSTYPE --mountpoint /")
        case "${STORAGE_LAYOUT:-usb}" in
            nvme) echo "259:2 ext4" ;;
            ambiguous) echo "0:42 overlay" ;;
            shared) echo "253:0 ext4" ;;
            *) echo "8:2 ext4" ;;
        esac ;;
    "-rn -o MAJ:MIN,TARGET")
        case "${STORAGE_LAYOUT:-usb}" in
            nvme) printf "259:2 /\n259:1 /boot\n" ;;
            ambiguous) echo "0:42 /" ;;
            shared) echo "253:0 /" ;;
            *) printf "8:2 /\n8:1 /boot\n" ;;
        esac ;;
    *) exit 1 ;;
esac'
stub swapon '[ "${STORAGE_LAYOUT:-usb}" != swapfail ]'
stub wipefs 'exit 0'
stub sfdisk '
[ "${STORAGE_LAYOUT:-usb}" != geometryfail ] || exit 1
printf "Start End Sectors Size\n1000 2000 1001 512512\n"'
stub lsblk '
case "$*" in
    "-o NAME,SIZE,TYPE,FSTYPE,FSAVAIL,MODEL,TRAN,RM,MOUNTPOINTS")
        echo "fixture inventory" ;;
    "-bdnro PATH,MAJ:MIN,TYPE,SIZE,RO,LOG-SEC")
        [ "${STORAGE_LAYOUT:-usb}" != missing ] || exit 0
        printf "/dev/sda 8:0 disk 32000000000 0 512\n/dev/nvme0n1 259:0 disk 1000000000000 0 512\n"
        if [ "${STORAGE_LAYOUT:-usb}" != baseline ]; then
            printf "/dev/sdb 8:16 disk 64000000000 0 512\n"
        fi ;;
    "-nro MAJ:MIN,TYPE -- /dev/sda")
        printf "8:0 disk\n8:1 part\n8:2 part\n"
        if [ "${STORAGE_LAYOUT:-usb}" = shared ]; then echo "253:0 crypt"; fi ;;
    "-nro MAJ:MIN,TYPE -- /dev/nvme0n1")
        [ "${STORAGE_LAYOUT:-usb}" != topologyfail ] || exit 1
        printf "259:0 disk\n"
        if [ "${STORAGE_LAYOUT:-usb}" != baseline ]; then
            printf "259:1 part\n259:2 part\n"
        fi
        if [ "${STORAGE_LAYOUT:-usb}" = shared ]; then echo "253:0 crypt"; fi ;;
    "-nro MAJ:MIN,TYPE -- /dev/sdb") echo "8:16 disk" ;;
    "-nro PATH,PARTTYPE -- /dev/sda") echo "/dev/sda1 c12a7328-f81f-11d2-ba4b-00a0c93ec93b" ;;
    "-nro PATH,PARTTYPE -- /dev/nvme0n1") echo "/dev/nvme0n1p1 C12A7328-F81F-11D2-BA4B-00A0C93EC93B" ;;
    "-nro PATH,PARTTYPE -- /dev/sdb") echo "/dev/sdb" ;;
    *) exit 1 ;;
esac'
export STORAGE_LAYOUT=baseline

run 0 --version
expect 'CIP-Core Preflight 0.4'
run 0 --help
expect 'Usage:'
run 64 --unknown
run 64 --help --version

run 0
expect '[PASS] TPM - Optional interface is absent'
expect '[PASS] Power supplies - No devices exposed by the optional interface'
expect 'PASS=15 WARN=0 FAIL=0 UNKNOWN=0'
expect "[PASS] Touchpad - Touchpad registered"
expect "Fixture Touchpad (driver: hid-multitouch)"
expect "ID 04f3:317c"
expect "[PASS] Wi-Fi - Wireless interface registered"
expect "wlan0 (driver: iwlwifi)"

stub udevadm 'exit 1'
run 1
expect "[UNKNOWN] Touchpad - Some input events could not be classified"
stub udevadm 'echo ID_INPUT_MOUSE=1'
rmdir "$sysfs/class/net/wlan0/wireless"
run 1
expect "[WARN] Touchpad - No touchpad registered"
expect "[WARN] Wi-Fi - No wireless interface registered"
stub udevadm 'echo ID_INPUT_TOUCHPAD=1'
mkdir "$sysfs/class/net/wlan0/wireless"

mkdir -p "$sysfs/class/tpm/tpm0" "$sysfs/class/power_supply/BAT0"
run 0
expect '[PASS] TPM - Interface detected'
expect '[PASS] Power supplies - Interface detected'

STORAGE_LAYOUT=usb run 1
expect '[PASS] Boot disk - Root device 8:2; PROTECTED: /dev/sda'
expect 'EFI System Partition: /dev/nvme0n1p1'
expect '[WARN] Storage target - /dev/nvme0n1: existing partitions'
expect 'Unallocated partition-table space:'
expect 'Candidate for manual review'
STORAGE_LAYOUT=nvme run 1
expect '[PASS] Boot disk - Root device 259:2; PROTECTED: /dev/nvme0n1'
STORAGE_LAYOUT=missing run 1
expect '[UNKNOWN] Storage - No whole disks found'
STORAGE_LAYOUT=ambiguous run 1
expect '[UNKNOWN] Boot disk - Root device or parent disk is ambiguous'
expect 'Withheld: root topology or storage activity could not be verified.'
if grep -Fq "Candidate for manual review" "$fixture/output"; then
    echo "Ambiguous root exposed an installation candidate" >&2
    exit 1
fi
STORAGE_LAYOUT=shared run 1
expect 'PROTECTED (possible root disks): /dev/sda /dev/nvme0n1'
expect 'Withheld: root topology or storage activity could not be verified.'
STORAGE_LAYOUT=topologyfail run 1
expect '[UNKNOWN] Storage target - /dev/nvme0n1: topology unavailable'
STORAGE_LAYOUT=geometryfail run 1
expect '[UNKNOWN] Unallocated space - /dev/nvme0n1'
STORAGE_LAYOUT=swapfail run 1
expect '[UNKNOWN] Storage activity'
expect 'Withheld: root topology or storage activity could not be verified.'

stub mokutil 'echo "SecureBoot disabled"'
stub systemctl 'echo "example.service loaded failed failed"'
run 1
expect '[WARN] Secure Boot - Disabled'
expect '[WARN] Failed services - systemd reported failed units'

stub mokutil 'echo "permission denied" >&2; exit 1'
stub systemctl 'exit 1'
stub lsblk 'exit 32'
rm "$bin/lspci"
run 1
expect '[UNKNOWN] Secure Boot - EFI variables could not be read'
expect '[UNKNOWN] Failed services - systemd could not be queried'
expect '[UNKNOWN] Storage - lsblk could not enumerate storage'
expect '[UNKNOWN] PCI - lspci is unavailable'

rm "$bin/mokutil"
run 1
expect '[UNKNOWN] Secure Boot - mokutil is unavailable'

rmdir "$sysfs/firmware/efi"
run 1
expect '[WARN] Boot mode - EFI interface is absent'
expect '[UNKNOWN] Secure Boot - EFI interface is absent'

stub uname 'echo aarch64'
run 2
expect '[FAIL] Architecture - This image requires x86-64'

rm "$bin/uname"
rmdir "$sysfs/firmware"
CIP_PREFLIGHT_SYSFS="$fixture/missing" run 1
expect '[UNKNOWN] Architecture'
expect '[UNKNOWN] Boot mode - Firmware interface is unavailable'
expect '[UNKNOWN] TPM - sysfs class directory is unavailable'

printf '%s\n' 'Preflight fixtures passed'
