#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

try:
	from dox.utils import *
except:
	from utils import *

import subprocess



#=======================================================================================================================
# functions
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


def _format_for_doxyfile(val):
	if val is None:
		return ''
	elif isinstance(val, str):
		return '"' + val.replace('"','\\"') + '"'
	elif isinstance(val, Path):
		return _format_for_doxyfile(str(val))
	elif isinstance(val, bool):
		return r'YES' if val else r'NO'
	elif isinstance(val, (int, float)):
		return str(val)
	else:
		assert False



#=======================================================================================================================
# Doxyfile
#=======================================================================================================================

class Doxyfile(object):

	__include = re.compile(r'^\s*@INCLUDE\s*=\s*(.+?)\s*$', re.M)

	def __init__(self, doxyfile_path, cwd=None, logger=None):
		# the path of the actual doxyfile
		self.path = coerce_path(doxyfile_path).resolve()

		# the working directory for doxygen invocations
		self.__cwd = Path.cwd() if cwd is None else coerce_path(cwd).resolve()
		assert_existing_directory(self.__cwd)

		# read in doxyfile (or generate one)
		self.__text = ''
		if self.path.exists():
			if not self.path.is_file():
				raise Exception(f'{self.path} was not a file')
			self.__text = read_all_text_from_file(self.path).strip()
		else:
			log(logger, rf'Warning: doxyfile {self.path} not found! A default one will be generated in-memory.', level=logging.WARNING)
			result = subprocess.run(
				r'doxygen -s -g -'.split(),
				check=True,
				capture_output=True,
				cwd=self.__cwd,
				encoding='utf-8'
			)
			self.__text = result.stdout.strip()

		# expand includes
		m = self.__include.search(self.__text)
		while m:
			inc = m[1].strip(' "')
			sub = ''
			if inc:
				inc = Path(inc)
				if not inc.is_absolute():
					inc = Path(self.__cwd, inc)
				inc = inc.resolve()
				sub = f'\n\n{read_all_text_from_file(inc).strip()}\n\n'
			self.__text = self.__text[:m.start()].strip() + sub + self.__text[m.end():].strip()
			m = self.__include.search(self.__text)

		# simplify regex searches by ensuring there's always leading and trailing newlines
		self.__text = f'\n{self.__text}\n'

	def cleanup(self):
		result = subprocess.run(
			r'doxygen -s -u -'.split(),
			check=True,
			capture_output=True,
			cwd=self.__cwd,
			encoding='utf-8',
			input=self.__text
		)
		self.__text = result.stdout.strip()

	def flush(self):
		if 1:
			self.cleanup()
		print(rf'Writing {self.path}')
		with open(self.path, 'w', encoding='utf-8', newline='\n') as f:
			print(self.__text, file=f)

	def hash(self):
		return sha1(self.__text)

	def contains(self, text):
		assert text is not None
		return self.__text.find(text) != -1

	def get_value(self, key, fallback=None):
		pattern = re.compile(rf'\n\s*{key}\s*=(.*?)\n', flags=re.S)
		text = self.__text
		m = pattern.search(text)
		while m:
			# doxygen allows values to appear multiple times and only accepts the last one, hence the loop
			text = text[m.end():]
			n = pattern.search(text)
			if not n:
				break
			m = n
		if m:
			val = m[1].strip(' "')
			return val if val else fallback
		return fallback

	def get_boolean(self, key, fallback=False):
		val = self.get_value(key)
		if val is None:
			return fallback
		return val.upper() == 'YES'

	def append(self, *args, end='\n', sep=' '):
		self.__text = rf'{self.__text}{sep.join(args)}{end}'
		return self

	def add_value(self, key, value=None):
		if value is not None:
			if isinstance(value, (list, tuple, set)):
				if value:
					for v in value:
						if v is not None:
							self.append(rf'{key:<23}+= {_format_for_doxyfile(v)}')
			else:
				self.append(rf'{key:<23}+= {_format_for_doxyfile(value)}')
		return self

	def set_value(self, key, value=None):
		if isinstance(value, (list, tuple, set)):
			first = True
			for v in value:
				if first:
					self.append(rf'{key:<23}=  {_format_for_doxyfile(v)}')
				else:
					self.add_value(key, v)
				first = False
		else:
			self.append(rf'{key:<23}=  {_format_for_doxyfile(value)}')
		return self

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if traceback is None:
			self.flush()
