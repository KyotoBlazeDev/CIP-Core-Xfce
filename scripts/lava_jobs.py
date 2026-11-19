#
# Copyright (c) Siemens AG, 2026
#
# Authors:
#  Quirin Gylstorff <quirin.gylstorff@siemens.com>
#
# SPDX-License-Identifier: MIT
#

"""Generate LAVA job definitions from YAML fragments."""

import argparse
import functools
import re
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "tests" / "templates"
JOBS_FILE = TEMPLATES_DIR / "jobs.yml"
PROJECT_URL = "https://s3.eu-central-1.amazonaws.com/download2.cip-project.org/cip-core"

KNOWN_VARIABLES = (
    "branch",
    "distribution",
    "project_url",
    "architecture",
    "imageargs",
    "context_architecture",
    "test_function",
    "updatestate",
    "job_title",
    "start_monitor",
    "end_monitor",
    "artifact",
    "IEC_TEST_TIMEOUT_MINUTES",
)

IMAGE_ARGS = {
    "qemu-amd64": (
        "-cpu Haswell,-pcid,-x2apic,-tsc-deadline,-hle,-invpcid,-rtm -machine q35,accel=tcg -smp 4 -global ICH9-LPC.noreboot=off -device ide-hd,drive=disk -drive if=pflash,format=raw,unit=0,readonly=on,file=/root/keys/${release}-ovmf/OVMF_CODE_4M.secboot.fd -device virtio-net-pci,netdev=net -drive if=pflash,format=raw,file=/root/keys/${release}-ovmf/OVMF_VARS_4M.snakeoil.fd  -global ICH9-LPC.disable_s3=1 -global isa-fdc.driveA= -device tpm-tis,tpmdev=tpm0"
    ),
    "qemu-arm64": (
        "-cpu cortex-a57 -machine virt -smp 4 -device virtio-serial-device -device virtconsole,chardev=con -chardev vc,id=con -device virtio-blk-device,drive=disk -device virtio-net-device,netdev=net -device tpm-tis-device,tpmdev=tpm0"
    ),
    "qemu-arm": (
        "-cpu cortex-a15 -machine virt -smp 2 -device virtio-serial-device -device virtconsole,chardev=con -chardev vc,id=con -device virtio-blk-device,drive=disk -device virtio-net-device,netdev=net -device tpm-tis-device,tpmdev=tpm0"
    ),
}

QEMU_TARGETS = tuple(IMAGE_ARGS)
MCOM_TARGETS = ("x86-uefi",)
TARGETS = QEMU_TARGETS + MCOM_TARGETS
FIRMWARE_TARGETS = ("qemu-arm64", "qemu-arm")

PLACEHOLDER = re.compile(r"\$\{([A-Za-z_]+)\}")

# Filled only after all text rewrites (sda -> vda, .swu -> -broken.swu, ...)
# so that these rewrites can never change a branch or release name.
DEFERRED_VARIABLES = ("distribution", "branch")

# Wide enough that PyYAML never folds a line (long shell commands).
NO_LINE_WRAP = 10**6


def load_yaml(path: Path) -> Any:
    """Parse a YAML file."""
    return yaml.safe_load(Path(path).read_text())


def find_unreplaced(text: str) -> list[str]:
    """Return known variable names still present as ${name}."""
    names = PLACEHOLDER.findall(text)
    return [name for name in names if name in KNOWN_VARIABLES]


def substitute(text: str, variables: Mapping[str, str]) -> str:
    """Replace ${name} from variables; KeyError if a known name is missing.

    Other ${name} forms (shell variables), $name and $$ stay untouched.
    """

    def value(match: re.Match) -> str:
        name = match.group(1)
        if name in variables:
            return str(variables[name])
        if name in KNOWN_VARIABLES:
            raise KeyError(name)
        return match.group(0)

    return PLACEHOLDER.sub(value, text)


def fragment_path(name: str) -> Path:
    """Locate a fragment in blocks/ or steps/."""
    for subdir in ("blocks", "steps"):
        path = TEMPLATES_DIR / subdir / f"{name}.yml"
        if path.exists():
            return path
    raise FileNotFoundError(name)


def load_fragment(name: str, variables: Mapping[str, str]) -> Any:
    """Substitute variables into a fragment's text, then parse it."""
    text = fragment_path(name).read_text()
    return yaml.safe_load(substitute(text, variables))


