from _evmjit import ffi, lib


def from_uint256be(uint256be):
    """ Converts EVM-C uint256be to integer."""
    if hasattr(int, 'from_bytes'):  # Python 3
        return int.from_bytes(uint256be.bytes, byteorder='big')
    return int(bytes(uint256be.bytes).encode('hex'), 16)


def to_uint256be(x):
    """ Converts integer to EVM-C uint256be."""
    assert x < 2**256

    if hasattr(int, 'to_bytes'):  # Python 3
        uint256be = x.to_bytes(256, byteorder='big')
    else:
        uint256be = '{:064x}'.format(x).decode('hex')
    # Must be returned inside list or tuple to be converted to evm_uint256be
    # struct by CFFI.
    return (uint256be,)


@ffi.def_extern()
def evm_query(env, key, arg):
    if key == EVMJIT.SLOAD:
        arg = from_uint256be(arg.uint256be)
    else:
        arg = None

    env = ffi.from_handle(ffi.cast('void*', env))
    res = env.query(key, arg)

    # Convert answer back to EVM-C.
    if key in (EVMJIT.GAS_PRICE,
               EVMJIT.DIFFICULTY,
               EVMJIT.BALANCE,
               EVMJIT.BLOCKHASH,
               EVMJIT.SLOAD):
        return {'uint256be': to_uint256be(res)}

    if key in (EVMJIT.ADDRESS,
               EVMJIT.CALLER,
               EVMJIT.ORIGIN,
               EVMJIT.COINBASE):
        assert len(res) == 20
        return {'address': res}

    if key in (EVMJIT.GAS_LIMIT,
               EVMJIT.NUMBER,
               EVMJIT.TIMESTAMP):
        return {'int64': res}

    if key == EVMJIT.CODE_BY_ADDRESS:
        return {'data': res, 'data_size': len(res)}


@ffi.def_extern()
def evm_update(env, key, arg1, arg2):
    env = ffi.from_handle(ffi.cast('void*', env))

    # Preprocess arguments.
    if key == EVMJIT.SSTORE:
        arg1 = from_uint256be(arg1.uint256be)
        arg2 = from_uint256be(arg2.uint256be)

    env.update(key, arg1, arg2)


@ffi.def_extern()
def evm_call(env, kind, gas, address, value, input, input_size, output,
             output_size):
    env = ffi.from_handle(ffi.cast('void*', env))
    return env.call(kind)  # FIXME


class Env(object):
    def query(self, key, arg):
        pass

    def update(self, key, arg1, arg2):
        pass

    def call(self, kind, gas, address, value, input):
        pass


class Result(object):
    def __init__(self, result, releaser):
        self.__res = result
        self.__releaser = releaser

    def __del__(self):
        # Pass pointer to the evm_result to evm_release_result function.
        self.__releaser((self.__res,))

    @property
    def code(self):
        return self.__res.code

    @property
    def gas_left(self):
        return self.__res.gas_left

    @property
    def output(self):
        output_size = self.__res.output_size
        if output_size == 0:
            return b''
        return ffi.unpack(self.__res.output_data, self.__res.output_size)


class EVMJIT:
    # Execution compatibility mode
    FRONTIER = lib.EVM_FRONTIER
    HOMESTEAD = lib.EVM_HOMESTEAD

    # Query keys
    SLOAD = lib.EVM_SLOAD
    ADDRESS = lib.EVM_ADDRESS
    CALLER = lib.EVM_CALLER
    ORIGIN = lib.EVM_ORIGIN
    GAS_PRICE = lib.EVM_GAS_PRICE
    COINBASE = lib.EVM_COINBASE
    DIFFICULTY = lib.EVM_DIFFICULTY
    GAS_LIMIT = lib.EVM_GAS_LIMIT
    NUMBER = lib.EVM_NUMBER
    TIMESTAMP = lib.EVM_TIMESTAMP
    CODE_BY_ADDRESS = lib.EVM_CODE_BY_ADDRESS
    BALANCE = lib.EVM_BALANCE
    BLOCKHASH = lib.EVM_BLOCKHASH

    # Update keys
    SSTORE = lib.EVM_SSTORE
    LOG = lib.EVM_LOG
    SELFDESTRUCT = lib.EVM_SELFDESTRUCT
    # TODO: The above constants comes from EVM-C and are not EVMJIT specific.
    #       Should we move them to EVM namespace?

    def __init__(self):
        # Get virtual interface from EVMJIT module.
        self.interface = lib.evmjit_get_interface()
        assert self.interface.abi_version == lib.EVM_ABI_VERSION,\
            'ABI version mismatch'
        # Create EVMJIT instance.
        self.instance = self.interface.create(lib.evm_query, lib.evm_update,
                                              lib.evm_call)

    def __del__(self):
        # FIXME: Explicit destroy() needed?
        self.interface.destroy(self.instance)

    def execute(self, env, mode, code_hash, code, gas, input, value):
        assert len(code_hash) == 32
        ret = self.interface.execute(self.instance,
                                     ffi.new_handle(env),
                                     mode,
                                     [code_hash],
                                     code,
                                     len(code),
                                     gas,
                                     input,
                                     len(input),
                                     to_uint256be(value))
        return Result(ret, self.interface.release_result)

    def set_option(self, name, value):
        return self.interface.set_option(self.instance, name, value)

    def is_code_ready(self, mode, code_hash):
        st = self.interface.get_code_status(self.instance, mode, [code_hash])
        return st == lib.EVM_READY

    def prepare_code(self, mode, code_hash, code):
        self.interface.prepare_code(self.instance, mode, [code_hash],
                                    code, len(code))
