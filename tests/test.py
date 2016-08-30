import hashlib
from evmjit import EVMJIT, Env, evm_mode, to_uint256


class TestEnv(Env):
    def query(self, key, arg):
        print("query(key: {}, arg: {})".format(key, arg))
        if key == 0:
            return 234588

    def update(self, key, arg1, arg2):
        print("update(key: {}, arg1: {}, arg2: {})".format(key, arg1, arg2))

    def call(self, kind, gas, address, value, input, input_size, output,
             output_size):
        return False


def test_to_uint256():
    assert to_uint256(0)[0] == [0, 0, 0, 0]
    assert to_uint256(1)[0] == [1, 0, 0, 0]
    assert to_uint256(1 << 63)[0] == [1 << 63, 0, 0, 0]
    assert to_uint256(1 << 64)[0] == [0, 1, 0, 0]
    assert to_uint256(1 << 255)[0] == [0, 0, 0, 1 << 63]


def test_evm():
    jit = EVMJIT()

    code = b'6001600260035455'.decode('hex')

    h = hashlib.new('sha256')
    h.update(code)
    code_hash = h.digest()

    input = "Hello World!"
    value = 4321543654643565
    gas = 200000

    success = jit.set_option("hello", "world")
    assert not success

    ready = jit.is_code_ready(evm_mode.EVM_HOMESTEAD, code_hash)
    assert not ready

    jit.prepare_code(evm_mode.EVM_HOMESTEAD, code_hash, code)

    ready = jit.is_code_ready(evm_mode.EVM_HOMESTEAD, code_hash)
    assert ready

    env = TestEnv()
    result = jit.execute(env, evm_mode.EVM_HOMESTEAD, code_hash, code, gas,
                         input, value)

    assert result.code == 0  # Success.
    assert result.gas_left == 194941
    assert result.output == b''


if __name__ == "__main__":
    test_to_uint256()
    test_evm()