def image_args(target: str, release: str) -> str:
    """Return the QEMU arguments of a target, using OVMF keys of release."""
    return substitute(IMAGE_ARGS.get(target, ""), {"release": release})


def build_variables(
    target: str, release: str, branch: str, iec_timeout: str
) -> dict[str, str]:
    """Return the globally known substitution values."""
    imageargs = image_args(target, release)
    return {
        "branch": branch,
        "distribution": release,
        "project_url": PROJECT_URL,
        "architecture": target,
        "context_architecture": target.split("-")[1],
        "imageargs": imageargs,
        "IEC_TEST_TIMEOUT_MINUTES": iec_timeout,
    }


def add_firmware(deploy_block: dict, variables: Mapping[str, str]) -> None:
    """Add the firmware image to a deploy block."""
    base = f"{variables['project_url']}/{variables['branch']}"
    url = f"{base}/{variables['architecture']}/firmware.bin"
    firmware = {"image_arg": "-bios {firmware}", "url": url}
    deploy_block["images"]["firmware"] = firmware


def write_job(job: dict, path: Path) -> None:
    """Write a job definition as YAML."""
    text = yaml.safe_dump(job, sort_keys=False, default_flow_style=False, width=NO_LINE_WRAP)
    Path(path).write_text(text)


@functools.cache
def load_jobs() -> dict:
    """Return the per-test job descriptions from jobs.yml (read once, do not mutate)."""
    return load_yaml(JOBS_FILE)["tests"]


def job_spec(test: str) -> dict:
    """Return the description of one test; ValueError if unknown."""
    jobs = load_jobs()
    if test not in jobs:
        raise ValueError(f"unknown test: {test}")
    return jobs[test]


def is_supported(test: str, target: str) -> bool:
    """Tell whether a job exists for this test and target."""
    targets = job_spec(test).get("targets", QEMU_TARGETS)
    return target in targets


def output_filename(test: str, target: str) -> str:
    """Return the job file name for a test and target."""
    return job_spec(test)["output_name"].format(test=test, target=target)


def replace_in_strings(node: Any, old: str, new: str, count: int = -1) -> Any:
    """Replace old with new in every string of a parsed structure, in place."""
    if isinstance(node, dict):
        for key in node:
            node[key] = replace_in_strings(node[key], old, new, count)
        return node
    if isinstance(node, list):
        for index, item in enumerate(node):
            node[index] = replace_in_strings(item, old, new, count)
        return node
    if isinstance(node, str):
        return node.replace(old, new, count)
    return node


def other_release(release: str) -> str:
    """Return the release whose OVMF keys do not match."""
    if release == "trixie":
        return "bookworm"
    return "trixie"


def find_empty_steps(node: Any) -> list | None:
    """Return the first empty `steps` list in a parsed structure."""
    if isinstance(node, dict):
        if node.get("steps") == []:
            return node["steps"]
        children = list(node.values())
    elif isinstance(node, list):
        children = node
    else:
        return None
    for child in children:
        found = find_empty_steps(child)
        if found is not None:
            return found
    return None


def tmpfs_deploy(job: dict) -> dict:
    """Return the deploy action that boots the image from tmpfs."""
    for action in job["actions"]:
        deploy = action.get("deploy")
        if deploy and deploy.get("to") == "tmpfs":
            return deploy
    raise ValueError("job has no tmpfs deploy")


def assemble(blocks: list, variables: Mapping[str, str]) -> dict:
    """Merge mapping fragments into the job, append list fragments to actions."""
    job: dict = {}
    actions: list = []
    context = None
    for name in blocks:
        fragment = load_fragment(name, variables)
        if isinstance(fragment, list):
            actions.extend(fragment)
        elif list(fragment) == ["context"]:
            # Fragment holding only "context": deferred so it ends up last in
            # the job, as in the old templates.
            context = fragment["context"]
        else:
            job.update(fragment)
    job["actions"] = actions
    if context is not None:
        job["context"] = context
    return job


def arch_spec(spec: dict, target: str) -> dict:
    """Return the per-target part of a test description."""
    return spec.get("per_arch", {}).get(target, {})


