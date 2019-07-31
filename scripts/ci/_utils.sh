#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Assume all the scripts are sourcing the _utils.sh from the scripts/ci directory
# and MY_DIR variable is set to this directory
AIRFLOW_SOURCES=$(cd "${MY_DIR}/../../" && pwd)
export AIRFLOW_SOURCES

BUILD_CACHE_DIR="${AIRFLOW_SOURCES}/.build"
export BUILD_CACHE_DIR

FILES_FOR_REBUILD_CHECK="\
setup.py \
setup.cfg \
Dockerfile \
.dockerignore \
airflow/version.py
"

mkdir -p "${AIRFLOW_SOURCES}/.mypy_cache"
mkdir -p "${AIRFLOW_SOURCES}/logs"
mkdir -p "${AIRFLOW_SOURCES}/tmp"

# Disable writing .pyc files - slightly slower imports but not messing around when switching
# Python version and avoids problems with root-owned .pyc files in host
export PYTHONDONTWRITEBYTECODE="true"

# Read default branch name
# shellcheck source=../../hooks/_default_branch.sh
. "${AIRFLOW_SOURCES}/hooks/_default_branch.sh"

# Default branch name for triggered builds is the one configured in hooks/_default_branch.sh
export AIRFLOW_CONTAINER_BRANCH_NAME=${AIRFLOW_CONTAINER_BRANCH_NAME:=${DEFAULT_BRANCH}}

#
# Sets mounting of host volumes to container for static checks
# unless AIRFLOW_MOUNT_HOST_VOLUMES_FOR_STATIC_CHECKS is not true
#
# Note that this cannot be function because we need the AIRFLOW_CONTAINER_EXTRA_DOCKER_FLAGS array variable
#
AIRFLOW_MOUNT_HOST_VOLUMES_FOR_STATIC_CHECKS=${AIRFLOW_MOUNT_HOST_VOLUMES_FOR_STATIC_CHECKS:="true"}


declare -a AIRFLOW_CONTAINER_EXTRA_DOCKER_FLAGS
if [[ ${AIRFLOW_MOUNT_HOST_VOLUMES_FOR_STATIC_CHECKS} == "true" ]]; then
    echo
    echo "Mounting host volumes to Docker"
    echo
    AIRFLOW_CONTAINER_EXTRA_DOCKER_FLAGS=( \
      "-v" "${AIRFLOW_SOURCES}/airflow:/opt/airflow/airflow:cached" \
      "-v" "${AIRFLOW_SOURCES}/.mypy_cache:/opt/airflow/.mypy_cache:cached" \
      "-v" "${AIRFLOW_SOURCES}/dev:/opt/airflow/dev:cached" \
      "-v" "${AIRFLOW_SOURCES}/docs:/opt/airflow/docs:cached" \
      "-v" "${AIRFLOW_SOURCES}/scripts:/opt/airflow/scripts:cached" \
      "-v" "${AIRFLOW_SOURCES}/tmp:/opt/airflow/tmp:cached" \
      "-v" "${AIRFLOW_SOURCES}/tests:/opt/airflow/tests:cached" \
      "-v" "${AIRFLOW_SOURCES}/.flake8:/opt/airflow/.flake8:cached" \
      "-v" "${AIRFLOW_SOURCES}/pylintrc:/opt/airflow/pylintrc:cached" \
      "-v" "${AIRFLOW_SOURCES}/setup.cfg:/opt/airflow/setup.cfg:cached" \
      "-v" "${AIRFLOW_SOURCES}/setup.py:/opt/airflow/setup.py:cached" \
      "-v" "${AIRFLOW_SOURCES}/.rat-excludes:/opt/airflow/.rat-excludes:cached" \
      "-v" "${AIRFLOW_SOURCES}/logs:/opt/airflow/logs:cached" \
      "-v" "${AIRFLOW_SOURCES}/logs:/root/logs:cached" \
      "-v" "${AIRFLOW_SOURCES}/tmp:/opt/airflow/tmp:cached" \
      "-e" "PYTHONDONTWRITEBYTECODE=true" \
    )
