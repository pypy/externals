External dependencies for building PyPy on macOS x86_64
=======================================================

This branch holds the prebuilt headers and libraries PyPy needs that are not
part of the macOS SDK, or where the system copy is too old or too slow.  It is
the macOS analogue of the ``win64_14x`` branch: ``get_externals.py`` in the
PyPy checkout clones this repo into ``<pypy>/externals`` at the branch named by
the platform (``macos-x86-64`` here, see ``externals_branch`` in
``rpython/translator/platform/darwin.py``), and the buildbot runs it as the
"fetch external dependencies" step before translating.  The darwin platform
support then puts ``externals/include`` and ``externals/lib`` first on the
compiler's search path, so these copies shadow the SDK and any homebrew
installation.

The committed layout is therefore::

    include/        headers, added to the include path
    lib/            static libraries, added to the library path

Rebuilding
----------

The builds are driven by bash, no Python needed::

    ./build.sh                 # build everything, in dependency order
    ./build.sh --only zlib-ng  # build one (comma-separated) dependency
    ./build.sh --jobs 4        # limit parallelism
    ./build.sh --help

Each dependency is one script in ``recipes/``, and each one is also runnable on
its own (``./recipes/zlib-ng.sh``).  ``common.sh`` holds the shared download /
unpack / flag setup; every variable in it can be overridden from the
environment, e.g. ``PREFIX=/tmp/stage ./recipes/zlib-ng.sh`` to build without
touching the committed ``include/`` and ``lib/``.

Sources are downloaded (with a checksum check) and unpacked under ``build/``,
which is not committed.  The results are installed straight into ``include/``
and ``lib/``, so after a successful run ``git status`` shows exactly what
changed, and committing that is the way to publish a new build.

Everything is built with ``-arch arm64 -mmacosx-version-min=11.0``; keep that
deployment target in sync with ``DARWIN_VERSION_MIN`` in
``rpython/translator/platform/darwin.py`` and ``lib_pypy/_sysconfigdata.py``.

Dependencies
------------

zlib-ng
    Built in zlib-compat mode, which gives the same API/ABI as zlib with
    SIMD-accelerated deflate/inflate/crc32, as on the windows branches and in
    the linux docker images (see ``docker/install_zlib_ng.sh`` in the pypy-ci
    repo, which this recipe is based on).  Unlike those two, the macOS build is
    a static ``libz.a``: nothing has to be shipped next to the pypy binary and
    no ``install_name``/``@rpath`` fixups are needed at packaging time.  The
    recipe runs zlib's own test suite (``make -C test teststatic``) before
    installing.

    Note that ``rpython/rlib/test/test_rzlib.py::test_translate_and_large_input``
    compares compressed bytes against the *host* interpreter's ``zlib`` module,
    so it only passes if the host interpreter is linked against zlib-ng too
    (as it is on the buildbot).  zlib-ng's deflate output is valid but not
    byte-identical to zlib's.
