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
        "url": "https://www.hboehm.info/gc/gc_source/gc-7.1.tar.gz",
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
        "url": "https://zlib.net/zlib1211.zip",
        "filename": "zlib1211.zip",
        "dir": "zlib-1.2.11",
        "build": [
            cmd_nmake(r"win32\Makefile.msc", "clean"),
            cmd_nmake(r"win32\Makefile.msc"),
        ],
        "headers": [r"z*.h"],
        "libs": [r"zlib.lib"],
        "bins": [r"zlib1.dll"],
    },
    "bz2": {
        "url": "https://github.com/python/cpython-source-deps/archive/bzip2-1.0.6.zip",
        "filename": "bzip2-1.0.6.zip",
        "dir": "cpython-source-deps-bzip2-1.0.6",
        "build": [
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": [r"bzlib.h"],
        "libs": [r"libbz2.lib"],
    },
    "sqlite3": {
        "url": "https://sqlite.org/2021/sqlite-amalgamation-3350500.zip",
        "filename": "sqlite-amalgamation-3350500.zip",
        "dir": "sqlite-amalgamation-3350500",
        "build": [
            cmd_copy(r"{winbuild_dir}\sqlite3.nmake", r"makefile.msc"),
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": [r"sql*.h"],
        "libs": [r"*.lib"],
        "bins": [r"*.dll"],
    },
    "libexpat": {
        "url": "https://github.com/libexpat/libexpat/archive/R_2_2_4.zip",
        "filename": "R_2_2_4.zip",
        "dir": "libexpat-R_2_2_4",
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
            cmd_cd(r"expat\lib"),
            cmd_copy(r"{winbuild_dir}\libexpat.nmake", r"makefile.msc"),
            cmd_nmake(r"makefile.msc", "clean"),
            cmd_nmake(r"makefile.msc"),
        ],
        "headers": [r"expat.h", r"expat_external.h"],
        "libs": [r"libexpat.lib"],
        "bins": [r"libexpat.dll"],
    },
    "openssl-cpython": {
        # use pre-built OpenSSL from CPython
        "url": "https://github.com/python/cpython-bin-deps/archive/openssl-bin-1.1.1g.tar.gz",
        "filename": "openssl-bin-1.1.1g.tar.gz",
        "dir": "cpython-bin-deps-openssl-bin-1.1.1g",
        "build": [
            cmd_xcopy(r"{cpython_arch}\include", "{inc_dir}"),
        ],
        "libs": [r"{cpython_arch}\lib*.lib"],
        "bins": [r"{cpython_arch}\lib*.dll"],
    },
    "openssl": {
        "url": "https://www.openssl.org/source/openssl-1.1.1k.tar.gz",
        "filename": "openssl-1.1.1k.tar.gz",
        "dir": "openssl-1.1.1k",
        "build": [
            "perl configure {openssl_arch} no-asm",
            cmd_nmake(),
            cmd_xcopy(r"include\openssl", "{inc_dir}\openssl"),
        ],
        "libs": [r"libcrypto.lib", r"libssl.lib"],
        "bins": [r"libcrypto-1_1.dll", r"libssl-1_1.dll"],
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
            cmd_set("TCLDIR", r"{build_dir}\tcl8.6.9"),
            cmd_set("MACHINE", "{tcl_arch}"),
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
    # You can find it https://developer.microsoft.com/en-us/windows/downloads/sdk-archive/ 
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


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This script requires Python 3.6+")

    # root directory
    winbuild_dir = os.path.dirname(os.path.realpath(__file__))

    verbose = False
    disabled = ["openssl-cpython"]
    depends_dir = os.path.join(winbuild_dir, "cache")
    architecture = "x86"
    build_dir = os.path.join(winbuild_dir, "build")
    force_tk = False
    for arg in sys.argv[1:]:
        if arg == "-v":
            verbose = True
        elif arg.startswith("--depends="):
            depends_dir = os.path.abspath(arg[10:])
        elif arg.startswith("--architecture="):
            architecture = arg[15:]
        elif arg.startswith("--dir="):
            build_dir = os.path.abspath(arg[6:])
        elif arg == "--cpython-openssl":
            disabled.remove("openssl-cpython")
            disabled.append("openssl")
        elif arg == "--with-tk":
            force_tk = True
        elif arg == "--no-boehm":
            disabled.append("boehm")
        else:
            raise ValueError("Unknown parameter: " + arg)

    # dependency cache directory
    os.makedirs(depends_dir, exist_ok=True)
    print("Caching dependencies in:", depends_dir)

    arch_prefs = architectures[architecture]
    print("Target Architecture:", architecture)

    msvs = find_msvs2015()
    if msvs is None:
        msvs = find_msvs()
        if not force_tk:
            # see warning below
            disabled.extend(["tcl", "tk"])
    if msvs is None:
        raise RuntimeError(
            "Visual Studio not found. Please install Visual Studio 2015 or newer."
        )
    print("Found Visual Studio at:", msvs["vs_dir"])

    print("Using output directory:", build_dir)

    # build directory for *.h files
    inc_dir = os.path.join(build_dir, "include")
    # build directory for *.lib files
    lib_dir = os.path.join(build_dir, "lib")
    # build directory for *.bin files
    bin_dir = os.path.join(build_dir, "bin")
    # build directory for auxiliary include files (win32.mak)
    aux_dir = os.path.join(build_dir, "auxiliary")

    tcltk_dir = os.path.join(build_dir, "tcltk")

    def rmtree_onerror(fn, path, excinfo):
        if excinfo[0] is PermissionError and excinfo[1].winerror == 5:
            os.chmod(path, stat.S_IWRITE)
            fn(path)
        else:
            raise

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, onerror=rmtree_onerror)
    for path in [build_dir, inc_dir, lib_dir, bin_dir, aux_dir, tcltk_dir]:
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

    if "tk" in disabled:
        print()
        print("!!! Building Tcl/Tk is disabled for Visual Studio 2017 or later, "
              "because Tk 8.5.2 requires Win SDK <= 10.0.15063.0, which is not available by default. "
              "See https://core.tcl-lang.org/tk/tktview?name=3d34589aa0 for more information.")
        print("!!! You can force Tcl/Tk compilation by running '%s --with-tk'. "
              "You may have to specify the target SDK version in the function 'find_msvs()' "
              "by replacing 'call \"{}\" {{vcvars_arch}}' with 'call \"{}\" {{vcvars_arch}} <sdk_version>'."
              % os.path.basename(__file__))

    if "openssl" not in disabled:
        if shutil.which("perl") is None:
            print()
            print("!!! perl.exe not found in PATH, compiling OpenSSL might fail.")