else
    echo
    echo "Skip mounting host volumes to Docker"
    echo
    AIRFLOW_CONTAINER_EXTRA_DOCKER_FLAGS=( \
        "-e" "PYTHONDONTWRITEBYTECODE=true" \
    )
fi

export AIRFLOW_CONTAINER_EXTRA_DOCKER_FLAGS

#
# Creates cache directory where we will keep temporary files needed for the build
#
# This directory will be automatically deleted when the script is killed or exists (via trap)
# Unless SKIP_CACHE_DELETION variable is set. You can set this variable and then see
# the output/files generated by the scripts in this directory.
#
# Most useful is out.log file in this directory storing verbose output of the scripts.
#
function create_cache_directory() {
    mkdir -p "${BUILD_CACHE_DIR}/cache/"

    CACHE_TMP_FILE_DIR=$(mktemp -d "${BUILD_CACHE_DIR}/cache/XXXXXXXXXX")
    export CACHE_TMP_FILE_DIR

    if [[ ${SKIP_CACHE_DELETION:=} != "true" ]]; then
        trap 'rm -rf -- "${CACHE_TMP_FILE_DIR}"' INT TERM HUP EXIT
    fi

    OUTPUT_LOG="${CACHE_TMP_FILE_DIR}/out.log"
    export OUTPUT_LOG
}

#
# Verifies if stored md5sum of the file changed since the last tme ot was checked
# The md5sum files are stored in .build directory - you can delete this directory
# If you want to rebuild everything from the scratch
#
function check_file_md5sum {
    local FILE="${1}"
    local MD5SUM
    mkdir -pv "${BUILD_CACHE_DIR}/${THE_IMAGE}"
    MD5SUM=$(md5sum "${FILE}")
    local MD5SUM_FILE
    MD5SUM_FILE=${BUILD_CACHE_DIR}/${THE_IMAGE}/$(basename "${FILE}").md5sum
    local MD5SUM_FILE_NEW
    MD5SUM_FILE_NEW=${CACHE_TMP_FILE_DIR}/$(basename "${FILE}").md5sum.new
    echo "${MD5SUM}" > "${MD5SUM_FILE_NEW}"
    local RET_CODE=0
    if [[ ! -f "${MD5SUM_FILE}" ]]; then
        echo "Missing md5sum for ${FILE}"
        RET_CODE=1
    else
        diff "${MD5SUM_FILE_NEW}" "${MD5SUM_FILE}" >/dev/null
        RES=$?
        if [[ "${RES}" != "0" ]]; then
            echo "The md5sum changed for ${FILE}"
            RET_CODE=1
        fi
    fi
    return ${RET_CODE}
}

#
# Moves md5sum file from it's temporary location in CACHE_TMP_FILE_DIR to
# BUILD_CACHE_DIR - thus updating stored MD5 sum fo the file
#
function move_file_md5sum {
    local FILE="${1}"
    local MD5SUM_FILE
    mkdir -pv "${BUILD_CACHE_DIR}/${THE_IMAGE}"
    MD5SUM_FILE=${BUILD_CACHE_DIR}/${THE_IMAGE}/$(basename "${FILE}").md5sum
    local MD5SUM_FILE_NEW
    MD5SUM_FILE_NEW=${CACHE_TMP_FILE_DIR}/$(basename "${FILE}").md5sum.new
    if [[ -f "${MD5SUM_FILE_NEW}" ]]; then
        mv "${MD5SUM_FILE_NEW}" "${MD5SUM_FILE}"
        echo "Updated md5sum file ${MD5SUM_FILE} for ${FILE}."
    fi
}

#
# Stores md5sum files for all important files and
# records that we built the images locally so that next time we use
# it from the local docker cache rather than pull (unless forced)
#
function update_all_md5_files() {
    echo
    echo "Updating md5sum files"
    echo
    for FILE in ${FILES_FOR_REBUILD_CHECK}
    do
        move_file_md5sum "${AIRFLOW_SOURCES}/${FILE}"
    done
    touch "${BUILD_CACHE_DIR}/.built_${THE_IMAGE}_${PYTHON_VERSION}"
}

