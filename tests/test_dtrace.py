#!/usr/bin/env python
# Copyright (C) 2015 Dmitry Rodionov
# This file is part of my GSoC'15 project for Cuckoo Sandbox:
#	http://www.cuckoosandbox.org
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import os
import sys
import unittest
import subprocess
from sets import Set

from analyzer.darwin.lib.dtrace.dtruss import *
from analyzer.darwin.lib.dtrace.ipconnections import *

TESTS_DIR = os.path.dirname(os. path.abspath(__file__))

class TestDtrace(unittest.TestCase):

	def setUp(self):
		build_target(self._testMethodName)

	def tearDown(self):
		cleanup_target(self._testMethodName)

	def current_target(self):
		return TESTS_DIR + "/assets/" + self._testMethodName

	def test_dtruss_helloworld(self):
		# given
		expected_syscall = 'write_nocancel'
		expected_args = [1, 'Hello, world!\n', 0xE]
		expected_result = 14
		expected_errno =  0
		output = []
		# when
		for call in dtruss(self.current_target()):
			output.append(call)
		# then
		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1

	def test_dtruss_specific_syscall(self):
		# given
		expected_syscall = 'write_nocancel'
		expected_args = [1, 'Hello, dtruss!\n', 0xF]
		expected_result = 15
		expected_errno =  0
		output = []
		# when
		for call in dtruss(self.current_target(), syscall="write_nocancel", run_as_root=False):
			output.append(call)
		# then
		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1

	def test_dtruss_timeout(self):
		# given
		expected_syscall = 'write'
		expected_args = [1, 'Hello, world!\n', 0xE]
		expected_result = 14
		expected_errno =  0
		output = []
		# when
		for call in dtruss(self.current_target(), timeout=2, run_as_root = True):
			output.append(call)
		# then
		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1
		assert sum(x.name == "write" for x in output) == 1

	def test_dtruss_with_args(self):
		# given
		expected_syscall = 'write_nocancel'
		expected_args = [1, 'Hello, WoR1D!\n', 0xE]
		expected_result = 14
		expected_errno =  0
		args = ["WoR1D", "-k", "foobar"]
		output = []
		# when
		for call in dtruss(self.current_target(), args=args):
			output.append(call)
		# then
		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1

	def test_dtruss_root(self):
		# given
		expected_syscall = 'write_nocancel'
		expected_args = [1, 'Hello, r00t!\n', 0xD]
		expected_result = 0xD
		expected_errno =  0
		pids = Set()
		output = []
		# when
		for call in dtruss(self.current_target(), run_as_root = True):
			output.append(call)
			pids.add(call.pid)
		# then
		assert len(pids) == 1

		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1

	def test_dtruss_non_root(self):
		# given
		expected_syscall = 'write_nocancel'
		expected_args = [1, 'Hello, user!\n', 0xD]
		expected_result = 0xD
		expected_errno =  0
		pids = Set()
		output = []
		# when
		for call in dtruss(self.current_target()):
			output.append(call)
			pids.add(call.pid)
		# then
		assert len(pids) == 1

		matched = [x for x in output if x.name == expected_syscall and x.args == expected_args and x.result == expected_result and x.errno == expected_errno]

		assert len(matched) == 1


	def test_ipconnections_udp(self):
		# given
		expected = ('127.0.0.1', # host
		            53,          # port
		            'UDP')       # protocol
		output = []
		# when
		for connection in ipconnections(self.current_target()):
			output.append(connection)
		# then
		assert len(output) == 1
		matched = [x for x in output if
			(x.remote, x.remote_port, x.protocol) == expected]
		assert len(matched) == 1

	def test_ipconnections_tcp(self):
		# given
		expected = ('127.0.0.1', # host
		            80,          # port
		            'TCP')       # protocol
		output = []
		# when
		for connection in ipconnections(self.current_target()):
			output.append(connection)
		# then
		assert len(output) == 1
		matched = [x for x in output if
			(x.remote, x.remote_port, x.protocol) == expected]
		assert len(matched) == 1

	def test_ipconnections_tcp_with_timeout(self):
		# given
		expected = ('127.0.0.1', # host
		            80,          # port
		            'TCP')       # protocol
		output = []
		# when
		for connection in ipconnections(self.current_target(), timeout=1):
			output.append(connection)
		# then
		assert len(output) == 1
		matched = [x for x in output if
			(x.remote, x.remote_port, x.protocol) == expected]
		assert len(matched) == 1

	def test_ipconnections_empty(self):
		# given
		output = []
		# when
		for connection in ipconnections(self.current_target()):
			output.append(connection)
		# then
		assert len(output) == 0

	def test_ipconnections_target_with_args(self):
		# given
		expected = ('127.0.0.1', # host
		            80,          # port
		            'TCP')       # protocol
		args = ["127.0.0.1"]
		output = []
		# when
		for connection in ipconnections(self.current_target(), args=args):
			output.append(connection)
		# then
		assert len(output) == 1
		matched = [x for x in output if
			(x.remote, x.remote_port, x.protocol) == expected]
		assert len(matched) == 1

def build_target(target):
	# clang -arch x86_64 -o $target_name $target_name.c
	output = executable_name_for_target(target)
	source = sourcefile_name_for_target(target)
	subprocess.check_call(["clang", "-arch", "x86_64", "-O0", "-o", output, source])

def cleanup_target(target):
	os.remove(executable_name_for_target(target))

def sourcefile_name_for_target(target):
	return "%s/assets/%s.c" % (TESTS_DIR, target)

def executable_name_for_target(target):
	return "%s/assets/%s" % (TESTS_DIR, target)

if __name__ == '__main__':
	unittest.main()