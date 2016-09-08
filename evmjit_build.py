import os
import subprocess
import tarfile
from os import path
from cffi import FFI
from io import BytesIO

try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

CDEF = """
extern "Python" union evm_variant evm_query(struct evm_env* env,
                                            enum evm_query_key key,
                                            union evm_variant arg);
extern "Python" void evm_update(struct evm_env* env,
                                enum evm_update_key key,
                                union evm_variant arg1,
                                union evm_variant arg2);
extern "Python" int64_t evm_call(struct evm_env* env,
                                 enum evm_call_kind kind,
                                 int64_t gas,
                                 struct evm_uint160be address,
                                 struct evm_uint256be value,
                                 uint8_t const* input,
                                 size_t input_size,
                                 uint8_t* output,
                                 size_t output_size);

struct evm_interface evmjit_get_interface(void);
"""

EVMJIT_URL = 'https://github.com/ethereum/evmjit/archive/develop.tar.gz'
BUILD_DIR = path.join(path.abspath(path.dirname(__file__)), 'build')
EVMJIT_SRC_DIR = path.join(BUILD_DIR, 'evmjit', 'src')
EVMJIT_BUILD_DIR = path.join(BUILD_DIR, 'evmjit', 'build')
EVMJIT_INSTALL_DIR = path.join(BUILD_DIR, 'evmjit', 'install')


def download_tarball(url, outdir):
    if (path.exists(outdir)):
        return
    basedir = path.dirname(outdir)
    if (not path.exists(basedir)):
        os.makedirs(basedir)
    try:
        r = urlopen(url)
        if r.getcode() == 200:
            content = BytesIO(r.read())
            content.seek(0)
            with tarfile.open(fileobj=content) as tf:
                dirname = tf.getnames()[0].partition('/')[0]
                tf.extractall()
            os.rename(dirname, outdir)
        else:
            raise SystemExit(
                "Unable to download evmjit library: HTTP-Status: %d",
                r.getcode()
            )
    except URLError as ex:
        raise SystemExit("Unable to download evmjit library: %s",
                         ex.message)

if 'EVMJIT_INSTALL_PREFIX' in os.environ:
    # Using prebuild version of EVMJIT. Good for development and testing.
    prefix = os.environ['EVMJIT_INSTALL_PREFIX']
else:
    # Download and build EVMJIT.
    download_tarball(EVMJIT_URL, EVMJIT_SRC_DIR)
    if (not path.exists(EVMJIT_BUILD_DIR)):
        os.makedirs(EVMJIT_BUILD_DIR)

    configure_cmd = [
        'cmake',
        '-DCMAKE_INSTALL_PREFIX={}'.format(EVMJIT_INSTALL_DIR),
        '-DCMAKE_BUILD_TYPE=Release',
        EVMJIT_SRC_DIR
    ]

    build_cmd = [
        'cmake',
        '--build', EVMJIT_BUILD_DIR,
        '--target', 'evmjit-standalone'
    ]
    if os.name == 'posix':
        build_cmd += ['--', '-j16']

    install_cmd = [
        'cmake',
        '--build', EVMJIT_BUILD_DIR,
        '--target', 'install'
    ]

    subprocess.check_call(' '.join(configure_cmd), shell=True,
                          cwd=EVMJIT_BUILD_DIR)
    subprocess.check_call(' '.join(build_cmd), shell=True)
    subprocess.check_call(' '.join(install_cmd), shell=True)
    prefix = EVMJIT_INSTALL_DIR


# Basic configuration.
include_dir = path.join(prefix, 'include')
evm_header_file = path.join(include_dir, 'evm.h')
library_dir = path.join(prefix, 'lib')
libraries = ['evmjit-standalone', 'stdc++']

# Preprocess evm.h header.
# We want to extract only essential part stripping out preprocessor directives.
evm_header = open(evm_header_file).read()
evm_cdef_begin = evm_header.index('// BEGIN Python CFFI declarations')
evm_cdef_end = evm_header.index('// END Python CFFI declarations')
evm_cdef = evm_header[evm_cdef_begin:evm_cdef_end]

ffibuilder = FFI()
ffibuilder.cdef(evm_cdef)
ffibuilder.cdef(CDEF)
ffibuilder.set_source('_evmjit', '#include <evmjit.h>',
                      libraries=libraries, library_dirs=[library_dir],
                      include_dirs=[include_dir])

if __name__ == "__main__":
    ffibuilder.compile()
