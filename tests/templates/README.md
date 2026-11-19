# LAVA job templates

`scripts/lava_jobs.py` builds LAVA job definitions from the files in this
directory. Every file is valid YAML, so it can be loaded and checked on its
own.

```
blocks/    one part of a job: header, deploy, boot or test action
steps/     list of shell commands run on the target by a test action
jobs.yml   which blocks and steps make up each test, plus per-target values
```

Values that change per job are written as `${name}`, for example
`${distribution}` or `${architecture}`. The available names are listed in
`doc/README.lava-testing.md`. Shell variables such as `$LAVA_JOB_ID` or
`${file}` are not placeholders and stay untouched.

## How a job is built

For one test and one target, `scripts/lava_jobs.py`:

1. takes the `blocks` of the test from `jobs.yml` (or
   `per_arch.<target>.blocks` if set) and loads them in the listed order.
   A block that is a list (`- deploy:`, `- boot:`, `- test:`) is appended
   to `actions`; a block that is a mapping (`header_qemu`, `context_qemu`)
   becomes top-level keys of the job.
2. fills in `${name}` placeholders. Values come from the command line
   (target, release, branch), then the `values` of the test, then
   `per_arch.<target>.values`; later ones win.
3. inserts the `steps` of the test into the first empty `steps: []` list of
   the job.
4. applies the text edits: `replace`, then `per_arch.<target>.replace`,
   `disk` and `efi_name`. `${branch}` and `${distribution}` are filled in
   only after these edits, so the edits never change a branch name.

## Example 1: a new negative software update test

The test applies an update whose `sw-description` is removed and expects
swupdate to refuse it. It differs from the existing negative tests only in
the commands, so it reuses their blocks.

1. Add the shell commands as `steps/missing_sw_description.yml`. Each entry is
   one command; `${distribution}` and `${architecture}` are filled in:

   ```yaml
   - curl -v --trace-time http://$LAVA_DISPATCHER_IP/tmp/$LAVA_JOB_ID/downloads/common/cip-core-image-security-cip-core-${distribution}-${architecture}.swu --output /root/update.swu
   - mkdir -p /root/swu
   - cpio -ivd --directory=/root/swu < /root/update.swu
   - rm /root/swu/sw-description
   - swupdate -l 5 -i /root/update.swu > /root/swupdate.txt
   - if grep -q "sw-description" /root/swupdate.txt; then echo "verification successful"; else lava-test-raise "Fail job"; fi
   ```

   `$LAVA_DISPATCHER_IP` and `$LAVA_JOB_ID` are shell variables on the
   target and stay as they are. The last command decides the result:
   `lava-test-raise` fails the job.

2. Add the test to `jobs.yml`:

   ```yaml
   swupdate-missing-sw-description:
     output_name: "{test}_{target}.yml"
     blocks: *swupdate_negative_blocks
     steps: {fragment: missing_sw_description}
     values:
       job_title: software update testing
   ```

   - The key `swupdate-missing-sw-description` is the test name, used as
     `--test` and as `test_function` in CI.
   - `output_name` is the file name of the job; `{test}` and `{target}` are
     filled in.
   - `*swupdate_negative_blocks` is the YAML anchor defined at
     `swupdate-corrupt-swu`: header, TPM, deploy of the image and the .swu,
     boot, and `test_swupdate_inline`, whose `steps: []` list receives the
     commands of `steps/missing_sw_description.yml`.
   - `job_title` ends up in the job name (`${architecture} ${job_title}` in
     `header_qemu`).
   - Without `targets`, the test exists for qemu-amd64, qemu-arm64 and
     qemu-arm.

3. Generate the job and validate it against the LAVA server:

   ```
   python3 scripts/lava_jobs.py --test swupdate-missing-sw-description \
       --target qemu-amd64 --release trixie --branch master \
       --iec-timeout 30 --out /tmp/jobs
   lavacli -i <identity> jobs validate /tmp/jobs/swupdate-missing-sw-description_qemu-amd64.yml
   ```

   `--branch` is the directory of the build artifacts on the download
   server; CI passes the pipeline ID. Read the generated file once: it is
   the job LAVA runs.

4. Add a unit test to `tests/test_lava_qemu_jobs.py` (M-COM jobs:
   `tests/test_lava_mcom_jobs.py`). Check what makes this test different
   from the others, here that the commands are in the job:

   ```python
   def test_missing_sw_description_steps(self):
       job = build("swupdate-missing-sw-description", "qemu-amd64")
       self.assertIn("rm /root/swu/sw-description", list(all_strings(job)))
   ```

   `build()` (from `tests/lava_test_helpers.py`) generates the job like the
   command line does, with branch `br` and release trixie.

