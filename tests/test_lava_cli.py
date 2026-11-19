#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests for the lava_jobs command line and its error handling."""

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import build, lava_jobs  # noqa: E402


class CommandLineTests(unittest.TestCase):
    def test_mismatch_keys_arm64_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "secure-boot-mismatch-keys",
                                 "--target", "qemu-arm64", "--release", "trixie",
                                 "--branch", "br", "--iec-timeout", "30", "--out", d])
            self.assertEqual(rc, 0)
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_unknown_test_exits_nonzero(self):
        with self.assertRaises(ValueError):
            build("no-such-test", "qemu-amd64")
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "no-such-test", "--target", "qemu-amd64",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", d])
            self.assertNotEqual(rc, 0)

    def test_malformed_target_exits_nonzero(self):
        for target in ("qemu", "foo"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                rc = lava_jobs.main(["--test", "swupdate", "--target", target,
                                     "--release", "trixie", "--branch", "br",
                                     "--iec-timeout", "30", "--out", d])
                self.assertNotEqual(rc, 0)
                self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_main_writes_output_filename(self):
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "swupdate", "--target", "qemu-arm",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", d])
            self.assertEqual(rc, 0)
            out = pathlib.Path(d) / "swupdate_qemu-arm.yml"
            self.assertEqual(lava_jobs.load_yaml(out)["device_type"], "qemu")

    def test_main_creates_missing_out_dir(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "a" / "b"
            rc = lava_jobs.main(["--test", "swupdate", "--target", "qemu-arm",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "swupdate_qemu-arm.yml").exists())

    def test_main_reports_missing_variable(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(lava_jobs, "build_job", side_effect=KeyError("x")):
            rc = lava_jobs.main(["--test", "swupdate", "--target", "qemu-arm",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "30", "--out", d])
            self.assertEqual(rc, 1)
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_iec_with_empty_timeout_fails_early(self):
        with tempfile.TemporaryDirectory() as d:
            rc = lava_jobs.main(["--test", "IEC", "--target", "qemu-arm",
                                 "--release", "trixie", "--branch", "br",
                                 "--iec-timeout", "", "--out", d])
            self.assertEqual(rc, 1)
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
