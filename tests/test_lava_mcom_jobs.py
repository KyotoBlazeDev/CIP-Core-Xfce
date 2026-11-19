#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests for the MCOM jobs and the IEC test block."""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import all_strings, lava_jobs  # noqa: E402


QEMU_TARGETS = ("qemu-amd64", "qemu-arm64", "qemu-arm")


def mcom_variables(iec_timeout="30"):
    return lava_jobs.build_variables("x86-uefi", "trixie", "br", iec_timeout)


def tests_of(job):
    return [a["test"] for a in job["actions"] if "test" in a]


class McomJobTests(unittest.TestCase):
    def test_mcom_iec_has_timeout(self):
        job = lava_jobs.build_job("IEC", "x86-uefi", mcom_variables("45"))
        self.assertEqual(tests_of(job)[0]["timeout"]["minutes"], 45)

    def test_mcom_job_name_contains_test_function(self):
        for test in ("IEC", "secure-boot", "swupdate"):
            with self.subTest(test=test):
                job = lava_jobs.build_job(test, "x86-uefi", mcom_variables())
                self.assertEqual(job["job_name"], f"mtda-mcom-{test}")
                self.assertEqual(job["device_type"], "mcom-mtda")

    def test_mcom_swupdate_updatestate_2(self):
        job = lava_jobs.build_job("swupdate", "x86-uefi", mcom_variables())
        text = "\n".join(all_strings(job))
        self.assertIn(") = 2 ]", text)

    def test_mcom_swupdate_deploys_swu_first(self):
        job = lava_jobs.build_job("swupdate", "x86-uefi", mcom_variables())
        deploys = [a["deploy"] for a in job["actions"] if "deploy" in a]
        self.assertEqual([d["to"] for d in deploys], ["downloads", "flasher"])
        self.assertTrue(deploys[0]["images"]["image"]["url"].endswith(
            "/br/x86-uefi/cip-core-image-security-cip-core-trixie-x86-uefi.swu"))
        self.assertIn("deploy", job["actions"][0])

    def test_mcom_overlay_renamed_for_swupdate_only(self):
        for test, overlay in (("swupdate", "overlay-2.1.1.4"),
                              ("IEC", "overlay-1.1.1.4"),
                              ("secure-boot", "overlay-1.1.1.4")):
            with self.subTest(test=test):
                job = lava_jobs.build_job(test, "x86-uefi", mcom_variables())
                text = "\n".join(all_strings(job))
                self.assertIn(f"--output {overlay}.tar.gz", text)

    def test_mcom_secure_boot_checks_kernel_start_message(self):
        job = lava_jobs.build_job("secure-boot", "x86-uefi", mcom_variables())
        boot = job["actions"][-1]["boot"]
        self.assertEqual(boot["parameters"]["kernel-start-message"],
                         "EFI stub: UEFI Secure Boot is enabled.")

    def test_mcom_has_no_firmware(self):
        for test in ("IEC", "secure-boot", "swupdate"):
            with self.subTest(test=test):
                job = lava_jobs.build_job(test, "x86-uefi", mcom_variables())
                self.assertNotIn("firmware.bin", "\n".join(all_strings(job)))

    def test_mcom_unsupported_test_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "kernel-panic", "--target", "x86-uefi",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", d])
            self.assertEqual(rc, 0)
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_main_writes_mcom_job(self):
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "IEC", "--target", "x86-uefi",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", d])
            self.assertEqual(rc, 0)
            out = pathlib.Path(d) / "IEC_x86-uefi.yml"
            self.assertEqual(lava_jobs.load_yaml(out)["device_type"], "mcom-mtda")

    def test_qemu_iec_has_test_block(self):
        for target in QEMU_TARGETS:
            with self.subTest(target=target):
                variables = lava_jobs.build_variables(target, "trixie", "br", "45")
                job = lava_jobs.build_job("IEC", target, variables)
                tests = tests_of(job)
                self.assertEqual(tests[-1]["timeout"]["minutes"], 45)
                self.assertEqual(tests[-1]["definitions"][0]["name"],
                                 "Security-Testcases")

if __name__ == "__main__":
    unittest.main()
