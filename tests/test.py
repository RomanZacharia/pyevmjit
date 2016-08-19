import hashlib
from evmjit import EVMJIT, evm_mode


def query(env, key, arg):
    print("query(env: {}, key: {}, arg: {})".format(env, key, arg))
    if key == 0:
        return 234588


def update(env, key, arg1, arg2):
    print("update(env: {}, key: {}, arg1: {}, arg2: {})"
          .format(env, key, arg1, arg2))


def call(env, kind, gas, address, value, input, input_size, output, output_size):
    return False


def test_evm():

    evm = EVMJIT()
    evm.evm_create(query, update, call)

    code = b'6001600260035455'.decode('hex')

    h = hashlib.new('sha256')
    h.update(code)
    code_hash = h.digest()

    input = "Hello World!"

    value_ffi = [1,0,0,0]

    gas = 200000

    # import pdb; pdb.set_trace()
    env = {'name': "Env"}  # You can pass any Python object as env argument.
    result = evm.evm_execute(env, evm_mode.EVM_HOMESTEAD, code_hash, code, gas,
                             input, value_ffi)

    evm.evm_destroy_result(result)
    evm.evm_destroy()


if __name__ == "__main__":
    test_evm()
