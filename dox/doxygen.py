#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

try:
	from dox.utils import *
except:
	from utils import *

import re
from pathlib import Path



#=======================================================================================================================
# FUNCTIONS
#=======================================================================================================================

def mangle_name(name):
	'''
	A lightweight version of doxygen's escapeCharsInString()
	(see https://github.com/doxygen/doxygen/blob/master/src/util.cpp)
	'''
	assert name is not None
	name = name.replace('_', '__')
	name = name.replace(':', '_1')
	name = name.replace('/', '_2')
	name = name.replace('<', '_3')
	name = name.replace('>', '_4')
	name = name.replace('*', '_5')
	name = name.replace('&', '_6')
	name = name.replace('|', '_7')
	name = name.replace('.', '_8')
	name = name.replace('!', '_9')
	name = name.replace(',', '_00')
	name = name.replace(' ', '_01')
	name = name.replace('{', '_02')
	name = name.replace('}', '_03')
	name = name.replace('?', '_04')
	name = name.replace('^', '_05')
	name = name.replace('%', '_06')
	name = name.replace('(', '_07')
	name = name.replace(')', '_08')
	name = name.replace('+', '_09')
	name = name.replace('=', '_0a')
	name = name.replace('$', '_0b')
	name = name.replace('\\','_0c')
	name = name.replace('@', '_0d')
	name = name.replace(']', '_0e')
	name = name.replace('[', '_0f')
	name = name.replace('#', '_0g')
	name = re.sub(r'[A-Z]', lambda m: '_' + m[0].lower(), name)
	return name



#=======================================================================================================================
# DOXYFILE
#=======================================================================================================================

class Doxyfile(object):

	__include = re.compile(r'@INCLUDE[ \t]*=[ \t]*(.+?)[ \t]*\n')

	def __init__(self, path, temp=False):
		assert path is not None
		if not isinstance(path, Path):
			path = Path(path)
		path = path.resolve()
		if not (path.exists() and path.is_file()):
			raise Exception(f'{path} did not exist or was not a file')
		self.__text = read_all_text_from_file(path) + '\n'
		self.path = Path(str(path) + rf'.{sha1(self.__text)}.temp') if temp else path

	def flush(self):
		print(rf'Writing {self.path}')
		with open(self.path, 'w', encoding='utf-8', newline='\n') as f:
			f.write(self.__text)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if traceback is None:
			self.flush()