#
# Checks md5sum of all important files in order to optimise speed of running various operations
# That mount sources of Airflow to container and require docker image built with latest dependencies.
# the Docker image will only be marked for rebuilding only in case any of the important files change:
# * setup.py
# * setup.cfg
# * Dockerfile
# * airflow/version.py
#
# This is needed because we want to skip rebuilding of the image when only airflow sources change but
# Trigger rebuild in case we need to change dependencies (setup.py, setup.cfg, change version of Airflow
# or the Dockerfile itself changes.
#
# Another reason to skip rebuilding Docker is thar currently it takes a bit longer time than simple Docker
# files. There are the following, problems with the current Dockerfiles that need longer build times:
# 1) We need to fix group permissions of files in Docker because different linux build services have
#    different default umask and Docker uses group permissions in checking for cache invalidation.
# 2) we use multi-stage build and in case of slim image we needlessly build a full CI image because
#    support for this only comes with the upcoming buildkit: https://github.com/docker/cli/issues/1134
#
# As result of this check - most of the static checks will start pretty much immediately.
#
function check_if_docker_build_is_needed() {
    set +e

    for FILE in ${FILES_FOR_REBUILD_CHECK}
    do
        if ! check_file_md5sum "${AIRFLOW_SOURCES}/${FILE}"; then
            export AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED="true"
        fi
    done
    set -e
}

#
# Checks if core utils required in the host system are installed and explain what needs to be done if not
#
function check_if_coreutils_installed() {
    set +e
    getopt -T >/dev/null
    GETOPT_RETVAL=$?

    if [[ $(uname -s) == 'Darwin' ]] ; then
        command -v gstat >/dev/null
        STAT_PRESENT=$?
    else
        command -v stat >/dev/null
        STAT_PRESENT=$?
    fi

    command -v md5sum >/dev/null
    MD5SUM_PRESENT=$?

    set -e

    CMDNAME="$(basename -- "$0")"

    ####################  Parsing options/arguments
    if [[ ${GETOPT_RETVAL} != 4 || "${STAT_PRESENT}" != "0" || "${MD5SUM_PRESENT}" != "0" ]]; then
        echo
        if [[ $(uname -s) == 'Darwin' ]] ; then
            echo >&2 "You are running ${CMDNAME} in OSX environment"
            echo >&2 "And you need to install gnu commands"
            echo >&2
            echo >&2 "Run 'brew install gnu-getopt coreutils'"
            echo >&2
            echo >&2 "Then link the gnu-getopt to become default as suggested by brew by typing:"
            echo >&2 "echo 'export PATH=\"/usr/local/opt/gnu-getopt/bin:\$PATH\"' >> ~/.bash_profile"
            echo >&2 ". ~/.bash_profile"
            echo >&2
            echo >&2 "if you use bash, or"
            echo >&2
            echo >&2 "echo 'export PATH=\"/usr/local/opt/gnu-getopt/bin:\$PATH\"' >> ~/.bash_profile"
            echo >&2 ". ~/.zprofile"
            echo >&2
            echo >&2 "if you use zsh"
            echo >&2
            echo >&2 "Your PATH variable should have \"/usr/local/opt/gnu-getopt/bin\" in front"
            echo >&2
            echo >&2 "Your current path is ${PATH}"
            echo >&2
            echo >&2 "Login and logout afterwards !!"
            echo >&2
        else
            echo >&2 "You do not have necessary tools in your path (getopt, stat, md5sum)."
            echo >&2 "Please install latest/GNU version of getopt and coreutils."
            echo >&2 "This can usually be done with 'apt install util-linux coreutils'"
        fi
        echo
        exit 1
    fi
}

#
# Asserts that we are not inside of the container
#
function assert_not_in_container() {
    if [[ -f /.dockerenv ]]; then
        echo >&2
        echo >&2 "You are inside the Airflow docker container!"
        echo >&2 "You should only run this script from the host."
        echo >&2 "Learn more about how we develop and test airflow in:"
        echo >&2 "https://github.com/apache/airflow/blob/master/CONTRIBUTING.md"
        echo >&2
        exit 1
    fi
}

