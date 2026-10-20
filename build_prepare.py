r"""
Write the scripts that build the PyPy Windows dependencies.

    python3 build_prepare.py [options]

writes build\build_all.cmd, plus one build\build_<lib>.cmd per dependency,
and then each of those has to be run:

    cmd.exe /c build\build_all.cmd

Run with --help for the available options.
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from itertools import count


def cmd_cd(path):
    return "cd /D {path}".format(**locals())


def cmd_set(name, value):
    return "set {name}={value}".format(**locals())


def cmd_append(name, value):
    op = "path " if name == "PATH" else "set {name}="
    return (op + "%{name}%;{value}").format(**locals())


def cmd_copy(src, tgt):
    return 'copy /Y /B "{src}" "{tgt}"'.format(**locals())


def cmd_xcopy(src, tgt):
    return 'xcopy /Y /E /I "{src}" "{tgt}"'.format(**locals())


def cmd_nmake(makefile=None, target="", params=None):
    if params is None:
        params = ""
    elif isinstance(params, list) or isinstance(params, tuple):
        params = " ".join(params)
    else:
        params = str(params)

    return " ".join(
        [
            "{{nmake}}",
            "-nologo",
            '-f "{makefile}"' if makefile is not None else "",
            "{params}",
            '"{target}"',
        ]
    ).format(**locals())


architectures = {
    "x86": {
        "cpython_arch": "win32",
        "boehm_arch": "NT",
        "boehm_target": r"Release\gc",
        "xz_arch": "i486",
        "tcl_arch": "IX86",
        "vcvars_arch": "x86",
        "openssl_arch": "VC-WIN32",
    },
    "x64": {
        "cpython_arch": "amd64",
        "boehm_arch": "NT_X64",
        "boehm_target": r"gc64_dll",
        "xz_arch": "x86-64",
        "tcl_arch": "AMD64",
        "vcvars_arch": "x86_amd64",
        "openssl_arch": "VC-WIN64A-masm",
    },
}

header = [
    cmd_set("INCLUDE", "{inc_dir};{aux_dir}"),
    cmd_set("INCLIB", "{lib_dir}"),
    cmd_set("LIB", "{lib_dir}"),
    cmd_append("PATH", "{bin_dir}"),
]

# dependencies, listed in order of compilation
deps = {
    "boehm": {
        "url": "https://hboehm.info/gc/gc_source/gc-7.1.tar.gz",
        "filename": "gc-7.1.tar.gz",
        "dir": "gc-7.1",
        "patch": {
            r"misc.c": {
                "void GC_abort(const char *msg)\n"
                "{{\n"
                "#   if defined(MSWIN32)":
                    "void GC_abort(const char *msg)\n"
                    "{{\n"
                    "#   if 0",
            },
            r"include\private\gc_priv.h": {
                "# ifndef abs": "#if 0",
            },
            r"NT_X64_THREADS_MAKEFILE": {
                "cvarsmt": "cvarsdll",
            },
        },
        "build": [
            cmd_nmake("{boehm_arch}_THREADS_MAKEFILE", "CLEAN"),
            cmd_nmake("{boehm_arch}_THREADS_MAKEFILE", params="nodebug=1"),
        ],
        "headers": [r"include\gc.h", r"include\gc_config_macros.h", r"include\gc_version.h"],
        "libs": [r"{boehm_target}.lib"],
        "bins": [r"{boehm_target}.dll"],
    },
    "zlib": {
        "url": "https://zlib.net/zlib131.zip",
        "filename": "zlib131.zip",
        "dir": "zlib-1.3.1",
        "build": [
            cmd_nmake(r"win32\Makefile.msc", "clean"),
            cmd_nmake(r"win32\Makefile.msc"),
        ],
        "headers": ["zconf.h", "zlib.h", "zutil.h"],
        "libs": [r"zlib.lib"],
        "bins": [r"zlib1.dll"],
    },
    "zlib-ng": {
        # zlib replacement, built in zlib-compat mode so that it produces the
        # same zlib.lib and zlib1.dll as the "zlib" target above. Based on
        # https://github.com/python/cpython/pull/131438
        "url": "https://github.com/python/cpython-source-deps/archive/zlib-ng-2.2.4.zip",
        "filename": "zlib-ng-2.2.4.zip",
        "dir": "cpython-source-deps-zlib-ng-2.2.4",
        "build": [
            cmd_copy(r"{winbuild_dir}\zlib-ng.nmake", r"makefile.msc"),
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": ["zconf.h", "zlib.h", "zlib_name_mangling.h"],
        "libs": [r"zlib.lib"],
        "bins": [r"zlib1.dll"],
    },
    "bz2": {
        "url": "https://github.com/python/cpython-source-deps/archive/bzip2-1.0.8.zip",
        "filename": "bzip2-1.0.8.zip",
        "dir": "cpython-source-deps-bzip2-1.0.8",
        "build": [
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": [r"bzlib.h"],
        "libs": [r"libbz2.lib"],
    },
    "sqlite3": {
        "url": "https://sqlite.org/2022/sqlite-amalgamation-3400100.zip",
        "filename": "sqlite-amalgamation-3400100.zip",
        "dir": "sqlite-amalgamation-3400100",
        "build": [
            cmd_copy(r"{winbuild_dir}\sqlite3.nmake", r"makefile.msc"),
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": ["sqlite3.h", "sqlite3ext.h"],
        "libs": [r"sqlite3.lib"],
        "bins": [r"sqlite3.dll"],
    },
    "libexpat": {
        "url": "https://github.com/libexpat/libexpat/archive/R_2_5_0.zip",
        "filename": "R_2_5_0.zip",
        "dir": "libexpat-R_2_5_0",
        "patch": {
            r"expat\lib\xmltok.c": {
                "  const ptrdiff_t bytesStorable = toLim - *toP;\n":
                    "  const ptrdiff_t bytesStorable = toLim - *toP;\n"
                    "  const char * fromLimBefore;\n"
                    "  ptrdiff_t bytesToCopy;\n",
                "  const char * const fromLimBefore = fromLim;\n":
                    "  fromLimBefore = fromLim;\n",
                "  const ptrdiff_t bytesToCopy = fromLim - *fromP;\n":
                    "  bytesToCopy = fromLim - *fromP;\n",
            },
        },
        "build": [
            cmd_cd(r"expat"),
            "mkdir build",
            "cd build",
            "cmake ..",
            "cmake --build . --config Release",
        ],
        "headers": [r"..\lib\expat.h", r"..\lib\expat_external.h"],
        "libs": [r"Release\libexpat.lib"],
        "bins": [r"Release\libexpat.dll"],
    },
    "openssl-cpython": {
        # use pre-built OpenSSL from CPython
        "url": "https://github.com/python/cpython-bin-deps/archive/openssl-bin-3.5.9.tar.gz",
        "filename": "openssl-bin-3.5.9.tar.gz",
        "dir": "cpython-bin-deps-openssl-bin-3.5.9",
        "build": [
            cmd_xcopy(r"{cpython_arch}\include", "{inc_dir}"),
        ],
        "libs": [r"{cpython_arch}\lib*.lib"],
        "bins": [r"{cpython_arch}\lib*.dll"],
    },
    "lzma": {
        "url": "https://tukaani.org/xz/xz-5.0.5-windows.zip",
        "filename": "xz-5.0.5-windows.zip",
        "dir": "xz-5.0.5-windows",
        "dir-create": True,
        "build": [
            cmd_copy(r"bin_{xz_arch}\liblzma.a", r"bin_{xz_arch}\lzma.lib"),
            cmd_xcopy(r"include", "{inc_dir}"),
        ],
        "libs": [r"bin_{xz_arch}\lzma.lib"],
        "bins": [r"bin_{xz_arch}\liblzma.dll"],
    },
    "tcl": {
        "url": "https://prdownloads.sourceforge.net/tcl/tcl8.6.9-src.tar.gz",
        "filename": "tcl8.6.9-src.tar.gz",
        "dir": "tcl8.6.9",
        "build": [
            cmd_cd("win"),
            cmd_set("COMPILERFLAGS", "-DWINVER=0x0500"),
            cmd_set("DEBUG", "0"),
            cmd_set("INSTALLDIR", r"{tcltk_dir}"),
            cmd_set("MACHINE", "{tcl_arch}"),
            cmd_nmake("makefile.vc", "clean"),
            cmd_nmake("makefile.vc", "all"),
            cmd_nmake("makefile.vc", "install"),
            cmd_xcopy(r"{tcltk_dir}\lib\tcl8.6", r"{lib_dir}\tcl8.6")
        ],
        "headers": [r"{tcltk_dir}\include\*.h"],
        "libs": [r"{tcltk_dir}\lib\tcl*.lib"],
        "bins": [r"{tcltk_dir}\bin\tcl*.dll"],
    },
    "tk": {
        "url": "https://prdownloads.sourceforge.net/tcl/tk8.6.9.1-src.tar.gz",
        "filename": "tk8.6.9.1-src.tar.gz",
        "dir": "tk8.6.9",
        "build": [
            cmd_cd("win"),
            cmd_set("COMPILERFLAGS", "-DWINVER=0x0500"),
            cmd_set("DEBUG", "0"),
            cmd_set("INSTALLDIR", r"{tcltk_dir}"),
            cmd_set("MACHINE", "{tcl_arch}"),
            cmd_set("TCLDIR", r"{build_dir}\tcl8.6.9"),
            cmd_nmake("makefile.vc", "clean"),
            cmd_nmake("makefile.vc", "all"),
            cmd_nmake("makefile.vc", "install"),
            cmd_xcopy(r"{tcltk_dir}\include\X11", r"{inc_dir}\X11"),
            cmd_xcopy(r"{tcltk_dir}\lib\tk8.6", r"{lib_dir}\tk8.6")
        ],
        "headers": [r"{tcltk_dir}\include\tk*.h"],
        "libs": [r"{tcltk_dir}\lib\tk*.lib"],
        "bins": [r"{tcltk_dir}\bin\tk*.dll"],
    },
}


# based on setuptools._distutils._msvccompiler version 50.0.0
def find_msvs2015():
    import winreg
    try:
        key = winreg.OpenKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\VisualStudio\SxS\VC7",
            access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
        )
    except OSError:
        print("Visual Studio not found in registry")
        return None

    with key:
        for i in count():
            try:
                v, vc_dir, vt = winreg.EnumValue(key, i)
            except OSError:
                print("Visual Studio 2015 not found")
                return None
            if v and vt == winreg.REG_SZ and os.path.isdir(vc_dir):
                try:
                    version = int(float(v))
                except (ValueError, TypeError):
                    continue
                if version == 14:
                    vspath = vc_dir
                    break

    vs = {
        "header": [],
        # nmake selected by vcvarsall
        "nmake": "nmake.exe",
        "vs_dir": vspath,
    }

    vcvarsall = os.path.join(vspath, "vcvarsall.bat")
    if not os.path.isfile(vcvarsall):
        print("Visual Studio vcvarsall not found")
        return None
    # ask for SDK 8.1, default SDK 10 is missing RC.exe
    vs["header"].append('call "{}" {{vcvars_arch}} 8.1'.format(vcvarsall))

    return vs


# based on distutils._msvccompiler from CPython 3.7.4
def find_msvs():
    root = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    if not root:
        print("Program Files not found")
        return None

    try:
        vspath = (
            subprocess.check_output(
                [
                    os.path.join(
                        root, "Microsoft Visual Studio", "Installer", "vswhere.exe"
                    ),
                    "-latest",
                    "-prerelease",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                    "-products",
                    "*",
                ]
            )
            .decode(encoding="mbcs")
            .strip()
        )
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError):
        print("vswhere not found")
        return None

    if not os.path.isdir(os.path.join(vspath, "VC", "Auxiliary", "Build")):
        print("Visual Studio seems to be missing C compiler")
        return None

    vs = {
        "header": [],
        # nmake selected by vcvarsall
        "nmake": "nmake.exe",
        "vs_dir": vspath,
    }

    vcvarsall = os.path.join(vspath, "VC", "Auxiliary", "Build", "vcvarsall.bat")
    if not os.path.isfile(vcvarsall):
        print("Visual Studio vcvarsall not found")
        return None
    # you can specify an SDK version here if building Tcl/Tk 8.5 with VS 2017+
    vs["header"].append('call "{}" {{vcvars_arch}}'.format(vcvarsall))

    return vs


def copy_win32mak():
    import winreg
    try:
        key = winreg.OpenKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\Microsoft SDKs\Windows",
            access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
        )
    except OSError:
        print("Windows SDKs not found in registry")
        return None

    with key:
        for i in count():
            try:
                v = winreg.EnumKey(key, i)
            except OSError:
                print("ntwin32.mak or win32.mak not found in installed SDKs")
                return None
            with winreg.OpenKeyEx(
                key, v, access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY
            ) as subkey:
                sdk_dir, vt = winreg.QueryValueEx(subkey, "InstallationFolder")
                if vt == winreg.REG_SZ:
                    sdk_include_dir = os.path.join(sdk_dir, "Include")
                    tgts = ["Win32.Mak", "NtWin32.Mak"]
                    ops = [(os.path.join(sdk_include_dir, t), os.path.join(aux_dir, t)) for t in tgts]
                    if all(os.path.isfile(a) for a, b in ops):
                        for a, b in ops:
                            shutil.copyfile(a, b)
                        return v


def extract_dep(url, filename, dir=None):
    import urllib.request
    import tarfile
    import zipfile

    file = os.path.join(depends_dir, filename)
    if not os.path.exists(file):
        ex = None
        for i in range(3):
            try:
                print("Fetching %s (attempt %d)..." % (url, i + 1))
                content = urllib.request.urlopen(url).read()
                with open(file, "wb") as f:
                    f.write(content)
                break
            except urllib.error.URLError as e:
                ex = e
        else:
            raise RuntimeError(ex)

    print("Extracting " + filename)
    if dir:
        dir = os.path.join(build_dir, dir)
    else:
        dir = build_dir
    if filename.endswith(".zip"):
        with zipfile.ZipFile(file) as zf:
            zf.extractall(dir)
    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        with tarfile.open(file, "r:gz") as tgz:
            tgz.extractall(dir)
    else:
        raise RuntimeError("Unknown archive type: " + filename)


def write_script(name, lines):
    name = os.path.join(build_dir, name)
    lines = [line.format(**prefs) for line in lines]
    print("Writing " + name)
    with open(name, "w") as f:
        f.write("\n".join(lines))
    if verbose:
        for line in lines:
            print("    " + line)


def get_footer(dep):
    lines = []
    for out in dep.get("headers", []):
        lines.append(cmd_copy(out, "{inc_dir}"))
        lines.append("@if errorlevel 1 exit /B 1")
    for out in dep.get("libs", []):
        lines.append(cmd_copy(out, "{lib_dir}"))
        lines.append("@if errorlevel 1 exit /B 1")
    for out in dep.get("bins", []):
        lines.append(cmd_copy(out, "{bin_dir}"))
        lines.append("@if errorlevel 1 exit /B 1")
    return lines


def build_dep(name):
    dep = deps[name]
    dir = dep["dir"]
    file = "build_{name}.cmd".format(**locals())

    extract_dep(dep["url"], dep["filename"], dep["dir"] if dep.get("dir-create", False) else None)

    for patch_file, patch_list in dep.get("patch", {}).items():
        if verbose:
            print("Patching " + patch_file)
        patch_file = os.path.join(build_dir, dir, patch_file.format(**prefs))
        with open(patch_file, "r") as f:
            text = f.read()
        for patch_from, patch_to in patch_list.items():
            text = text.replace(patch_from.format(**prefs), patch_to.format(**prefs))
        with open(patch_file, "w") as f:
            f.write(text)

    banner = "Building {name} ({dir})".format(**locals())
    lines = [
        "@echo " + ("=" * 70),
        "@echo ==== {:<60} ====".format(banner),
        "@echo " + ("=" * 70),
        "cd /D %s" % os.path.join(build_dir, dir),
        *prefs["header"],
        *dep.get("build", []),
        *get_footer(dep),
    ]

    write_script(file, lines)
    return file


def build_all():
    lines = ["@echo on"]
    enabled = []
    skipped = []
    for dep_name in deps:
        if dep_name in disabled:
            skipped.append(dep_name)
            continue
        enabled.append(dep_name)
        lines.append(r'cmd.exe /c "{{build_dir}}\{}"'.format(build_dep(dep_name)))
        lines.append("@if errorlevel 1 @echo Build failed! && exit /B 1")
    lines.append("@echo All PyPy dependencies built successfully!")
    write_script("build_all.cmd", lines)

    print()
    print("Finished writing scripts for: " + ", ".join(enabled))
    print("Skipped disabled targets: " + ", ".join(skipped))


def parse_args(argv=None):
    winbuild_dir = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="dependencies, in build order:\n"
               "    " + ", ".join(deps) + "\n\n"
               "All of them are built by default, except for zlib: zlib-ng\n"
               "replaces it unless --zlib is given. Tcl/Tk are skipped as well\n"
               "when Visual Studio 2015 is not installed, see --with-tk.\n",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="echo the generated scripts while writing them")
    parser.add_argument(
        "--only", metavar="LIB", action="append", default=[],
        help="write a script for LIB only instead of for every dependency. "
             "May be repeated, and takes a comma-separated list. This "
             "overrides the defaults, so it also builds a dependency that is "
             "off by default, and it keeps the existing build directory "
             "instead of wiping it, so that sources extracted by an earlier "
             "run are reused. Pick from: " + ", ".join(deps))
    parser.add_argument(
        "--architecture", choices=sorted(architectures), default="x64",
        help="target architecture (default: %(default)s)")
    parser.add_argument(
        "--dir", metavar="DIR", dest="build_dir",
        default=os.path.join(winbuild_dir, "build"),
        help="directory to write the build scripts to "
             "(default: %(default)s)")
    parser.add_argument(
        "--depends", metavar="DIR", dest="depends_dir",
        default=os.path.join(winbuild_dir, "cache"),
        help="directory to cache the downloaded archives in "
             "(default: %(default)s)")
    parser.add_argument(
        "--zlib", action="store_true",
        help="build zlib instead of zlib-ng")
    parser.add_argument(
        "--openssl", action="store_true",
        help="do not use CPython's prebuilt OpenSSL. NOTE: this script has no "
             "from-source OpenSSL target, so this currently means no OpenSSL "
             "at all")
    parser.add_argument(
        "--with-tk", action="store_true",
        help="build Tcl/Tk with Visual Studio 2017 or later too, see the "
             "warning this script prints when it skips them")
    parser.add_argument(
        "--no-boehm", action="store_true",
        help="skip the Boehm GC, which needs a Windows XP or older SDK")
    args = parser.parse_args(argv)

    args.winbuild_dir = winbuild_dir
    args.build_dir = os.path.abspath(args.build_dir)
    args.depends_dir = os.path.abspath(args.depends_dir)

    # --only takes repeated and comma-separated names
    only = []
    for value in args.only:
        for name in value.split(","):
            name = name.strip()
            if not name:
                continue
            if name not in deps:
                parser.error(
                    "unknown dependency %r for --only, pick from: %s"
                    % (name, ", ".join(deps))
                )
            if name not in only:
                only.append(name)
    args.only = only

    return args


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This script requires Python 3.6+")

    args = parse_args()
    verbose = args.verbose
    winbuild_dir = args.winbuild_dir
    build_dir = args.build_dir
    depends_dir = args.depends_dir
    architecture = args.architecture
    force_tk = args.with_tk

    # targets that are not built, by name in deps
    disabled = ["zlib-ng" if args.zlib else "zlib"]
    if args.openssl:
        disabled.append("openssl-cpython")
    if args.no_boehm:
        disabled.append("boehm")

    # dependency cache directory
    os.makedirs(depends_dir, exist_ok=True)
    print("Caching dependencies in:", depends_dir)

    arch_prefs = architectures[architecture]
    print("Target Architecture:", architecture)

    skipped_tk = False
    msvs = find_msvs2015()
    if msvs is None:
        msvs = find_msvs()
        if not force_tk:
            # see warning below
            disabled.extend(["tcl", "tk"])
            skipped_tk = True
    if msvs is None:
        raise RuntimeError(
            "Visual Studio not found. Please install Visual Studio 2015 or newer."
        )
    print("Found Visual Studio at:", msvs["vs_dir"])

    if args.only:
        # an explicit list of targets overrides every default above
        disabled = [name for name in deps if name not in args.only]
        skipped_tk = False

    print("Using output directory:", build_dir)

    # build directory for *.h files
    inc_dir = os.path.abspath("include")
    # build directory for *.lib files
    lib_dir = os.path.abspath("lib")
    # build directory for *.bin files
    bin_dir = os.path.abspath("bin")
    # build directory for auxiliary include files (win32.mak)
    aux_dir = os.path.join(build_dir, "auxiliary")

    tcltk_dir = os.path.join(build_dir, "tcltk")

    def rmtree_onerror(fn, path, excinfo):
        if excinfo[0] is PermissionError and excinfo[1].winerror == 5:
            os.chmod(path, stat.S_IWRITE)
            fn(path)
        else:
            raise

    if os.path.isdir(build_dir) and not args.only:
        shutil.rmtree(build_dir, onerror=rmtree_onerror)
    for path in [build_dir, inc_dir, lib_dir, bin_dir, aux_dir, tcltk_dir]:
        if not os.path.exists(path):
            os.makedirs(path)

    prefs = {
        # Target architecture
        "architecture": architecture,
        **arch_prefs,
        # Build paths
        "winbuild_dir": winbuild_dir,
        "build_dir": build_dir,
        "inc_dir": inc_dir,
        "lib_dir": lib_dir,
        "bin_dir": bin_dir,
        "aux_dir": aux_dir,
        "tcltk_dir": tcltk_dir,
        # Compilers / Tools
        **msvs,
        # script header
        "header": sum([header, msvs["header"], ["@echo on"]], []),
    }

    print()
    write_script(
        ".gitignore",
        [
            "/*",
            "!/bin",
            "!/bin/*.dll",
            "!/lib",
            "!/lib/*.lib",
            "!/include",
        ],
    )

    build_all()

    if "boehm" not in disabled:
        print()
        xp_sdk = copy_win32mak()
        if xp_sdk is None:
            print("!!! ntwin32.mak or win32.mak not found, required by Boehm GC.")
            print("!!! Install Windows XP support in VS2015 or older and rerun %s, "
                  "or copy win32.mak and ntwin32.mak to '%s' before running build_all.cmd."
                  % (os.path.basename(__file__), aux_dir))
            print("!!! You can skip Boehm GC compilation by running '%s --no-boehm'."
                  % os.path.basename(__file__))
        else:
            print("Copied ntwin32.mak and win32.mak from Windows SDK %s" % xp_sdk)

    if skipped_tk:
        print()
        print("!!! Building Tcl/Tk is disabled for Visual Studio 2017 or later, "
              "because Tk 8.5.2 requires Win SDK <= 10.0.15063.0, which is not available by default. "
              "See https://core.tcl-lang.org/tk/tktview?name=3d34589aa0 for more information.")
        print("!!! You can force Tcl/Tk compilation by running '%s --with-tk'. "
              "You may have to specify the target SDK version in the function 'find_msvs()' "
              "by replacing 'call \"{}\" {{vcvars_arch}}' with 'call \"{}\" {{vcvars_arch}} <sdk_version>'."
              % os.path.basename(__file__))

    if args.openssl:
        if shutil.which("perl") is None:
            print()
            print("!!! perl.exe not found in PATH, compiling OpenSSL might fail.")
