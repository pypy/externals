#!/bin/bash
# Build the external dependencies PyPy needs on macOS, installing the headers
# and libraries into this repo's include/ and lib/ directories.
#
#     ./build.sh                      # build everything
#     ./build.sh --only zlib-ng       # build one (comma-separated) dependency
#     ./build.sh --jobs 4             # limit parallelism
#
# Each recipe in recipes/ is also runnable on its own; see common.sh for the
# environment variables they honour.
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# Dependencies, in build order.
RECIPES=(zlib-ng)

usage() {
    sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
    echo "available recipes: ${RECIPES[*]}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --only)
            IFS=, read -r -a RECIPES <<< "$2"
            shift 2
            ;;
        --only=*)
            IFS=, read -r -a RECIPES <<< "${1#*=}"
            shift
            ;;
        --jobs|-j)
            export JOBS="$2"
            shift 2
            ;;
        --jobs=*)
            export JOBS="${1#*=}"
            shift
            ;;
        --prefix)
            export PREFIX="$2"
            shift 2
            ;;
        --prefix=*)
            export PREFIX="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

for recipe in "${RECIPES[@]}"; do
    if [ ! -x "${HERE}/recipes/${recipe}.sh" ]; then
        echo "no such recipe: ${recipe}" >&2
        exit 2
    fi
done

for recipe in "${RECIPES[@]}"; do
    echo "=== building ${recipe} ==="
    "${HERE}/recipes/${recipe}.sh"
done

echo "=== done: ${RECIPES[*]} ==="
