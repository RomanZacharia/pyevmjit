from evmjit import EVMJIT

def evm_query(env, key, arg):
    result = ffi.new("union evm_variant*")
    if key == lib.EVM_GAS_LIMIT:
        result.int64 = 314
    elif key == lib.EVM_BALANCE:
        result.uint256 = 777
    else:
        result.int64 = 0
    return result


def evm_update(env, key, arg1, arg2):


def evm_call(env, kind, gas, address, value, input, input_size, output, output_size):
    result = 0
    return result

def test_evm():

    evm = EVMJIT()
    evm.evm_create()

    code = "exec()"
    
    code_hash = [1, 2, 3, 0]

    input = "Hello World!"

    value_ffi = [1,0,0,0]

    gas = 200000;

    import pdb; pdb.set_trace()
    result = evm.evm_execute(0, evm_mode.EVM_HOMESTEAD, code_hash, code, gas, input, value_ffi)

    evm.evm_destroy_result(result)
    evm.evm_destroy()


if __name__ == "__main__":
    test_evm()