def job_blocks(spec: dict, target: str) -> list:
    """Return the fragments of the job; per-target blocks win (M-COM)."""
    return arch_spec(spec, target).get("blocks", spec["blocks"])


def job_variables(spec: dict, target: str, variables: Mapping[str, str]) -> dict:
    """Combine global variables with per-test and per-target values."""
    arch = arch_spec(spec, target)
    merged = dict(variables)
    merged["updatestate"] = "2"
    merged.update(spec.get("values", {}))
    merged.update(arch.get("values", {}))
    if spec.get("swap_ovmf"):
        # Mismatch keys test: boot with OVMF keys of the other release.
        release = other_release(variables["distribution"])
        merged["imageargs"] = image_args(target, release)
    return merged


def defer(variables: Mapping[str, str]) -> dict:
    """Return variables whose deferred names map to their own placeholder."""
    kept = dict(variables)
    for name in DEFERRED_VARIABLES:
        kept[name] = "${" + name + "}"
    return kept


def fill_deferred(job: dict, variables: Mapping[str, str]) -> None:
    """Replace the deferred placeholders in every string of the job."""
    for name in DEFERRED_VARIABLES:
        replace_in_strings(job, "${" + name + "}", variables[name])


def add_steps(job: dict, spec: dict, variables: Mapping[str, str]) -> None:
    """Insert the test's steps into the job's empty steps list."""
    steps_spec = spec.get("steps")
    if not steps_spec:
        return
    if "fragment" in steps_spec:
        steps = load_fragment(steps_spec["fragment"], variables)
    else:
        steps = list(steps_spec["inline"])
    find_empty_steps(job).extend(steps)


def rewrite_texts(job: dict, spec: dict, arch: dict) -> None:
    """Apply the test and architecture text edits to the job, in place."""
    # Text rewrites, in the order of the old submit_lava.sh. They run while
    # branch and distribution are still placeholders (DEFERRED_VARIABLES):
    # 1. test texts (kernel-panic, initramfs-crash) match the original
    #    fragment text, so they run first.
    #    Per-target texts (M-COM overlay name) follow.
    for old, new in spec.get("replace", []) + arch.get("replace", []):
        replace_in_strings(job, old, new)
    # 2. '-broken.swu' update image: first '.swu' of each string only.
    if spec.get("broken_swu"):
        replace_in_strings(job, ".swu", "-broken.swu", 1)
    # 3. guest disk name (vda on arm); after 1 so '/dev/sda5' inserted by
    #    initramfs-crash (amd64 only) is never renamed.
    if "disk" in arch:
        replace_in_strings(job, "sda", arch["disk"])
    # 4. EFI boot loader name (bootaa64.efi, bootarm.efi).
    if "efi_name" in arch:
        replace_in_strings(job, "bootx64.efi", arch["efi_name"])


def build_job(test: str, target: str, variables: Mapping[str, str]) -> dict:
    """Build the LAVA job definition for a test and target."""
    spec = job_spec(test)
    if not is_supported(test, target):
        raise ValueError(f"unsupported combination: {test} on {target}")
    arch = arch_spec(spec, target)
    values = job_variables(spec, target, variables)
    early_values = defer(values)
    job = assemble(job_blocks(spec, target), early_values)
    add_steps(job, spec, early_values)
    rewrite_texts(job, spec, arch)
    fill_deferred(job, values)
    # Firmware (qemu-arm64, qemu-arm; never M-COM) is added last, after all
    # rewrites, since its URL holds the branch name.
    if target in FIRMWARE_TARGETS:
        add_firmware(tmpfs_deploy(job), values)
    return job


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--iec-timeout", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Write the job definition for --test/--target into --out."""
    args = parse_args(argv)
    if args.target not in TARGETS:
        print(f"error: unsupported target: {args.target}", file=sys.stderr)
        return 1
    if args.test == "IEC" and not args.iec_timeout:
        print("error: --iec-timeout must not be empty for IEC", file=sys.stderr)
        return 1
    variables = build_variables(args.target, args.release, args.branch, args.iec_timeout)
    try:
        if not is_supported(args.test, args.target):
            print(f"no {args.test} job for {args.target}, nothing written")
            return 0
        job = build_job(args.test, args.target, variables)
        name = output_filename(args.test, args.target)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyError as error:
        print(f"error: missing value for placeholder {error}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / name
    write_job(job, path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
