#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Tests for the YAML fragments and placeholder substitution."""

import pathlib
import sys
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lava_test_helpers import TEMPLATES, lava_jobs  # noqa: E402


class FragmentTests(unittest.TestCase):
    def test_all_fragments_parse(self):
        files = []
        for sub in ("blocks", "steps"):
            files += sorted((TEMPLATES / sub).glob("*.yml"))
        self.assertTrue(files, "no fragments found")
        for f in files:
            with self.subTest(fragment=f.name):
                self.assertIsNotNone(yaml.safe_load(f.read_text()))


JOBS_YML = TEMPLATES / "jobs.yml"
# ${name} forms in fragments that are shell variables, not placeholders.
SHELL_VARIABLES = ("file", "offset", "rootfs_start", "rootfs_start_sector")


class PlaceholderTests(unittest.TestCase):
    def test_substitute_replaces_known(self):
        out = lava_jobs.substitute("a ${branch} b", {"branch": "next"})
        self.assertEqual(out, "a next b")

    def test_substitute_missing_variable_raises(self):
        with self.assertRaises(KeyError):
            lava_jobs.substitute("a ${branch}", {})

    def test_substitute_keeps_shell_variables(self):
        text = "curl $LAVA_DISPATCHER_IP/${offset}"
        self.assertEqual(lava_jobs.substitute(text, {}), text)

    def test_substitute_leaves_unknown_shell_variables(self):
        text = "x=$(( ${rootfs_start} + 1 )) $LAVA_JOB_ID ${file}"
        out = lava_jobs.substitute(text, {"branch": "b"})
        self.assertEqual(out, text)

    def test_substitute_leaves_dollar_dollar_and_bare_names(self):
        text = "$$x $branch ${artefact}"
        self.assertEqual(lava_jobs.substitute(text, {"branch": "b"}), text)

    def test_fragments_use_only_known_or_shell_variables(self):
        files = [JOBS_YML]
        for sub in ("blocks", "steps"):
            files += sorted((TEMPLATES / sub).glob("*.yml"))
        allowed = set(lava_jobs.KNOWN_VARIABLES) | set(SHELL_VARIABLES)
        for f in files:
            with self.subTest(fragment=f.name):
                names = set(lava_jobs.PLACEHOLDER.findall(f.read_text()))
                self.assertEqual(names - allowed, set())


if __name__ == "__main__":
    unittest.main()
