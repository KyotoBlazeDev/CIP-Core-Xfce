#!/bin/bash
#
# SPDX-License-Identifier: MIT
#
# Copyright (C) 2024, Renesas Electronics Europe GmbH
# Chris Paterson <chris.paterson2@renesas.com>
# Sai Ashrith <sai.sathujoda@toshiba-tsip.com>
################################################################################

set -e

################################################################################
LAVA_JOBS_URL="https://${CIP_LAVA_LAB_SERVER:-lava.ciplatform.org}/scheduler/job"
LAVA_API_URL="https://$CIP_LAVA_LAB_USER:$CIP_LAVA_LAB_TOKEN@${CIP_LAVA_LAB_SERVER:-lava.ciplatform.org}/api/v0.2"
LAVACLI_ARGS="--uri https://$CIP_LAVA_LAB_USER:$CIP_LAVA_LAB_TOKEN@${CIP_LAVA_LAB_SERVER:-lava.ciplatform.org}/RPC2"

WORK_DIR=$(pwd)
RESULTS_DIR="$WORK_DIR/results"
ERROR=false
TEST=$1
TARGET=$2
COMMIT_REF=$3
RELEASE=$4
COMMIT_BRANCH=$5
IEC_TEST_TIMEOUT_MINUTES=$6

if [ -z "$SUBMIT_ONLY" ]; then SUBMIT_ONLY=false; fi

set_up (){
	job_dir="$(mktemp -d)"
}

clean_up () {
	rm -rf "$job_dir"
}

# $1: Job definition file
submit_job() {
        # First check if respective device is online
	local job device ret device
	job=$1
	device=$(grep device_type "$job" | cut -d ":" -f 2 | awk '{$1=$1};1')
	if is_device_online "$device"; then
		echo "Submitting $1 to LAVA master..."
		# Catch error that occurs if invalid yaml file is submitted
		# shellcheck disable=2086
		ret=$(lavacli $LAVACLI_ARGS jobs submit "$1") || ERROR=true

		if [[ $ret != [0-9]* ]]
		then
			echo "Something went wrong with job submission. LAVA returned:"
			return 1
		else
			echo "Job submitted successfully as #${ret}."
			echo "URL: ${LAVA_JOBS_URL}/${ret}"

			local lavacli_output=${job_dir}/lavacli_output
			# shellcheck disable=2086
			lavacli $LAVACLI_ARGS jobs show "${ret}" \
				> "$lavacli_output"

			DEVICE=$(grep "device      :" "$lavacli_output" \
				| cut -d ":" -f 2 \
				| awk '{$1=$1};1')

			# shellcheck disable=2086
			lavacli $LAVACLI_ARGS jobs logs "${ret}"
			# shellcheck disable=2086
			lavacli $LAVACLI_ARGS results "${ret}"

			get_junit_test_results "$ret"
		fi
	else
		return 1
	fi
}

# $1: Device-type to search for
is_device_online () {
	local count
	local lavacli_output=${job_dir}/lavacli_output

	# Get list of all devices
	# shellcheck disable=2086
	lavacli $LAVACLI_ARGS devices list > "$lavacli_output"

	# Count the number of online devices
	count=$(grep "(${1})" "$lavacli_output" | grep -c "Good")
	echo "There are currently $count \"${1}\" devices online."

	if [ "$count" -gt 0 ]; then
		return 0
	fi
	return 1
}

# This method checks if the job is valid before submitting it later on.
validate_job () {
	local job
	job=$(find "${job_dir}"/*.yml)
	# shellcheck disable=2086
	if lavacli $LAVACLI_ARGS jobs validate "${job}"; then
		echo "$job is a valid definition"
		if ! submit_job $job; then
			clean_up
			exit 1
		fi
	else
		echo "$job is not a valid definition"
		return 1
	fi
	return 0
}

get_first_xml_attr_value() {
	file=${1}
	tag=${2}

	grep -m 1 -o "${tag}=\".*\"" "${file}" | cut -d\" -f2
}

get_junit_test_results () {
	mkdir -p "${RESULTS_DIR}"
	curl -s -o "${RESULTS_DIR}"/results_"$1".xml "${LAVA_API_URL}"/jobs/"$1"/junit/

	# change return code to generate a error in gitlab-ci if a test is failed
	if xmlstarlet sel -t  -v "/testsuites/testsuite/testcase[@name='job']/failure/@type" "${RESULTS_DIR}"/results_"$1".xml; then
		ERROR=true
	fi
}

set_up

if [[ ! $TARGET =~ "qemu" && ! $TARGET =~ "x86-uefi" ]]; then
	echo "Invalid target"
	clean_up
	exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/lava_jobs.py" --test "$TEST" --target "$TARGET" \
	--release "$RELEASE" --branch "$COMMIT_BRANCH" \
	--iec-timeout "$IEC_TEST_TIMEOUT_MINUTES" --out "$job_dir" || {
	clean_up
	exit 1
}

if ! compgen -G "${job_dir}/*.yml" > /dev/null; then
	echo "No job definition generated for $TEST on $TARGET"
	clean_up
	exit 1
fi

if ! validate_job; then
	clean_up
	exit 1
fi

clean_up

if $ERROR; then
	exit 1
fi