5. Run the test in CI. Add one job per target to `.gitlab-ci.yml`:

   ```yaml
   test:qemu-amd64-swupdate-missing-sw-description:
     extends:
       - .test-cip-core
     needs: ["build:qemu-amd64-base"]
     variables:
       target: qemu-amd64
       test_function: swupdate-missing-sw-description
   ```

   `.test-cip-core` calls `scripts/submit_lava.sh`, which generates the job
   with `test_function` as `--test`, validates and submits it. `needs`
   names the build job that deploys the image the test downloads.

## Example 2: a test with its own blocks

The test boots the image and checks the kernel architecture. No existing
test action fits, so it gets a new block.

1. Create `blocks/test_kernel_arch.yml`. A block is a list with one LAVA
   action:

   ```yaml
   - test:
       timeout:
         minutes: 5
       definitions:
       - repository:
           metadata:
             format: Lava-Test Test Definition 1.0
             name: kernel-arch
             description: "check the kernel architecture"
           run:
             steps:
               - uname -m
         from: inline
         name: kernel-arch
         path: inline/kernel-arch.yaml
   ```

2. Add the test to `jobs.yml` with the full list of blocks:

   ```yaml
   kernel-arch:
     output_name: "{test}_{target}.yml"
     blocks: [header_qemu, action_tpm, deploy_tmpfs, boot_qemu,
              test_kernel_arch, context_qemu]
     values:
       job_title: kernel architecture check
     targets: [qemu-amd64, qemu-arm64]
   ```

   - `header_qemu` (mapping): device type, timeouts, tags, notification.
   - `action_tpm`: starts the software TPM; `deploy_tmpfs` passes its
     socket to QEMU, so the two go together.
   - `deploy_tmpfs`: downloads and decompresses the wic image.
   - `boot_qemu`: boots and logs in.
   - `test_kernel_arch`: the new block.
   - `context_qemu` (mapping): the LAVA context; always written last.
   - `targets`: only these targets get the job. For any other target
     `lava_jobs.py` writes nothing, and `submit_lava.sh` fails with
     "No job definition generated".

3. Generate, validate, add a unit test and the CI jobs as in Example 1.

## Example 3: differences between targets

`per_arch` holds what differs for one target. From `jobs.yml`:

```yaml
secure-boot-unsigned-bootloader:
  ...
  values:
    start_monitor: Access Denied
    end_monitor: "BdsDxe: failed to load Boot"
  per_arch:
    qemu-arm64:
      disk: vda
      efi_name: bootaa64.efi
      values:
        start_monitor: Image not authenticated
        end_monitor: EFI Boot failed!
```

- `values` overrides the values of the test for this target: the arm64
  firmware prints other messages than OVMF on amd64.
- `disk: vda` replaces every `sda` in the job; the arm guests have a virtio
  disk.
- `efi_name` replaces `bootx64.efi` with the boot loader name of the
  target.

M-COM (x86-uefi) is real hardware and needs other blocks. The `swupdate`
test sets them with `per_arch.x86-uefi.blocks`, and uses `replace` for a
text that differs on M-COM:

```yaml
per_arch:
  x86-uefi:
    blocks: [header_mcom, deploy_mcom_swu, deploy_mcom, boot_mcom, ...]
    replace:
      - ["overlay-1.1.1.4", "overlay-2.1.1.4"]
```

`replace` is a list of `[old, new]` pairs applied to every string of the
job. Use it for a small change of an existing block; for anything larger,
add a block. M-COM must be listed in `targets`.

## Example 4: a new placeholder

To use a new value, for example `${swu_name}` in a block:

1. Add `swu_name` to `KNOWN_VARIABLES` in `scripts/lava_jobs.py`. Only
   known names are replaced; any other `${...}` is treated as a shell
   variable and left in the job, so a missing entry is not reported.
2. Set the value in `values` of the test (or `per_arch.<target>.values`).
   If a test uses a block with `${swu_name}` and sets no value,
   `lava_jobs.py` stops with "missing value for placeholder 'swu_name'".
3. Document the name in `doc/README.lava-testing.md`.

## Blocks to keep in sync

The `boot_mcom`, `boot_mcom_secureboot` and `boot_mcom_after_update`
blocks are near-copies; keep them in sync.

## Run the tests

```
python3 -m unittest discover -s tests
```

The tests are split by area: `tests/test_lava_fragments.py` (fragments and
placeholders), `test_lava_core.py` (variables, firmware, job writing),
`test_lava_qemu_jobs.py`, `test_lava_mcom_jobs.py`, `test_lava_branch_names.py`
and `test_lava_cli.py`. A single area runs with e.g.

```
python3 -m unittest tests.test_lava_qemu_jobs
```
