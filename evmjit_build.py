import os
from os import path
from cffi import FFI

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


if 'EVMJIT_INSTALL_PREFIX' in os.environ:
    # Using prebuild version of EVMJIT. Good for development and testing.
    prefix = os.environ['EVMJIT_INSTALL_PREFIX']

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
