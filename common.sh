# Shared helpers for the macOS externals build recipes.  Sourced, not run:
#
#     . "$(dirname "$0")/../common.sh"
#
# Everything is overridable from the environment, so that a recipe can be run
# standalone, e.g. PREFIX=/tmp/foo ./recipes/zlib-ng.sh

# Root of this repo (the directory holding common.sh).
EXTERNALS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Where the built headers and libraries end up.  The layout is <PREFIX>/include
# and <PREFIX>/lib, matching the windows branches, so that pointing
# PYPY_LOCALBASE (or rpython's darwin platform support) at it just works.
: "${PREFIX:=${EXTERNALS_ROOT}}"

# Scratch space: downloaded tarballs and unpacked sources.  Not committed.
: "${BUILD_DIR:=${EXTERNALS_ROOT}/build}"
: "${DOWNLOAD_DIR:=${BUILD_DIR}/download}"
: "${SRC_DIR:=${BUILD_DIR}/src}"

: "${ARCH:=$(uname -m)}"
# arm64 macOS starts at 11.0; keep in sync with DARWIN_VERSION_MIN in
# rpython/translator/platform/darwin.py and lib_pypy/_sysconfigdata.py.
if [ "${ARCH}" = "arm64" ]; then
    : "${MACOSX_DEPLOYMENT_TARGET:=11.0}"
else
    : "${MACOSX_DEPLOYMENT_TARGET:=10.13}"
fi
export MACOSX_DEPLOYMENT_TARGET

: "${JOBS:=$(sysctl -n hw.ncpu)}"

# Flags every dependency is built with.  -fPIC because the libraries get linked
# into pypy's shared libpypy-c.dylib as well as into the pypy executable.
: "${EXTERNALS_CFLAGS:=-O2 -fPIC -arch ${ARCH} -mmacosx-version-min=${MACOSX_DEPLOYMENT_TARGET}}"

mkdir -p "${DOWNLOAD_DIR}" "${SRC_DIR}" "${PREFIX}/include" "${PREFIX}/lib"

# fetch <url> <filename> <sha256>
# Download into DOWNLOAD_DIR unless already there, then verify the checksum.
fetch() {
    local url="$1" filename="$2" sha256="$3"
    if [ ! -f "${DOWNLOAD_DIR}/${filename}" ]; then
        curl -sS -L "${url}" -o "${DOWNLOAD_DIR}/${filename}.part"
        mv "${DOWNLOAD_DIR}/${filename}.part" "${DOWNLOAD_DIR}/${filename}"
    fi
    # macOS has shasum, not sha256sum
    echo "${sha256}  ${DOWNLOAD_DIR}/${filename}" | shasum -a 256 -c -
}

# unpack <filename> <dirname>
# Unpack DOWNLOAD_DIR/<filename> into SRC_DIR, removing a previous
# SRC_DIR/<dirname> first so every build starts from pristine sources.
# Echoes the path of the unpacked source directory.
unpack() {
    local filename="$1" dirname="$2"
    rm -rf "${SRC_DIR}/${dirname}"
    tar -x -f "${DOWNLOAD_DIR}/${filename}" -C "${SRC_DIR}"
    test -d "${SRC_DIR}/${dirname}"
    echo "${SRC_DIR}/${dirname}"
}
