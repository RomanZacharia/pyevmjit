from _libevmjit import ffi, lib
evm_query_cb = None
evm_update_cb = None
evm_call_cb = None

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

@ffi.def_extern()
def evm_query(env, key, arg):
    if key == evm_query_key.EVM_SLOAD:
        arg = from_uint256(arg.uint256)
    else:
        arg = None

    global evm_query_cb
    if evm_query_cb:
        env = ffi.from_handle(ffi.cast('void*', env))
        variant = evm_query_cb(env, key, arg)
        if key == evm_query_key.EVM_GAS_PRICE or\
                key == evm_query_key.EVM_DIFFICULTY or\
                key == evm_query_key.EVM_BALANCE or\
                key == evm_query_key.EVM_BLOCKHASH or\
                key == evm_query_key.EVM_SLOAD:
            return {'uint256': ([0,1,2,3],)}

        if key == evm_query_key.EVM_ADDRESS or\
                key == evm_query_key.EVM_CALLER or\
                key == evm_query_key.EVM_ORIGIN or\
                key == evm_query_key.EVM_COINBASE:
            ret[0].address.bytes = variant

        if key == evm_query_key.EVM_GAS_LIMIT or\
                key == evm_query_key.EVM_NUMBER or\
                key == evm_query_key.EVM_TIMESTAMP:
            ret[0].int64 = variant

        if key == evm_query_key.EVM_CODE_BY_ADDRESS:
            ret[0].data = ffi.new("uint8_t[]", variant)
            ret[0].data_size = len(variant)

    else:
        ret[0].uint256 = [[0, 0, 0, 0]]


@ffi.def_extern()
def evm_update(env, key, arg1, arg2):
    global evm_update_cb
    if evm_update_cb:
        evm_update_cb(env, key, arg1, arg2)


@ffi.def_extern()
def evm_call(env, kind, gas, address, value, input, input_size, output, output_size):
    global evm_call_cb
    if evm_call_cb:
        return evm_call_cb(env, kind, gas, address, value, input, input_size, output, output_size)
    else:
        return 0


class EVMJIT:
    evm = None

    def __init__(self):
        pass

    def evm_create(self, query_cb=None, update_cb=None, call_cb=None):
        assert self.evm is None, 'evm is already initialized'
        # import pdb; pdb.set_trace()
        global evm_query_cb
        global evm_update_cb
        global evm_call_cb
        evm_query_cb = query_cb
        evm_update_cb = update_cb
        evm_call_cb = call_cb
        self.evm = lib.evm_create(lib.evm_query, lib.evm_update, lib.evm_call)

    def evm_execute(self, env, mode, code_hash, code, gas, input, value):
        assert self.evm, 'Please initialize the evm by calling evm_create'
        if env == 0:
            env = ffi.NULL
        ret = lib.evm_execute(self.evm,
                              ffi.new_handle(env),
                              mode,
                              [code_hash],
                              code,
                              len(code),
                              gas,
                              input,
                              len(input),
                              [value])
        return ret

    def evm_destroy_result(self, result):
        lib.evm_destroy_result(result)

    def evm_destroy(self):
        if self.evm:
            lib.evm_destroy(self.evm)
            self.evm = None

    def evm_get_info(key):
        lib.evm_get_info(key)

    def evm_set_option(self, name, value):
        assert self.evm, 'Please initialize the evm by calling evm_create'
        return lib.evm_set_option(self.evm, name, value)

    def evmjit_is_code_ready(self, mode, code_hash):
        assert self.evm, 'Please initialize the evm by calling evm_create'
        return lib.evmjit_is_code_ready(self.evm, mode, code_hash)

    def evmjit_compile(self, mode, code, code_hash):
        assert self.evm, 'Please initialize the evm by calling evm_create'
        lib.evmjit_compile(self.evm, mode, code, len(code), [code_hash])

    def __del__(self):
        if self.evm:
            lib.evm_destroy(self.evm)
