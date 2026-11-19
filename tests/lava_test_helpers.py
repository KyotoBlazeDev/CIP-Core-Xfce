#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Shared setup and helpers for the LAVA job generator tests."""

import pathlib
import sys

TEMPLATES = pathlib.Path(__file__).parent / "templates"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import lava_jobs  # noqa: E402


def variables(target, release="trixie"):
    return lava_jobs.build_variables(target, release, "br", "30")


def build(test, target, release="trixie"):
    return lava_jobs.build_job(test, target, variables(target, release))


def all_strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from all_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_strings(value)
    elif isinstance(node, str):
        yield node
