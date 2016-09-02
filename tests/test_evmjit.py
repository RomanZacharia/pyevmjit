import hashlib
from evmjit import EVMJIT, Env


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

    ready = jit.is_code_ready(EVMJIT.HOMESTEAD, code_hash)
    assert not ready

    jit.prepare_code(EVMJIT.HOMESTEAD, code_hash, code)

    ready = jit.is_code_ready(EVMJIT.HOMESTEAD, code_hash)
    assert ready

    env = TestEnv()
    result = jit.execute(env, EVMJIT.HOMESTEAD, code_hash, code, gas,
                         input, value)

    assert result.code == 0  # Success.
    assert result.gas_left == 194941
    assert result.output == b''


if __name__ == "__main__":
    test_evm()
