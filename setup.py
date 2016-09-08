# coding=utf-8

import errno
import os
import os.path
import shutil
import subprocess
import tarfile
from distutils import log
from distutils.command.build_clib import build_clib as _build_clib
from distutils.command.build_ext import build_ext as _build_ext
from distutils.errors import DistutilsError
from io import BytesIO
import sys

from setuptools import Distribution as _Distribution, setup, find_packages, __version__ as setuptools_version
from setuptools.command.develop import develop as _develop
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist
try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None
    pass

try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError


sys.path.append(os.path.abspath(os.path.dirname(__file__)))


# Version of libevmjit to download if none exists in the `libevmjit`
# directory
LIB_TARBALL_URL = "https://github.com/ethereum/evmjit/archive/v0.10.0-rc.1.tar.gz"


# We require setuptools >= 3.3
if [int(i) for i in setuptools_version.split('.')] < [3, 3]:
    raise SystemExit(
        "Your setuptools version ({}) is too old to correctly install this "
        "package. Please upgrade to a newer version (>= 3.3).".format(setuptools_version)
    )

# Ensure pkg-config is available
try:
    subprocess.check_call(['pkg-config', '--version'])
except OSError:
    raise SystemExit(
        "'pkg-config' is required to install this package. "
        "Please see the README for details."
    )


def download_library(command):
    if command.dry_run:
        return
    libdir = absolute("libevmjit")
    if os.path.exists(os.path.join(libdir, "appveyor.yml")):
        # Library already downloaded
        return
    if not os.path.exists(libdir):
        command.announce("downloading libevmjit source code", level=log.INFO)
        try:
            r = urlopen(LIB_TARBALL_URL)
            if r.getcode() == 200:
                content = BytesIO(r.read())
                content.seek(0)
                with tarfile.open(fileobj=content) as tf:
                    dirname = tf.getnames()[0].partition('/')[0]
                    tf.extractall()
                shutil.move(dirname, libdir)
            else:
                raise SystemExit(
                    "Unable to download evmjit library: HTTP-Status: %d",
                    r.getcode()
                )
        except URLError as ex:
            raise SystemExit("Unable to download evmjit library: %s",
                             ex.message)


class egg_info(_egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        download_library(self)

        _egg_info.run(self)


class sdist(_sdist):
    def run(self):
        download_library(self)
        _sdist.run(self)


if _bdist_wheel:
    class bdist_wheel(_bdist_wheel):
        def run(self):
            download_library(self)
            _bdist_wheel.run(self)
else:
    bdist_wheel = None


class Distribution(_Distribution):
    def has_c_libraries(self):
        return not has_system_lib()


class build_clib(_build_clib):
    def initialize_options(self):
        _build_clib.initialize_options(self)
        self.build_flags = None

    def finalize_options(self):
        _build_clib.finalize_options(self)
        if self.build_flags is None:
            self.build_flags = {
                'include_dirs': [],
                'library_dirs': [],
                'define': [],
            }

    def get_source_files(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        download_library(self)

        return [
            absolute(os.path.join(root, filename))
            for root, _, filenames in os.walk(absolute("libevmjit"))
            for filename in filenames
        ]

    def build_libraries(self, libraries):
        raise Exception("build_libraries")

    def check_library_list(self, libraries):
        raise Exception("check_library_list")

    def get_library_names(self):
        return build_flags('libevmjit', 'l', os.path.abspath(self.build_temp))

    def run(self):
        if has_system_lib():
            log.info("Using system library")
            return

        build_temp = os.path.abspath(self.build_temp)

        try:
            os.makedirs(build_temp)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        subprocess.check_call(["cmake"], cwd=build_temp)
        subprocess.check_call(["make"], cwd=build_temp)
        subprocess.check_call(["make", "install"], cwd=build_temp)
        subprocess.check_call(["ldconfig"], cwd=build_temp)

        self.build_flags['include_dirs'].extend(build_flags('libevmjit', 'I', build_temp))
        self.build_flags['library_dirs'].extend(build_flags('libevmjit', 'L', build_temp))
        if not has_system_lib():
            self.build_flags['define'].append(('CFFI_ENABLE_RECOVERY', None))
        else:
            pass


class build_ext(_build_ext):
    def run(self):
        if self.distribution.has_c_libraries():
            build_clib = self.get_finalized_command("build_clib")
            self.include_dirs.append(
                os.path.join(build_clib.build_clib, "include"),
            )
            self.include_dirs.extend(build_clib.build_flags['include_dirs'])

            self.library_dirs.append(
                os.path.join(build_clib.build_clib, "lib"),
            )
            self.library_dirs.extend(build_clib.build_flags['library_dirs'])

            self.define = build_clib.build_flags['define']

        return _build_ext.run(self)


class develop(_develop):
    def run(self):
        if not has_system_lib():
            raise DistutilsError(
                "This library is not usable in 'develop' mode when using the "
                "bundled libevmjit. See README for details.")
        _develop.run(self)


setup(
    name="evmjit",
    version="0.10.0b1",

    description='FFI bindings to libevmjit',
    url='https://github.com/RomanZacharia/pyevmjit',
    author=u'Roman Zacharia, Paweł Bylica',
    author_email='roman.zacharia@gmail.com',
    license='MIT',  # FIXME: Can we change to APACHE 2.0?

    setup_requires=['cffi>=1.8.2'],
    install_requires=['cffi>=1.8.2'],

    packages=['evmjit'],
    cffi_modules=['evmjit_build.py:ffibuilder'],

    # cmdclass={
    #     'build_clib': build_clib,
    #     'build_ext': build_ext,
    #     'develop': develop,
    #     'egg_info': egg_info,
    #     'sdist': sdist,
    #     'bdist_wheel': bdist_wheel
    # },
    # distclass=Distribution,
    zip_safe=False,

    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries",
        "Topic :: Virtualization :: VM"
    ]
)
