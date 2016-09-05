import json
import os
from binascii import hexlify
from os import path

import hashlib
import sha3  # Patches hashlib. # noqa

from evmjit import EVMJIT


def code_hash(code):
    h = hashlib.sha3_256()
    h.update(code)
    return h.digest()


class Env(object):
    def __init__(self, desc):
        self.desc = desc
        self.pre = desc['pre']
        self.addr = desc['exec']['address'].decode('hex')
        self.caller = desc['exec']['caller'].decode('hex')
        self.tx_origin = desc['exec']['origin'].decode('hex')
        self.block_number = int(desc['env']['currentNumber'], 16)
        self.block_timestamp = int(desc['env']['currentTimestamp'], 16)
        self.block_gas_limit = int(desc['env']['currentGasLimit'], 16)
        self.block_difficulty = int(desc['env']['currentDifficulty'], 16)
        self.block_coinbase = desc['env']['currentCoinbase'].decode('hex')
        self.out_storage = {}

    def get_balance(self, addr):
        addr = addr.encode('hex')
        if addr not in self.pre:
            return 0
        return int(self.pre[addr]['balance'], 16)

    def query(self, key, arg):
        print("query(key: {}, arg: {})".format(key, arg))
        if key == EVMJIT.SLOAD:
            sload_key = '{:x}'.format(arg)
            value = self.pre[hexlify(self.addr)]['storage'].get(sload_key, '0')
            return int(value, 16)
        if key == EVMJIT.ADDRESS:
            return self.addr
        if key == EVMJIT.CALLER:
            return self.caller
        if key == EVMJIT.ORIGIN:
            return self.tx_origin
        if key == EVMJIT.COINBASE:
            return self.block_coinbase
        if key == EVMJIT.NUMBER:
            return self.block_number
        if key == EVMJIT.TIMESTAMP:
            return self.block_timestamp
        if key == EVMJIT.GAS_LIMIT:
            return self.block_gas_limit
        if key == EVMJIT.DIFFICULTY:
            return self.block_difficulty

    def update(self, key, arg1, arg2):
        print("update(key: {}, arg1: {}, arg2: {})".format(key, arg1, arg2))
        self.out_storage[arg1] = arg2

    def call(self, kind, gas, address, value, input):
        if kind != EVMJIT.DELEGATECALL:
            if self.get_balance(self.addr) < value:
                return EVMJIT.FAILURE, b'', 0
        if kind == EVMJIT.CREATE:
            print("create(gas: {}, value: {}, code: {})".format(
                gas, value, input))
            return EVMJIT.SUCCESS, b'', 0

        if kind == EVMJIT.DELEGATECALL:
            assert value == 0

        cost = 0
        if value:
            cost += 9000 - 2300

        if hexlify(address) not in self.desc['pre']:
            cost += 25000

        print("call(kind: {}, gas: {}, value: {})".format(kind, gas, value))
        return EVMJIT.SUCCESS, b'', cost


def test_vmtests():
    jit = EVMJIT()

    tests_dir = os.environ['ETHEREUM_TEST_PATH']
    vmtests_dir = path.join(tests_dir, 'VMTests')
    json_test_files = []
    for subdir, _, files in os.walk(vmtests_dir):
        json_test_files += [path.join(subdir, f)
                            for f in files if f.endswith('.json')]
    # print(json_test_files)
    test_suite = json.load(open(json_test_files[0]))
    for name, desc in test_suite.iteritems():
        print(name)
        # pprint(desc)
        ex = desc['exec']
        code = ex['code'][2:].decode('hex')
        data = ex['data'][2:].decode('hex')
        gas = int(ex['gas'], 16)
        value = int(ex['value'], 16)
        res = jit.execute(Env(desc), EVMJIT.FRONTIER, code_hash(code), code,
                          gas, data, value)
        if 'gas' in desc:
            assert res.code == EVMJIT.SUCCESS
            expected_gas = int(desc['gas'], 16)
            assert res.gas_left == expected_gas
        else:
            assert res.code != EVMJIT.SUCCESS


if __name__ == '__main__':
    test_vmtests()
