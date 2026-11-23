# CIP-Core Preflight 0.4

Run **CIP-Core Preflight** from the Xfce Applications Menu under **System**,
or run `/usr/sbin/cip-core-installer` from a terminal. The launcher holds the
terminal open after the report and runs as the signed-in user. Preflight reads
system and hardware information. It has no disk writes or elevation prompt.
The hardware report lists registered touchpads and wireless interfaces with
available driver names and device IDs. The wireless check uses local kernel
information and makes no network requests.

| Status | Meaning |
| --- | --- |
| PASS | A query completed, a requirement was met, or an optional device was absent. |
| WARN | An observed state warrants attention, such as disabled Secure Boot or failed services. |
| FAIL | A confirmed requirement failed, such as an architecture other than x86-64. |
| UNKNOWN | A tool, permission, interface, or successful probe result was unavailable. |

Exit codes are 0 for a clean run, 1 for any warning or unknown, 2 for a failure
(which takes precedence), and 64 for invalid arguments.

## First-boot local user setup

A freshly built Xfce image opens a text prompt on tty1 before starting the
desktop. Enter an unused username, then set a password in the standard
password prompt. The new account has a home directory and ordinary user
permissions. The completed setup is recorded on that booted image.

Press Enter without a username to defer setup and continue booting. The
username prompt waits up to 45 seconds and the entire service has a
five-minute limit. If setup is deferred, it is offered at the next boot.
An existing account, group or home directory is never reused. If the
password prompt fails after account creation, the account remains without a
usable password. A local administrator can inspect it and set its password.

The prompt requires physical or virtual console access and is intended for
operator-controlled enrollment on a fresh image. It preserves the existing
development accounts. The Preflight launcher and CLI remain read-only.

## Read-only installation plan

Preflight lists whole disks and their partitions, filesystem types, free space
inside mounted filesystems, removable flags, transports and mount points.
It resolves the running root by kernel device number and marks the associated
disk and disks with mounted boot filesystems as protected. When root ancestry
or mount/swap state is ambiguous, target recommendations are withheld.

An EFI System Partition is identified by partition type. The running OS is
reported separately. Other OS evidence can come from readable Linux release
metadata or Windows system files on already mounted filesystems. An EFI
partition or a filesystem type alone cannot identify an OS. Preflight does
not mount filesystems, request elevated privileges or contact the network.

A whole-disk WIC requires a dedicated 512-byte logical-sector disk that fits
the exact image. Preflight uses 4 GiB as a planning minimum for this build
family. A disk with no detected partitions or signatures is only a candidate
for manual review. Existing partitions, signatures, mounts and active swap
require review. Unallocated partition-table regions are displayed only when
the session can read the layout. Filesystem free space is different from
unallocated disk space.

> [!WARNING]
> Writing a whole-disk WIC replaces the target's partition table. Installing
> into unallocated space on a disk with existing partitions requires a
> partition-based installer.

For the Yoga example, Preflight should protect the booted USB and flag the
internal SSD with existing EFI and Arch partitions even if it has 100 GiB
unallocated. Preflight itself is read-only.

## NVMe over Fabrics

Bookworm's nvme-cli package enables nvmf-autoconnect.service at installation.
Its vendor unit attempts to load nvme-fabrics when either of the two
discovery configuration files is missing. The stock Xfce kernel ships the
PCIe NVMe drivers. The Xfce image masks the NVMe-oF boot and event-driven
connection units by default, while retaining nvme-cli for local devices.

For a dedicated NVMe-oF build, provide a kernel with the intended host
transport and configure the site's discovery endpoint and access credentials.
Set `CIP_XFCE_NVME_OF = "1"` via a site KAS overlay's `local_conf_header` to
omit the image masks. Validate that the required host and transport modules
exist for that kernel and check the vendor unit conditions against the site's
chosen discovery configuration. The stock Xfce kernel lacks NVMe-oF support.

## Production credentials

> [!IMPORTANT]
> The Xfce recipe and base kas profile include development credentials. Every
> image that retains the shared password hash has the same exposure if the
> password is recovered. See the Trixie account policy below.

For production, use a site overlay that ships root and cipuser with locked
passwords. Verify the resulting account state and use trusted per-device
enrollment to provision named administrator accounts with individual SSH public
keys or unique credentials. Deliver credentials through a restricted provisioning
channel and keep them out of source, build variables, logs, and shared images.
Rotate any development credentials used on devices and verify that the
production SSH and graphical login policies enforce the intended access.

### Fresh Trixie images

The Xfce image replaces the root and cipuser password hashes with locked
entries. First-user setup on tty1 creates a named administrator with sudo
access once a password has been set. If the username prompt times out, reboot
to try again. If setup created an account but failed before finishing, boot
trusted SystemRescue media, identify the installed CIP-ROOT by label and
filesystem, and mount it read-write. For an existing named account, use
`chroot /mnt/cip-root passwd USER` and
`chroot /mnt/cip-root usermod -aG sudo USER`, substituting the account name.
Unmount the filesystem before rebooting. Check `sudo whoami` from a new login.

### Remote access

The Xfce build masks the OpenSSH service, socket and instance template. Local
console and graphical login remain available. Before enabling SSH on a deployed
system, replace or lock shared credentials, remove the inherited root-login
override, and configure a named administrator with an SSH public key. Check
the effective policy with `sshd -T` before unmasking and enabling the service.
On an existing installation, run `sudo systemctl mask --now ssh.service
ssh.socket ssh@.service` from the local console to apply the same default.

## Verification

From the repository root:

```sh
pkg=recipes-support/cip-core-installer
sh -n "$pkg/files/cip-core-installer"
sh -n "$pkg/tests/test-preflight.sh"
sh "$pkg/tests/test-preflight.sh"
desktop-file-validate "$pkg/files/cip-core-preflight.desktop"
./kas-container build kas-cip.yml:kas-xfce.yml
```

After booting the image, check the launcher from an ordinary Xfce session.
Confirm the terminal stays open and Preflight reports local disks under Storage.
Check the default systemd policy and boot journal:

```sh
systemctl is-enabled nvmf-autoconnect.service nvmefc-boot-connections.service nvmf-connect@.service
journalctl -b -u nvmf-autoconnect.service --no-pager
lsblk -o NAME,SIZE,TYPE,TRAN
```
