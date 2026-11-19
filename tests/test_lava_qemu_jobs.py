#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests for the QEMU LAVA jobs and the generator command line."""

import pathlib
import sys
import re
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import all_strings, build, lava_jobs  # noqa: E402


def monitor(job):
    tests = [a["test"] for a in job["actions"] if "test" in a]
    return tests[-1]["monitors"][0]


def postprocess_steps(job):
    return job["actions"][1]["deploy"]["postprocess"]["docker"]["steps"]


class QemuJobTests(unittest.TestCase):
    def test_unsigned_kernel_amd64_monitors(self):
        mon = monitor(build("secure-boot-unsigned-kernel", "qemu-amd64"))
        self.assertEqual(mon["end"], "Access Denied")
        self.assertEqual(mon["start"], "Cannot load specified kernel image")
        self.assertEqual(mon["name"], "corrupted-linux-image")

    def test_unsigned_kernel_arm64_uses_vda_and_firmware(self):
        job = build("secure-boot-unsigned-kernel", "qemu-arm64")
        text = "\n".join(postprocess_steps(job))
        self.assertIn("/dev/vda2", text)
        self.assertNotIn("sda", text)
        deploys = [a["deploy"] for a in job["actions"] if "deploy" in a]
        self.assertIn("firmware", deploys[-1]["images"])
        self.assertEqual(monitor(job)["end"], "Application failed")

    def test_unsigned_bootloader_arm_uses_bootarm_efi(self):
        job = build("secure-boot-unsigned-bootloader", "qemu-arm")
        text = "\n".join(postprocess_steps(job))
        self.assertIn("bootarm.efi", text)
        self.assertNotIn("bootx64.efi", text)
        self.assertIn("/dev/vda1", text)

    def test_kernel_panic_updatestate_3_and_broken_swu(self):
        job = build("kernel-panic", "qemu-amd64")
        text = "\n".join(all_strings(job))
        self.assertIn(") = 3 ]", text)
        self.assertNotIn(") = 2 ]", text)
        self.assertIn("-broken.swu", text)
        self.assertIn("Kernel panic - not syncing: sysrq triggered crash", text)
        self.assertEqual(job["job_name"], "qemu-amd64 kernel-panic_rollback_testing")
        self.assertEqual(lava_jobs.output_filename("kernel-panic", "qemu-amd64"),
                         "kernel-panic.yml")

    def test_initramfs_crash_replaces_success_with_dd(self):
        text = "\n".join(all_strings(build("initramfs-crash", "qemu-amd64")))
        self.assertIn("dd if=/dev/urandom of=/dev/sda5 bs=512 count=1", text)
        self.assertNotIn("echo software update is successful!!", text)
        self.assertNotIn("-broken.swu", text)

    def test_mismatch_keys_swaps_ovmf_distro(self):
        for release, keys in (("trixie", "bookworm"), ("bookworm", "trixie")):
            with self.subTest(release=release):
                job = build("secure-boot-mismatch-keys", "qemu-amd64", release)
                text = "\n".join(all_strings(job))
                self.assertIn(f"{keys}-ovmf", text)
                self.assertNotIn(f"{release}-ovmf", text)
                self.assertEqual(postprocess_steps(job), ["echo 'no postprocess steps'"])

    def test_reboot_without_confirm_replaces_bg_setenv(self):
        job = build("swupdate-reboot-without-confirm", "qemu-arm")
        text = "\n".join(all_strings(job))
        self.assertNotIn("bg_setenv -c", text)
        self.assertIn("echo No update confirm", text)
        self.assertIn("kernel: C:BOOT0:linux.efi", text)

    def test_no_unreplaced_placeholders_for_all_tests(self):
        for test in lava_jobs.load_jobs():
            for target in lava_jobs.TARGETS:
                with self.subTest(test=test, target=target):
                    if not lava_jobs.is_supported(test, target):
                        continue
                    job = build(test, target)
                    text = yaml.safe_dump(job)
                    self.assertEqual(lava_jobs.find_unreplaced(text), [])
                    self.assertIsNone(re.search(r"#[A-Za-z_-]+#", text))

    def test_check_ustate_step_uses_updatestate(self):
        text = lava_jobs.fragment_path("test_swupdate_check_ustate").read_text()
        self.assertIn(") = ${updatestate} ]", text)
        self.assertFalse(hasattr(lava_jobs, "set_update_state"))

    def test_updatestate_only_set_in_values(self):
        for name, spec in lava_jobs.load_jobs().items():
            with self.subTest(test=name):
                self.assertNotIn("updatestate", spec)


if __name__ == "__main__":
    unittest.main()
