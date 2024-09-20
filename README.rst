Reproducing the binaries here
=============================

These binaries were produced with VS 14.0, i.e. Visual Studio 2017
but should work with VS 16.0 i.e. Visual Studio 2019 as well


The Boehm garbage collector
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This library is needed if you plan to use the ``--gc=boehm`` translation
option (this is the default at some optimization levels like ``-O1``,
but unneeded for high-performance translations like ``-O2``).
You may get it at
http://hboehm.info/gc/gc_source/gc-7.1.tar.gz

Versions 7.0 and 7.1 are known to work; the 6.x series won't work with
RPython. Unpack this folder in the base directory.
The default GC_abort(...) function in misc.c will try to open a MessageBox.
You may want to disable this with the following patch::

    --- a/misc.c    Sun Apr 20 14:08:27 2014 +0300
    +++ b/misc.c    Sun Apr 20 14:08:37 2014 +0300
    @@ -1058,7 +1058,7 @@
     #ifndef PCR
      void GC_abort(const char *msg)
       {
       -#   if defined(MSWIN32)
       +#   if 0 && defined(MSWIN32)
              (void) MessageBoxA(NULL, msg, "Fatal error in gc", MB_ICONERROR|MB_OK);
               #   else
                      GC_err_printf("%s\n", msg);

For VS14 I needed to comment out the `define abs` on line 1245 in
`include/privat/gc_priv.h`

Then open a "Developer Command Prompt"::

    cd gc-7.1
    nmake -f NT_THREADS_MAKEFILE
    copy Release\gc.dll <somewhere in the PATH>


The zlib compression library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download http://www.gzip.org/zlib/zlib-1.2.11.tar.gz and extract it in
the base directory.  Then compile::

    cd zlib-1.2.11
    nmake -f win32\Makefile.msc
    copy zlib.lib <somewhere in LIB>
    copy zlib.h zconf.h <somewhere in INCLUDE>
    copy zlib1.dll <in PATH> # (needed for tests via ll2ctypes)


The bz2 compression library
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Get the same version of bz2 used by python and compile as a static library::

    svn export http://svn.python.org/projects/external/bzip2-1.0.6
    cd bzip2-1.0.6
    nmake -f makefile.msc
    copy libbz2.lib <somewhere in LIB>
    copy bzlib.h <somewhere in INCLUDE>


The sqlite3 database library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the latest version from CPython and build the dll and lib::

    git clone https://github.com/python/cpython-source-deps
    cd cpython-source-deps
    git checkout sqlite
    cl -DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 \
       -DSQLITE_API=__declspec(dllexport) -LD sqlite3.c
    copy *.h <somewhere in INCLUDE>
    copy *.lib <somewhere in LIB>
    copy *.dll <somewhere in BIN>

The expat XML parser
~~~~~~~~~~~~~~~~~~~~

CPython compiles expat from source as part of the build. PyPy uses the same
code base, but expects to link to a static lib of expat. Here are instructions
to reproduce the static lib in version 2.2.4.

Download the source code of expat: https://github.com/libexpat/libexpat. 
``git checkout`` the proper tag, in this case ``R_2_2_4``. Run
``vcvars.bat`` to set up the visual compiler tools, and CD into the `Source/lib`
directory. Create a file ``stdbool.h`` with the content

.. code-block:: c

    #pragma once

    #define false   0
    #define true    1

    #define bool int

and put it in a place on the ``INCLUDE`` path, or create it in the local
directory and add ``.`` to the ``INCLUDE`` path::

    SET INCLUDE=%INCLUDE%;.

Then compile all the ``*.c`` file into ``*.obj``::

    cl.exe /nologo /MD  /O2 *c /c
    rem for debug
    cl.exe /nologo /MD  /O0 /Ob0 /Zi *c /c

You may need to move some variable declarations to the beginning of the
function, to be compliant with C89 standard. Here is the diff for version 2.2.4

.. code-block:: diff

    diff --git a/expat/lib/xmltok.c b/expat/lib/xmltok.c
    index 007aed0..a2dcaad 100644
    --- a/expat/lib/xmltok.c
    +++ b/expat/lib/xmltok.c
    @@ -399,19 +399,21 @@ utf8_toUtf8(const ENCODING *UNUSED_P(enc),
       /* Avoid copying partial characters (due to limited space). */
       const ptrdiff_t bytesAvailable = fromLim - *fromP;
       const ptrdiff_t bytesStorable = toLim - *toP;
    +  const char * fromLimBefore;
    +  ptrdiff_t bytesToCopy;
       if (bytesAvailable > bytesStorable) {
         fromLim = *fromP + bytesStorable;
         output_exhausted = true;
       }

       /* Avoid copying partial characters (from incomplete input). */
    -  const char * const fromLimBefore = fromLim;
    +  fromLimBefore = fromLim;
       align_limit_to_full_utf8_characters(*fromP, &fromLim);
       if (fromLim < fromLimBefore) {
         input_incomplete = true;
       }

    -  const ptrdiff_t bytesToCopy = fromLim - *fromP;
    +  bytesToCopy = fromLim - *fromP;
       memcpy((void *)*toP, (const void *)*fromP, (size_t)bytesToCopy);
       *fromP += bytesToCopy;
       *toP += bytesToCopy;


Create ``libexpat.lib`` (for translation) and ``libexpat.dll`` (for tests)::

    cl /LD *.obj libexpat.def /Felibexpat.dll 
    rem for debug
    rem cl /LDd /Zi *.obj libexpat.def /Felibexpat.dll

    rem this will override the export library created in the step above
    rem but tests do not need the export library, they load the dll dynamically
    lib *.obj /out:libexpat.lib

Then, copy 

- ``libexpat.lib`` into LIB
- both ``lib\expat.h`` and ``lib\expat_external.h`` in INCLUDE
- ``libexpat.dll`` into PATH


The OpenSSL library
~~~~~~~~~~~~~~~~~~~

OpenSSL is built by CPython, so use their version:

    git clone https://github.com/python/cpython-bin-deps.git
    cd cpython-bin-deps
    git checkout openssl-bin
    cd win32\include
    xcopy openssl  thisdir\include /s
For tests you will also need the dlls::
    nmake -f ms\ntdll.mak install
    copy out32dll\*.dll <somewhere in PATH>

TkInter module support
~~~~~~~~~~~~~~~~~~~~~~

Note that much of this is taken from the cpython build process.
Tkinter is imported via cffi, so the module is optional. To recreate the tcltk
directory found for the release script, create the dlls, libs, headers and
runtime by running::

    svn export http://svn.python.org/projects/external/tcl-8.5.2.1 tcl85
    svn export http://svn.python.org/projects/external/tk-8.5.2.0 tk85
    cd tcl85\win
    nmake -f makefile.vc COMPILERFLAGS=-DWINVER=0x0500 DEBUG=0 INSTALLDIR=..\..\tcltk clean all
    nmake -f makefile.vc DEBUG=0 INSTALLDIR=..\..\tcltk install
    cd ..\..\tk85\win
    nmake -f makefile.vc COMPILERFLAGS=-DWINVER=0x0500 OPTS=noxp DEBUG=1 INSTALLDIR=..\..\tcltk TCLDIR=..\..\tcl85 clean all
    nmake -f makefile.vc COMPILERFLAGS=-DWINVER=0x0500 OPTS=noxp DEBUG=1 INSTALLDIR=..\..\tcltk TCLDIR=..\..\tcl85 install
    copy ..\..\tcltk\bin\* <somewhere in PATH>
    copy ..\..\tcltk\lib\*.lib <somewhere in LIB>
    xcopy /S ..\..\tcltk\include <somewhere in INCLUDE>

The lzma compression library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.3 ship with CFFI wrappers for the lzma library, which can be
downloaded from this site http://tukaani.org/xz. Python 3.3-3.5 use version
5.0.5, a prebuilt version can be downloaded from
http://tukaani.org/xz/xz-5.0.5-windows.zip, check the signature
http://tukaani.org/xz/xz-5.0.5-windows.zip.sig

Then copy the headers to the include directory, rename ``liblzma.a`` to 
``lzma.lib`` and copy it to the lib directory

Note that the libeay32.dll and ssleay32.dll files are for testing only,
PyPy will statically link to libeay32.lib and ssleay32.lib
