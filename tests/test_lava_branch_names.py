#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests that branch and distribution names are kept verbatim."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import all_strings, lava_jobs  # noqa: E402


BRANCHES = ("fix-sda-x", "a.swu-b", "x-bootx64.efi-y", "trixie-ovmf")
# (test, target) pairs that run the sda, .swu, bootx64.efi and OVMF rewrites.
REWRITING_JOBS = (
    ("kernel-panic", "qemu-amd64"),
    ("secure-boot-unsigned-bootloader", "qemu-arm64"),
    ("secure-boot-unsigned-kernel", "qemu-arm"),
    ("secure-boot-mismatch-keys", "qemu-amd64"),
)


class BranchVerbatimTests(unittest.TestCase):
    def test_urls_keep_branch_verbatim(self):
        for branch in BRANCHES:
            for test, target in REWRITING_JOBS:
                with self.subTest(branch=branch, test=test, target=target):
                    v = lava_jobs.build_variables(target, "trixie", branch, "30")
                    job = lava_jobs.build_job(test, target, v)
                    urls = [s for s in all_strings(job)
                            if s.startswith(lava_jobs.PROJECT_URL)]
                    self.assertTrue(urls)
                    for url in urls:
                        self.assertIn(f"/{branch}/", url)

    def test_distribution_kept_verbatim(self):
        v = lava_jobs.build_variables("qemu-arm64", "sda.swu", "br", "30")
        job = lava_jobs.build_job("secure-boot-unsigned-kernel", "qemu-arm64", v)
        text = "\n".join(all_strings(job))
        self.assertIn("cip-core-sda.swu-qemu-arm64.wic", text)
        self.assertIn("/dev/vda2", text)

if __name__ == "__main__":
    unittest.main()
