from _libevmjit import ffi, lib


def enum(**enums):
    return type('Enum', (), enums)

evm_mode = enum(EVM_FRONTIER=0, EVM_HOMESTEAD=1)

evm_query_key = enum(
    EVM_SLOAD = 0,            #< Storage value of a given key for SLOAD.
    EVM_ADDRESS = 1,          #< Address of the contract for ADDRESS.
    EVM_CALLER = 2,           #< Message sender address for CALLER.
    EVM_ORIGIN = 3,           #< Transaction origin address for ORIGIN.
    EVM_GAS_PRICE = 4,        #< Transaction gas price for GASPRICE.
    EVM_COINBASE = 5,         #< Current block miner address for COINBASE.
    EVM_DIFFICULTY = 6,       #< Current block difficulty for DIFFICULTY.
    EVM_GAS_LIMIT = 7,        #< Current block gas limit for GASLIMIT.
    EVM_NUMBER = 8,           #< Current block number for NUMBER.
    EVM_TIMESTAMP = 9,        #< Current block timestamp for TIMESTAMP.
    EVM_CODE_BY_ADDRESS = 10, #< Code by an address for EXTCODE/SIZE.
    EVM_BALANCE = 11,         #< Balance of a given address for BALANCE.
    EVM_BLOCKHASH = 12        #< Block hash of by block number for BLOCKHASH.
)


def from_uint256(a):
    # TODO: We could've used int.from_bytes here, but I don't know how to
    #       access bytes of uint256
    words = a.words
    v = 0
    v = (v << 64) | words[3]
    v = (v << 64) | words[2]
    v = (v << 64) | words[1]
    v = (v << 64) | words[0]
    return v


def to_uint256(x):
    """ Converts integer to EVM-C uint256."""
    assert x < 2**256
    words = []
    for i in range(4):
        word = x & 0xffffffffffffffff
        words.append(word)
        x = x >> 64
    return (words, )


@ffi.def_extern()
def evm_query(env, key, arg):
    if key == evm_query_key.EVM_SLOAD:
        arg = from_uint256(arg.uint256)
    else:
        arg = None

    env = ffi.from_handle(ffi.cast('void*', env))
    res = env.query(key, arg)

    # Convert answer back to EVM-C.
    if key in (evm_query_key.EVM_GAS_PRICE,
               evm_query_key.EVM_DIFFICULTY,
               evm_query_key.EVM_BALANCE,
               evm_query_key.EVM_BLOCKHASH,
               evm_query_key.EVM_SLOAD):
        return {'uint256': to_uint256(res)}

    if key in (evm_query_key.EVM_ADDRESS,
               evm_query_key.EVM_CALLER,
               evm_query_key.EVM_ORIGIN,
               evm_query_key.EVM_COINBASE):
        assert len(res) == 20
        return {'address': res}

    if key in (evm_query_key.EVM_GAS_LIMIT,
               evm_query_key.EVM_NUMBER,
               evm_query_key.EVM_TIMESTAMP):
        return {'int64': res}

    if key == evm_query_key.EVM_CODE_BY_ADDRESS:
        return {'data': res, 'data_size': len(res)}


@ffi.def_extern()
def evm_update(env, key, arg1, arg2):
    env = ffi.from_handle(ffi.cast('void*', env))

    # Preprocess arguments.
    if key == lib.EVM_SSTORE:
        arg1 = from_uint256(arg1.uint256)
        arg2 = from_uint256(arg2.uint256)

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
                                     to_uint256(value))
        return Result(ret, self.interface.release_result)

    def set_option(self, name, value):
        return self.interface.set_option(self.instance, name, value)

    def is_code_ready(self, mode, code_hash):
        st = self.interface.get_code_status(self.instance, mode, [code_hash])
        return st == lib.EVM_READY

    def prepare_code(self, mode, code_hash, code):
        self.interface.prepare_code(self.instance, mode, [code_hash],
                                    code, len(code))
