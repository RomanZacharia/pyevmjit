import os
import sys
from collections import namedtuple

from cffi import FFI

sys.path.append(os.path.abspath(os.path.dirname(__file__)))


def absolute(*paths):
    op = os.path
    return op.realpath(op.abspath(op.join(op.dirname(__file__), *paths)))

Source = namedtuple('Source', ('h', 'include'))


def _mk_ffi(sources, name="_libevmjit", bundled=True, **kwargs):
    ffi = FFI()
    code = []
    if 'INCLUDE_DIR' in os.environ:
        kwargs['include_dirs'] = [absolute(os.environ['INCLUDE_DIR'])]
    if 'LIB_DIR' in os.environ:
        kwargs['library_dirs'] = [absolute(os.environ['LIB_DIR'])]
    for source in sources:
        with open(source.h, 'rt') as h:
            ffi.cdef(h.read())
        code.append(source.include)
    if bundled:
        code.append("#define PY_USE_BUNDLED")
    ffi.set_source(name, "\n".join(code), **kwargs)
    return ffi


from pprint import pprint
pprint('The dir where the linker is executed:')
pprint(os.getcwd())
pprint(os.listdir('.'))


_base = [Source(absolute("evm.h"), "#include \"" + absolute("evm.h") + "\"",)]
ffi = _mk_ffi(_base, libraries=['libevmjit-static'])
ffi.cdef("""
    extern "Python" union evm_variant evm_query(struct evm_env* env,
                                          enum evm_query_key key,
                                          union evm_variant arg);
    extern "Python" void evm_update(struct evm_env* env,
                              enum evm_update_key key,
                              union evm_variant arg1,
                              union evm_variant arg2);
    extern "Python" int64_t evm_call(
    struct evm_env* env,
    enum evm_call_kind kind,
    int64_t gas,
    struct evm_hash160 address,
    struct evm_uint256 value,
    uint8_t const* input,
    size_t input_size,
    uint8_t* output,
    size_t output_size);
""")
ffi.compile()
