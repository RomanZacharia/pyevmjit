#!/bin/bash

set -e
set -x

# Install a system package required by our library
yum install -y pkg-config libffi libffi-devel

# The whole auto* stack in CentOS is too old - see https://github.com/pypa/manylinux/issues/71
wget -q https://cmake.org/files/v3.5/cmake-3.5.2-Linux-x86_64.tar.gz && tar zxf cmake-*.tar.gz && cd cmake* && ./configure > /dev/null && make install > /dev/null && cd ..
wget -q https://ftp.gnu.org/gnu/libtool/libtool-2.4.5.tar.gz && tar zxf libtool-*.tar.gz && cd libtool* && ./configure > /dev/null && make install > /dev/null && cd ..

# Compile wheels
for PYBIN in /opt/python/*/bin; do
	if [[ ${PYBIN} != *"cp26"* ]]; then
	${PYBIN}/pip wheel /io/ -w wheelhouse/
    fi
done

# Adjust wheel tags
mkdir out
for whl in wheelhouse/evmjit*.whl; do
    auditwheel repair $whl -w out
done

cp out/*.whl /io/dist
