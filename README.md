# CIP-Core Xfce Edition

CIP-Core Xfce Edition is a downstream desktop image for **x86-64 UEFI PCs**
built on Debian Trixie, Xfce, Isar, and the Linux CIP kernel. The image includes
desktop graphics and Wi-Fi profiles, first-boot enrollment, and recovery tools.

> [!NOTE]
> Trixie is the development baseline. The Linux 6.12-CIP image builds from
> the GitHub checkout. Hardware validation of that exact WIC is pending,
> and the Forky profile is experimental.

## Build the Trixie Xfce image

Use a Linux build environment with Git and Docker or Podman. The example
selects Linux 6.12.111-cip32 and the broad GPU and Wi-Fi profiles.

```sh
git clone https://github.com/KyotoBlazeDev/CIP-Core-Xfce.git
cd CIP-Core-Xfce
./kas-container --isar-privileged build \
  kas-cip.yml:kas/board/x86-uefi.yml:kas-xfce-broad-gpu.yml:kas-xfce-broad-wifi.yml:kas-xfce-cip32.yml
```

The build writes its artifacts to `build/tmp/deploy/images/x86-uefi/`.

| Artifact | Purpose |
| --- | --- |
| `.wic` | Bootable disk image for USB or VM testing |
| `.wic.spdx.json` | SPDX software bill of materials for the matching WIC |
| `.wic.manifest` | Package and version list for the matching WIC |

## Build validation

On November 23, 2026, all 127 BitBake tasks passed from GitHub source
commit [9344123](https://github.com/KyotoBlazeDev/CIP-Core-Xfce/commit/9344123bf5f96163b62a36d1572fa88de13248ce).
The build produced the Trixie x86-UEFI WIC and its matching SPDX 2.3 report.
The WIC manifest lists the kernel package version
`6.12.111-cip32+r0+yoga1+gpu1+wifi1`.

## Boot and test

> [!WARNING]
> Flashing the WIC overwrites the selected drive. Verify the target by
> model and capacity before writing. To evaluate the desktop, boot a
> dedicated USB stick and leave the internal drive alone.

Boot in UEFI mode. Complete first-user setup at the console, then sign in
to Xfce. See the [Preflight and installer guide](recipes-support/cip-core-installer/README.md)
for enrollment and storage checks.

The ThinkPad L15 Gen 2 AMD passed AMDGPU and Wi-Fi checks on the 6.1 build.
The Yoga Slim 7 Carbon passed touchpad and Iris Xe checks on the 6.12 test
kernel. These results apply to those builds. The RTX 5060 was detected over
PCI, but Nouveau on the tested 6.1 image could not initialize it. See the
[GPU kernel configuration](recipes-kernel/linux/files/xfce-broad-gpu.cfg) for enabled drivers.

For changes and bug reports, see [Contributing](CONTRIBUTING.md). The
[upstream Isar CIP-Core project](https://gitlab.com/cip-project/cip-core/isar-cip-core)
maintains the generic image layer.

## CIP Core Generic Profile demonstration and test images

This generates bootable images for virtual and physical targets using the
Debian package set of the [CIP](https://www.cip-project.org/) Core Generic
Profile and the CIP SLTS kernel.

The build system used for this is [Isar](https://github.com/ilbers/isar), an
image generator that assembles Debian binaries or builds individual packages
from scratch.

### Building Target Images

Install docker or podman. For true unprivileged builds, podman is recommended.
See [kas documentation](https://kas.readthedocs.io/en/latest/userguide/kas-container.html)
for more details.

Open up the image configuration menu and select the desired target and its
options:

    ./kas-container menu

You can directly start the build from the menu.

If you prefer selecting the configuration via the command line, this builds
the BeagleBone Black target image with real-time kernel, e.g.:

    ./kas-container build kas-cip.yml:kas/board/bbb.yml:kas/opt/rt.yml


### Running Target Images

When having built a virtual QEMU target image, this can be started directly.
Run, e.g.,

    ./start-qemu.sh x86

when having built a QEMU AMD64 image. Using the image configuration menu will
initialize variables used by start-qemu.sh with fitting defaults. Otherwise, a
security image for QEMU can be started like this:

    TARGET_IMAGE=cip-core-image-security ./start-qemu.sh x86

For using the Firmware TPM / UEFI key storage option with a virtual target
(`kas/opt/ftpm-stmm.yml`), QEMU v10.2.0 or newer is required.

Physical targets will generate ready-to-boot images under
`build/tmp/deploy/images/`. To flash, e.g., the BeagleBone Black image to an SD
card, run

    dd if=build/tmp/deploy/images/bbb/cip-core-image-cip-core-buster-bbb.wic \
       of=/dev/<medium-device> bs=1M status=progress

or via bmap-tools

    bmaptool copy build/tmp/deploy/images/bbb/cip-core-image-cip-core-buster-bbb.wic /dev/<medium-device>

### Xfce boot smoke test

Boot the Xfce WIC image with UEFI in a virtual machine. Confirm that the login
screen appears, then copy `tests/xfce-boot-smoke.sh` into the guest and run
`sh xfce-boot-smoke.sh` from a guest terminal. It checks UEFI, the running CIP
kernel, the Xfce session and LightDM packages, and the active display manager.
Pass an expected `uname -r` value as the first argument to check an exact
kernel release.

### Documentation

The following topics are in separate READMEs:
 - [Secureboot](./doc/README.secureboot.md)
 - [Update process with SWUpdate](./doc/README.swupdate.md)
 - [Update and Secure boot signing](./doc/README.signing.md)
 - [Encryption with TPM2](./doc/README.tpm2.encryption.md)
 - [Factory-reset](./doc/README.factory-reset.md)
 - [Release policy](./doc/README_version-release-policy.md)

### Community Resources

Mailing list:

 - cip-dev@lists.cip-project.org

 - Subscription:
   - cip-dev+subscribe@lists.cip-project.org
   - https://lists.cip-project.org/g/cip-dev

 - Archives:
   - https://lore.kernel.org/cip-dev/
   - https://lists.cip-project.org/g/cip-dev

Continuous integration:

  - https://gitlab.com/cip-project/cip-core/isar-cip-core/-/pipelines

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution process.


### Credits

- The Civil Infrastructure Platform (CIP) and the
  [ISAR CIP Core contributors](https://gitlab.com/cip-project/cip-core/isar-cip-core/-/graphs/master) maintain the upstream recipes and build configurations this project builds on.
- The [Isar contributors](https://github.com/ilbers/isar/graphs/contributors)
  develop the image build system.
- The [Debian](https://www.debian.org/) and
  [Xfce](https://www.xfce.org/) communities provide the package base and desktop
  environment.
- The [Linux kernel community](https://www.kernel.org/) and CIP kernel maintainers provide the kernel foundation, hardware support, security fixes, and long-term maintenance.
- [KyotoBlazeDev](https://github.com/KyotoBlazeDev) contributed the Xfce image
  recipes, hardware profiles, installer integration, and build documentation in
  this repository.

Thanks to all contributors and maintainers of isar-cip-core! Contributions to downstream are welcome and greatly appreciated! For upstream, please report any bugs or merges through the official Civil Infrastructure Platform (CIP) mailing list and GitLab Work (Issues).

### Side Notes
All source code is licensed under the MIT license, which allows our work to progress. The goal is to power embedded industrial PCs and portable industrial PCs. Check the COPYING file for more details at the backup-xfce-recipes.

### License

Unless otherwise stated in the respective file, files in this layer are
provided under the MIT license; see COPYING file. Patches (files ending with
.patch) are licensed according to their target project and file, typically
GPLv2.