#
# Forces Python version to 3.5 (for static checks)
#
function force_python_3_5() {
    # Set python version variable to force it in the container scripts
    PYTHON_VERSION=3.5
    export PYTHON_VERSION
}

#
# Rebuilds the slim image for static checks if needed. In order to speed it up, it's built without NPM
#
function rebuild_image_if_needed_for_static_checks() {
    export AIRFLOW_CONTAINER_SKIP_SLIM_CI_IMAGE="false"
    export AIRFLOW_CONTAINER_SKIP_CI_IMAGE="true"
    export AIRFLOW_CONTAINER_SKIP_CHECKLICENCE_IMAGE="true"
    export AIRFLOW_CONTAINER_PUSH_IMAGES="false"
    export AIRFLOW_CONTAINER_BUILD_NPM="false"  # Skip NPM builds to make them faster !

    export PYTHON_VERSION=3.5  # Always use python version 3.5 for static checks
    AIRFLOW_VERSION=$(cat airflow/version.py - << EOF | python
print(version.replace("+",""))
EOF
    )
    export AIRFLOW_VERSION

    export THE_IMAGE="SLIM_CI"
    if [[ -f "${BUILD_CACHE_DIR}/.built_${THE_IMAGE}_${PYTHON_VERSION}" ]]; then
        if [[ ${AIRFLOW_CONTAINER_FORCE_PULL_IMAGES:=""} != "true" ]]; then
            echo
            echo "Image built locally - skip force-pulling them"
            echo
        fi
    else
        echo
        echo "Image not built locally - force pulling them first"
        echo
        export AIRFLOW_CONTAINER_FORCE_PULL_IMAGES="true"
        export AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED="true"
    fi

    AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED=${AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED:="false"}
    check_if_docker_build_is_needed

    if [[ "${AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED}" == "true" ]]; then
        local SKIP_REBUILD="false"
        if [[ ${CI:=} != "true" ]]; then
            set +e
            if ! "${MY_DIR}/../../confirm" "The image might need to be rebuild."; then
               SKIP_REBUILD="true"
            fi
            set -e
        fi
        if [[ ${SKIP_REBUILD} != "true" ]]; then
            echo
            echo "Rebuilding image"
            echo
            # shellcheck source=../../hooks/build
            ./hooks/build | tee -a "${OUTPUT_LOG}"
            update_all_md5_files
            echo
            echo "Image rebuilt"
            echo
        fi
    else
        echo
        echo "No need to rebuild the image as none of the sensitive files changed: ${FILES_FOR_REBUILD_CHECK}"
        echo
    fi

    AIRFLOW_SLIM_CI_IMAGE=$(cat "${BUILD_CACHE_DIR}/.AIRFLOW_SLIM_CI_IMAGE")
    export AIRFLOW_SLIM_CI_IMAGE
}

