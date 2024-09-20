Reproducing the binaries here
=============================

To recompile all binaries, run the ``build_prepare.py`` script in CPython 3.6+,
then the generated script ``build\build_all.cmd``. After running the script,
it is necessary to copy the directories ``bin``, ``lib``, and ``include``
from the generated subdirectory ``build`` to this root directory.

This script is based on the instructions in the ``win64_14x`` branch.

Due to https://core.tcl-lang.org/tk/tktview?name=3d34589aa0, the script will
prefer Visual Studio 2015 if available. It may be necessary to modify the script
if only a newer Visual Studio version is available.

It is also necessary to have at least one Windows XP or older SDK installed
to build the (optional) Boehm GC.

The binaries in this branch were built using Visual Studio 2022 Community
version 14.0.25431.01 Update 3, and are compatible with any VS2015, VS2017, or VS2019 compiler,
see https://docs.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017?view=vs-2019.

The libffi build was done separately using the
``cpython\PCbuild\prepare_libffi.bat`` script::

    prepare_libffi.bat --install-cygwin
    rem clone libffi (be sure to convert line endings to unix, dos will fail)
    set LIBFFI_SOURCE=path/to/libffisource
    set VCVARSALL=path/to/vcvarsall.bat
    prepare_libffi.bat -x64

This builds the library as a dll and copies the results to
``cpython\externals\libffi\amd64``
