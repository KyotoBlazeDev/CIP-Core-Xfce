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

## Example: a new negative software update test

The test applies an update whose `sw-description` is removed and expects
swupdate to refuse it.

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

2. Add the test to `jobs.yml`. It reuses the blocks of the other negative
   software update tests and only names the new steps:

   ```yaml
   swupdate-missing-sw-description:
     output_name: "{test}_{target}.yml"
     blocks: *swupdate_negative_blocks
     steps: {fragment: missing_sw_description}
     values:
       job_title: software update testing
   ```

   `output_name` is the file name; `{test}` and `{target}` are filled in.
   The `test_swupdate_inline` block contains an empty `steps: []` list; the
   generator fills it with the commands from the fragment.

3. Generate and check the job:

   ```
   python3 scripts/lava_jobs.py --test swupdate-missing-sw-description \
       --target qemu-amd64 --release trixie --branch master \
       --iec-timeout 30 --out /tmp/jobs
   lavacli -i <identity> jobs validate /tmp/jobs/swupdate-missing-sw-description_qemu-amd64.yml
   ```

4. Add a unit test (in `tests/test_lava_qemu_jobs.py` for QEMU jobs,
   `tests/test_lava_mcom_jobs.py` for MCOM jobs), and a `test_function` entry
   in `.gitlab-ci.yml` to run the test in the pipeline.

## Adding a new block

Create `blocks/<name>.yml` with the action as a list item, for example a
test action:

```yaml
- test:
    timeout:
      minutes: 5
    definitions:
    - repository:
        metadata:
          format: Lava-Test Test Definition 1.0
          name: sample-test
          description: "check the kernel version"
        run:
          steps:
            - uname -r | grep -q ${context_architecture}
      from: inline
      name: sample-test-4
      path: inline/sample-test.yaml
```

Then list `<name>` in the `blocks:` of a test in `jobs.yml`. Blocks are
added to `actions` in the listed order. A block that is a mapping (for
example `header_qemu` or `context_qemu`) becomes top-level keys of the job
instead. The `jobs.yml` header describes all keys, including `per_arch` for
target specific blocks, values and text replacements.

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