function rebuild_image_if_needed_for_tests() {
    export AIRFLOW_CONTAINER_SKIP_SLIM_CI_IMAGE="true"
    export AIRFLOW_CONTAINER_SKIP_CHECKLICENCE_IMAGE="true"
    export AIRFLOW_CONTAINER_SKIP_CI_IMAGE="false"
    PYTHON_VERSION=${PYTHON_VERSION:=$(python -c \
        'import sys; print("%s.%s" % (sys.version_info.major, sys.version_info.minor))')}
    export PYTHON_VERSION
    AIRFLOW_VERSION=$(cat airflow/version.py - << EOF | python
print(version.replace("+",""))
EOF
    )
    export AIRFLOW_VERSION

    export THE_IMAGE="CI"
    if [[ -f "${BUILD_CACHE_DIR}/.built_${THE_IMAGE}_${PYTHON_VERSION}" ]]; then
        echo
        echo "Image built locally - skip force-pulling them"
        echo
    else
        echo
        echo "Image not built locally - force pulling them first"
        echo
        export AIRFLOW_CONTAINER_FORCE_PULL_IMAGES="true"
        export AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED="true"
    fi

    export DOCKERHUB_USER=${DOCKERHUB_USER:="apache"}
    export DOCKERHUB_REPO=${DOCKERHUB_REPO:="airflow"}
    export AIRFLOW_CONTAINER_PUSH_IMAGES="false"
    export AIRFLOW_CONTAINER_CI_OPTIMISED_BUILD="true"

    AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED=${AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED:="false"}
    check_if_docker_build_is_needed

    if [[ "${AIRFLOW_CONTAINER_DOCKER_BUILD_NEEDED}" == "true" ]]; then
        local SKIP_REBUILD="false"
        if [[ ${CI:=} != "true" ]]; then
            set +e
            if ! "${MY_DIR}/../../confirm" "The image might need to be rebuild."; then
               SKIP_REBUILD="true"
            fi
            set -e
        fi
        if [[ ${SKIP_REBUILD} != "true" ]]; then
            echo
            echo "Rebuilding image"
            echo
            # shellcheck source=../../hooks/build
            ./hooks/build | tee -a "${OUTPUT_LOG}"
            update_all_md5_files
            echo
            echo "Image rebuilt"
            echo
        fi
    else
        echo
        echo "No need to rebuild the image as none of the sensitive files changed: ${FILES_FOR_REBUILD_CHECK}"
        echo
    fi

    AIRFLOW_CI_IMAGE=$(cat "${BUILD_CACHE_DIR}/.AIRFLOW_CI_IMAGE")
    export AIRFLOW_CI_IMAGE
}

function rebuild_image_for_checklicence() {
    export AIRFLOW_CONTAINER_SKIP_SLIM_CI_IMAGE="true"
    export AIRFLOW_CONTAINER_SKIP_CHECKLICENCE_IMAGE="false"
    export AIRFLOW_CONTAINER_SKIP_CI_IMAGE="true"
    export AIRFLOW_CONTAINER_PUSH_IMAGES="false"

    export THE_IMAGE="CHECKLICENCE"
    echo
    echo "Rebuilding image"
    echo
    # shellcheck source=../../hooks/build
    ./hooks/build | tee -a "${OUTPUT_LOG}"
    update_all_md5_files
    echo
    echo "Image rebuilt"
    echo
    AIRFLOW_CHECKLICENCE_IMAGE=$(cat "${BUILD_CACHE_DIR}/.AIRFLOW_CHECKLICENCE_IMAGE")
    export AIRFLOW_CHECKLICENCE_IMAGE
}
#
# Starts the script/ If VERBOSE variable is set to true, it enables verbose output of commands executed
# Also prints some useful diagnostics information at start of the script
#
function script_start {
    echo
    echo "Running $(basename $0)"
    echo
    echo "Log is redirected to ${OUTPUT_LOG}"
    echo
    if [[ ${VERBOSE:=} == "true" ]]; then
        echo
        echo "Variable VERBOSE Set to \"true\""
        echo "You will see a lot of output"
        echo
        set -x
    else
        echo "You can increase verbosity by running 'export VERBOSE=\"true\""
        if [[ ${SKIP_CACHE_DELETION:=} != "true" ]]; then
            echo "And skip deleting the output file with 'export SKIP_CACHE_DELETION=\"true\""
        fi
        echo
    fi
    START_SCRIPT_TIME=$(date +%s)
}

#
# Disables verbosity in the script
#
function script_end {
    if [[ ${VERBOSE:=} == "true" ]]; then
        set +x
    fi
    END_SCRIPT_TIME=$(date +%s)
    RUN_SCRIPT_TIME=$((END_SCRIPT_TIME-START_SCRIPT_TIME))
    echo
    echo "Finished the script $(basename $0)"
    echo "It took ${RUN_SCRIPT_TIME} seconds"
    echo
}

function go_to_airflow_sources {
    echo
    pushd "${MY_DIR}/../../" &>/dev/null || exit 1
    echo
    echo "Running in host in $(pwd)"
    echo
}

#
# Performs basic sanity checks common for most of the scripts in this directory
#
function basic_sanity_checks() {
    assert_not_in_container
    go_to_airflow_sources
    check_if_coreutils_installed
    create_cache_directory
}
