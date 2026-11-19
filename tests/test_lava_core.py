#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests for variable building, firmware and job writing."""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import lava_jobs  # noqa: E402


class CoreTests(unittest.TestCase):
    def test_build_variables_context_arch(self):
        v = lava_jobs.build_variables("qemu-arm64", "trixie", "next", "30")
        self.assertEqual(v["context_architecture"], "arm64")

    def test_build_variables_imageargs_amd64_uses_release(self):
        v = lava_jobs.build_variables("qemu-amd64", "trixie", "next", "30")
        self.assertIn("trixie-ovmf", v["imageargs"])

    def test_build_variables_imageargs_empty_for_unknown_target(self):
        v = lava_jobs.build_variables("x86-uefi", "trixie", "next", "30")
        self.assertEqual(v["imageargs"], "")
        self.assertEqual(v["context_architecture"], "uefi")

    def test_add_firmware_adds_images_firmware(self):
        v = lava_jobs.build_variables("qemu-arm64", "trixie", "next", "30")
        deploy = {"images": {}}
        lava_jobs.add_firmware(deploy, v)
        fw = deploy["images"]["firmware"]
        self.assertEqual(fw["image_arg"], "-bios {firmware}")
        self.assertTrue(fw["url"].endswith("/next/qemu-arm64/firmware.bin"))

    def test_load_fragment_corrupt_rootfs_keeps_shell_vars(self):
        v = lava_jobs.build_variables("qemu-arm64", "trixie", "next", "30")
        steps = lava_jobs.load_fragment("corrupt_rootfs", v)
        text = "\n".join(str(s) for s in steps)
        self.assertIn("${rootfs_start}", text)
        self.assertIn("trixie-qemu-arm64", text)

    def test_write_job_roundtrip(self):
        job = {"z": 1, "a": "x" * 500}
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "job.yml"
            lava_jobs.write_job(job, path)
            self.assertEqual(lava_jobs.load_yaml(path), job)
            self.assertEqual(len(path.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
