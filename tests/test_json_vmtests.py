import json
import os
from os import path
from pprint import pprint

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
        self.out_storage = {}

    def query(self, key, arg):
        print("query(key: {}, arg: {})".format(key, arg))
        if key == EVMJIT.SLOAD:
            sload_key = '{:x}'.format(arg)
            value = self.desc['pre'][self.desc['exec']['address']]['storage'].get(sload_key, '0')
            print("Value: {}".format(value))
            return int(value, 16)
        if key == EVMJIT.ADDRESS:
            return self.desc['exec']['address'].decode('hex')

    def update(self, key, arg1, arg2):
        print("update(key: {}, arg1: {}, arg2: {})".format(key, arg1, arg2))
        self.out_storage[arg1] = arg2

    def call(self, kind, gas, address, value, input):
        if kind == EVMJIT.CREATE:
            print("create(gas: {}, value: {}, code: {})".format(
                gas, value, input))
            return EVMJIT.SUCCESS, b'', gas

        print("call(kind: {}, gas: {}, value: {})".format(kind, gas, value))
        return EVMJIT.SUCCESS, b'', gas


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
        # print(code.encode('hex'))
        # code = '7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff600052'.decode('hex')
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
