#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import sys
import re
import requests
import subprocess
import shutil
import fnmatch
import traceback
import time
import hashlib
from datetime import timedelta
from pathlib import Path
from io import StringIO


#=======================================================================================================================
# FUNCTIONS
#=======================================================================================================================

def is_collection(val):
	if isinstance(val, (list, tuple, dict, set, range)):
		return True
	return False



__verbose = False
def verbose(val = None):
	global __verbose
	if val is not None:
		__verbose = bool(val)
	return __verbose



def vprint(*args):
	global __verbose
	if __verbose:
		print(*args)



def eprint(*args):
	print(*args, file=sys.stderr)



def print_exception(exc, skip_frames = 0, file=sys.stderr):
	buf = StringIO()
	print(f'Error: [{type(exc).__name__}] {exc}', file=buf)
	tb = exc.__traceback__
	while skip_frames > 0 and tb.tb_next is not None:
		skip_frames = skip_frames - 1
		tb = tb.tb_next
	traceback.print_exception(type(exc), exc, tb, file=buf)
	print(buf.getvalue(),file=file, end='')



__entry_script_dir = None
def entry_script_dir():
	global __entry_script_dir
	if __entry_script_dir is None:
		__entry_script_dir = Path(sys.argv[0]).resolve().parent
	return __entry_script_dir



def assert_existing_file(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not (path.exists() and path.is_file()):
		raise Exception(f'{path} did not exist or was not a file')



def assert_existing_directory(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not (path.exists() and path.is_dir()):
		raise Exception(f'{path} did not exist or was not a directory')



def delete_directory(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if path.exists():
		if not path.is_dir():
			raise Exception(f'{path} was not a directory')
		print(f'Deleting {path}')
		shutil.rmtree(str(path.resolve()))



def copy_file(source, dest):
	assert source is not None
	assert dest is not None
	if not isinstance(source, Path):
		source = Path(source)
	if not isinstance(dest, Path):
		dest = Path(dest)
	assert_existing_file(source)
	print(f'Copying {source}')
	shutil.copyfile(str(source), str(dest))



def delete_file(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if path.exists():
		if not path.is_file():
			raise Exception(f'{path} was not a file')
		print(f'Deleting {path}')
		path.unlink()



def get_all_files(path, all=None, any=None, recursive=False, sort=True):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not path.exists():
		return []
	if not path.is_dir():
		raise Exception(f'{path} was not a directory')
	path = path.resolve()
	
	child_files = []
	files = []
	for p in path.iterdir():
		if p.is_dir():
			if recursive:
				child_files = child_files + get_all_files(p, all=all, any=any, recursive=True, sort=False)
		elif p.is_file():
			files.append(str(p))

	if files and all is not None:
		if (not is_collection(all)):
			all = (all,)
		all = [f for f in all if f is not None]
		for fil in all:
			files = fnmatch.filter(files, fil)

	if files and any is not None:
		if (not is_collection(any)):
			any = (any,)
		any = [f for f in any if f is not None]
		if any:
			results = set()
			for fil in any:
				results.update(fnmatch.filter(files, fil))
			files = [f for f in results]

	files = [Path(f) for f in files] + child_files
	if sort:
		files.sort()
	return files



def read_all_text_from_file(path, fallback_url=None, encoding='utf-8'):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if fallback_url is None:
		assert_existing_file(path)
	try:
		print(f'Reading {path}')
		with open(path, 'r', encoding=encoding) as f:
			text = f.read()
		return text
	except:
		if fallback_url is not None:
			print(f"Couldn't read file locally, downloading from {fallback_url}")
			response = requests.get(
				fallback_url,
				timeout=1
			)
			text = response.text
			with open(path, 'w', encoding='utf-8', newline='\n') as f:
				f.write(text)
			return text
		else:
			raise



def run_python_script(path, *args, cwd=None):
	assert path is not None
	if cwd is not None:
		cwd = str(cwd)
	assert_existing_file(path)
	subprocess.run(
		['py' if shutil.which('py') is not None else 'python3', str(path)] + [arg for arg in args],
		check=True,
		cwd=cwd
	)



def sha1(*objs):
	assert objs
	h = hashlib.sha1()
	for o in objs:
		assert o is not None
		h.update(str(o).encode('utf-8'))
	return h.hexdigest()



def regex_or(regexes, pattern_prefix = '', pattern_suffix = ''):
	regexes = [str(r) for r in regexes]
	regexes.sort()
	regexes = re.compile(pattern_prefix + '(?:' + '|'.join(regexes) + ')' + pattern_suffix)
	return regexes



#=======================================================================================================================
# SCOPE TIMER
#=======================================================================================================================

class ScopeTimer(object):

	def __init__(self, scope, verbose_only=False):
		self.__scope = str(scope)
		self.__print = vprint if verbose_only else print

	def __enter__(self):
		self.__start = time.perf_counter_ns()

	def __exit__(self ,type, value, traceback):
		if traceback is None:
			nanos = time.perf_counter_ns() - self.__start
			micros = int(nanos / 1000)
			nanos = int(nanos % 1000)
			micros = float(micros) + float(nanos) / 1000.0
			self.__print(rf'{self.__scope} completed in {timedelta(microseconds=micros)}.')



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
