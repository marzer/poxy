#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Low-level helper functions and useful bits.
"""

import sys
import re
import io
import logging
from typing import Tuple
from pathlib import Path
from misk import *

#=======================================================================================================================
# FUNCTIONS
#=======================================================================================================================



def regex_or(patterns, pattern_prefix='', pattern_suffix='', flags=0):
	patterns = [str(r) for r in patterns if r is not None and r]
	patterns.sort()
	pattern = ''
	if patterns:
		pattern = '(?:(?:' + ')|(?:'.join(patterns) + '))'
	patterns = re.compile(rf'{pattern_prefix}{pattern}{pattern_suffix}', flags=flags)
	return patterns



def log(logger, msg, level=logging.INFO):
	if logger is None or msg is None:
		return
	if isinstance(logger, bool):
		if logger:
			print(msg, file=sys.stderr if level >= logging.WARNING else sys.stdout)
	elif isinstance(logger, logging.Logger):
		logger.log(level, msg)
	elif isinstance(logger, io.IOBase):
		print(msg, file=logger)
	else:
		logger(msg)



def combine_dicts(x, y):
	z = x.copy()
	z.update(y)
	return z



RX_IS_URI = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*://.+$')



def is_uri(s):
	global RX_IS_URI
	return RX_IS_URI.fullmatch(str(s)) is not None



def find_package_dir() -> Path:
	if not hasattr(find_package_dir, "dir"):
		find_package_dir.dir = Path(__file__).resolve().parent
		assert_existing_directory(find_package_dir.dir)
	return find_package_dir.dir



def find_data_dir() -> Path:
	if not hasattr(find_data_dir, "dir"):
		find_data_dir.dir = Path(find_package_dir(), r'data')
		assert_existing_directory(find_data_dir.dir)
	return find_data_dir.dir



def find_generated_dir() -> Path:
	if not hasattr(find_generated_dir, "dir"):
		find_generated_dir.dir = Path(find_data_dir(), r'generated')
	return find_generated_dir.dir



def find_mcss_dir() -> Path:
	if not hasattr(find_mcss_dir, "dir"):
		find_mcss_dir.dir = Path(find_data_dir(), r'm.css')
		assert_existing_directory(find_mcss_dir.dir)
		assert_existing_file(Path(find_mcss_dir.dir, r'documentation/doxygen.py'))
	return find_mcss_dir.dir



def lib_version() -> Tuple[int, int, int]:
	if not hasattr(lib_version, "val"):
		with open(Path(find_data_dir(), 'version.txt'), encoding='utf-8') as file:
			lib_version.val = [int(v.strip()) for v in file.read().strip().split('.')]
			assert len(lib_version.val) == 3
			lib_version.val = tuple(lib_version.val)
	return lib_version.val



def filter_filenames(files, include, exclude):
	if include is not None:
		files = [f for f in files if include.search(f.name)]
	if exclude is not None:
		files = [f for f in files if not exclude.search(f.name)]
	return files



#=======================================================================================================================
# REGEX REPLACER
#=======================================================================================================================



class RegexReplacer(object):

	def __substitute(self, m):
		self.__result = True
		return self.__handler(m, self.__out_data)

	def __init__(self, regex, handler, value):
		self.__handler = handler
		self.__result = False
		self.__out_data = []
		self.__value = regex.sub(lambda m: self.__substitute(m), value)

	def __str__(self):
		return self.__value

	def __bool__(self):
		return self.__result

	def __len__(self):
		return len(self.__out_data)

	def __getitem__(self, index):
		return self.__out_data[index]



#=======================================================================================================================
# CppTree
#=======================================================================================================================



class CppTree(object):

	NAMESPACES = 1
	TYPES = 2
	ENUM_VALUES = 4

	class Node(object):

		def __init__(self, val, parent, type_=0):
			assert val.find(r'::') == -1
			assert type_ in (0, CppTree.NAMESPACES, CppTree.TYPES, CppTree.ENUM_VALUES)
			self.value = val
			self.parent = parent
			self.type = type_
			self.mask = type_
			self.children = {}

		def add(self, val, type_=0):
			assert val.find(r'::') == -1
			assert type_ in (0, CppTree.NAMESPACES, CppTree.TYPES, CppTree.ENUM_VALUES)
			child = None
			if val not in self.children:
				child = CppTree.Node(val, self, type_)
				self.children[val] = child
			else:
				child = self.children[val]
				if type_:
					assert child.type in (0, type_)
					child.type = type_
					child.mask = child.mask | type_
			self.mask = self.mask | child.mask
			return child

		def regex_matcher(self, type_):
			assert type_ in (CppTree.NAMESPACES, CppTree.TYPES, CppTree.ENUM_VALUES)
			if not (type_ & self.mask):
				return None
			if not self.children:
				return self.value
			matchers = [v.regex_matcher(type_) for k, v in self.children.items()]
			matchers = [v for v in matchers if v is not None]
			if not matchers:
				if self.type == type_:
					return self.value
				return None

			grouped = len(matchers) > 1
			matchers = r'|'.join(matchers)
			if not self.value and not self.parent:  # root
				return matchers
			matchers = (r'(?:' if grouped else '') + matchers + (r')' if grouped else '')

			if self.type == type_:
				return rf'{self.value}(?:::{matchers})?'
			else:
				return rf'{self.value}::{matchers}'

	def __init__(self):
		self.root = CppTree.Node('', None)

	def add(self, val, type_):
		assert type_ in (CppTree.NAMESPACES, CppTree.TYPES, CppTree.ENUM_VALUES)
		val = [v for v in val.split(r'::') if len(v)]
		parent = self.root
		while len(val):
			v = val.pop(0)
			parent = parent.add(v, type_ if not len(val) else 0)

	def add_type(self, val):
		self.add(val, CppTree.TYPES)

	def add_namespace(self, val):
		self.add(val, CppTree.NAMESPACES)

	def add_enum_value(self, val):
		self.add(val, CppTree.ENUM_VALUES)

	def matcher(self, type_):
		return self.root.regex_matcher(type_)



#=======================================================================================================================
# Custom exceptions
#=======================================================================================================================



class Error(Exception):
	"""Base class for other exceptions."""

	def __init__(self, *message):
		self.__message = r' '.join([str(m) for m in message])
		super().__init__(*message)

	def __str__(self):
		return self.__message



class WarningTreatedAsError(Error):
	"""Raised when a warning is generated and the user has chosen to treat warnings as errors."""
	pass
