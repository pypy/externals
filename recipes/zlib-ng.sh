#!/bin/bash
# zlib-ng built in zlib-compat mode: a drop-in replacement for zlib (same
# API/ABI) with SIMD-accelerated deflate/inflate/crc32.  The windows branches
# build the same source into zlib.lib/zlib1.dll; here we build a static libz.a
# so that nothing has to be shipped alongside the pypy binary and no
# @rpath/install_name fixups are needed at packaging time.
#
# Based on https://github.com/pypy/pypy-ci/blob/main/docker/install_zlib_ng.sh
set -xeo pipefail
. "$(dirname "$0")/../common.sh"

VERSION="2.3.3"
SHA256="f9c65aa9c852eb8255b636fd9f07ce1c406f061ec19a2e7d508b318ca0c907d1"

TARBALL="zlib-ng-${VERSION}.tar.gz"
fetch "https://github.com/zlib-ng/zlib-ng/archive/refs/tags/${VERSION}.tar.gz" \
      "${TARBALL}" "${SHA256}"
srcdir=$(unpack "${TARBALL}" "zlib-ng-${VERSION}")

pushd "${srcdir}"
# No --native: the SIMD paths are selected at runtime, so one build runs on
# every arm64 mac.
CFLAGS="${EXTERNALS_CFLAGS}" ./configure \
    --zlib-compat \
    --static \
    --prefix="${PREFIX}" \
    --libdir="${PREFIX}/lib" \
    --includedir="${PREFIX}/include"
make -j"${JOBS}"
# 'make test' also builds the shared-library tests, which a --static build has
# no library for.  Run the static zlib test suite instead.
make -C test teststatic
make install
popd

# The generated zlib.pc has this machine's absolute PREFIX baked into it, which
# would be wrong for everyone else checking out this branch.  The headers and
# libz.a are what gets committed.
rm -f "${PREFIX}/lib/pkgconfig/zlib.pc"
rmdir "${PREFIX}/lib/pkgconfig" 2>/dev/null || true
rm -rf "${PREFIX}/share/man/man3/zlib.3"
rmdir -p "${PREFIX}/share/man/man3" 2>/dev/null || true

ls -l "${PREFIX}/lib/libz.a"
