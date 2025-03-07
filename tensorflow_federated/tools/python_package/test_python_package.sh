#!/usr/bin/env bash
# Copyright 2019, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Tool to test the TensorFlow Federated pip package.
set -e

script="$(readlink -f "$0")"
script_dir="$(dirname "${script}")"
source "${script_dir}/common.sh"

usage() {
  local script_name=$(basename "${0}")
  local options=(
      "--package=<path>"
  )
  echo "usage: ${script_name} ${options[@]}"
  echo "  --package=<path>  A path to a local pip package."
  exit 1
}

main() {
  # Parse arguments
  local package=""

  while [[ "$#" -gt 0 ]]; do
    option="$1"
    case "${option}" in
      --package=*)
        package="${option#*=}"
        shift
        ;;
      *)
        error_unrecognized "${option}"
        usage
        ;;
    esac
  done

  if [[ -z "${package}" ]]; then
    error_required "--package"
    usage
  elif [[ ! -f "${package}" ]]; then
    error_file_does_not_exist "${package}"
    usage
  fi

  # Create working directory
  local temp_dir="$(mktemp -d)"
  trap "rm -rf ${temp_dir}" EXIT
  pushd "${temp_dir}"

  # Create a virtual environment
  python3.9 -m venv "venv"
  source "venv/bin/activate"
  python --version
  pip install --upgrade pip
  pip --version

  # Test pip package
  pip install --upgrade "${package}"
  pip freeze
  python -c "import tensorflow_federated as tff; print(tff.federated_computation(lambda: 'Hello World')())"

  # Cleanup
  deactivate
  popd
}

main "$@"
