#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import sys
import os
import re
import traceback
import subprocess
import random
import concurrent.futures as futures
import html
import bs4 as soup
import json
import pytomlpp
import shutil
import fnmatch
import requests
from lxml import etree
from io import BytesIO
from argparse import ArgumentParser
from pathlib import Path



#=== UTILITY FUNCTIONS =================================================================================================



def multi_sha256(*objs):
	assert objs
	h = hashlib.sha256()
	for o in objs:
		assert o is not None
		h.update(str(o).encode('utf-8'))
	return h.hexdigest()



def read_all_text_from_file(path, fallback_url=None, encoding='utf-8'):
	try:
		print(f'Reading {path}')
		with open(str(path), 'r', encoding=encoding) as f:
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
			with open(str(path), 'w', encoding='utf-8', newline='\n') as f:
				print(text, end='', file=f)
			return text
		else:
			raise



def is_collection(val):
	if isinstance(val, (list, tuple, dict, set, range)):
		return True
	return False



_script_folder = None
def this_script_dir():
	global _script_folder
	if _script_folder is None:
		_script_folder = Path(sys.argv[0]).resolve().parent
	return _script_folder
	


_verbose = False
def vprint(*args):
	global _verbose
	if _verbose:
		print(*args)



def print_exception(exc):
	print(
		f'Error: [{type(exc).__name__}] {str(exc)}',
		file=sys.stderr
	)
	traceback.print_exc(file=sys.stderr)



def delete_directory(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if path.exists():
		if not path.is_dir():
			raise Exception(f'{path} was not a directory')
		print(f'Deleting {path}')
		shutil.rmtree(str(path.resolve()))



def assert_existing_file(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not (path.exists() and path.is_file()):
		raise f'{path} did not exist or was not a file'



def assert_existing_directory(path):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not (path.exists() and path.is_dir()):
		raise f'{path} did not exist or was not a directory'



def run_python_script(path, *args, cwd=None):
	assert path is not None
	assert cwd is not None
	if not isinstance(path, Path):
		path = Path(path)
	assert_existing_file(path)
	subprocess.run(
		['py' if shutil.which('py') is not None else 'python3', str(path)] + [arg for arg in args],
		check=True,
		cwd=str(cwd)
	)



def get_all_files(path, all=None, any=None):
	assert path is not None
	if not isinstance(path, Path):
		path = Path(path)
	if not path.exists():
		return []
	if not path.is_dir():
		raise Exception(f'{path} was not a directory')
	path = path.resolve()
	files = [str(f) for f in path.iterdir() if f.is_file()]
	if (files and all is not None):
		if (not is_collection(all)):
			all = (all,)
		all = [f for f in all if f is not None]
		for fil in all:
			files = fnmatch.filter(files, fil)

	if (files and any is not None):
		if (not is_collection(any)):
			any = (any,)
		any = [f for f in any if f is not None]
		if any:
			results = set()
			for fil in any:
				results.update(fnmatch.filter(files, fil))
			files = [f for f in results]
	files.sort()
	return [Path(f) for f in files]



def copy_file(source, dest):
	assert source is not None
	assert dest is not None
	if not isinstance(source, Path):
		source = Path(source)
	if not isinstance(dest, Path):
		dest = Path(dest)
	assert_existing_file(source)
	shutil.copyfile(str(source), str(dest))



#=== CONFIG ============================================================================================================



_namespaces = (
	'std',
	'std::chrono_literals',
	'std::chrono',
	'std::complex_literals',
	'std::execution',
	'std::filesystem',
	'std::literals::chrono_literals',
	'std::literals::complex_literals',
	'std::literals::string_literals',
	'std::literals::string_view_literals',
	'std::literals',
	'std::numbers',
	'std::ranges',
	'std::string_literals',
	'std::string_view_literals',
	'std::this_thread'
)
_inline_namespaces = tuple()
_types = (
	#------ standard/built-in types
	r'_Float128',
	r'_Float16',
	r'_Float80',
	r'__float128',
	r'__float80',
	r'__fp16',
	r'__int128_t',
	r'__m128',
	r'__m128d',
	r'__m128i',
	r'__m256',
	r'__m256d',
	r'__m256i',
	r'__m512',
	r'__m512d',
	r'__m512i',
	r'__m64',
	r'__uint128_t',
	r'array',
	r'bool',
	r'byte',
	r'char',
	r'const_iterator',
	r'double',
	r'exception',
	r'float',
	r'float128_t',
	r'int',
	r'iterator',
	r'long',
	r'optional',
	r'pair',
	r'ptrdiff_t',
	r'short',
	r'signed',
	r'size_t',
	r'span',
	r'string(?:_view)?',
	r'i?o?f?(?:string)?stream',
	r'tuple',
	r'u?int(?:8|16|32|64|128)_t',
	r'u?intptr_t',
	r'unsigned',
	r'vector',
	r'wchar_t',
	#------ documentation-only types
	r'[T-V][0-9]',
	r'Foo',
	r'Bar',
	r'strong_typedef',
	r'[a-zA-Z_]+_type',
	r'[Vv]ec(?:tor)?[1-4][hifd]?',
	r'[Mm]at(?:rix)?[1-4](?:[xX][1-4])?[hifd]?'
)
_macros = (
    r'assert',
    r'offsetof'
)
_string_literals = ('s', 'sv')
_external_links = (
	(r'std::assume_aligned(?:\(\))?', 'https://en.cppreference.com/w/cpp/memory/assume_aligned'),
	(r'(?:std::)?nullptr_t', 'https://en.cppreference.com/w/cpp/types/nullptr_t'),
	(r'(?:std::)?ptrdiff_t', 'https://en.cppreference.com/w/cpp/types/ptrdiff_t'),
	(r'(?:std::)?size_t', 'https://en.cppreference.com/w/cpp/types/size_t'),
	(r'(?:std::)?u?int(?:_fast|_least)?(?:8|16|32|64)_ts?', 'https://en.cppreference.com/w/cpp/types/integer'),
	(r'(?:std::)?u?int(?:max|ptr)_t', 'https://en.cppreference.com/w/cpp/types/integer'),
	(r'(?:wchar|char(?:8|16|32))_ts?', 'https://en.cppreference.com/w/cpp/language/types#Character_types'),
	(r'\s(?:<|&lt;)fstream(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/fstream'),
	(r'\s(?:<|&lt;)iosfwd(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/iosfwd'),
	(r'\s(?:<|&lt;)iostream(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/iostream'),
	(r'\s(?:<|&lt;)sstream(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/sstream'),
	(r'\s(?:<|&lt;)string(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/string'),
	(r'\s(?:<|&lt;)string_view(?:>|&gt;)', 'https://en.cppreference.com/w/cpp/header/string_view'),
	(r'const_cast','https://en.cppreference.com/w/cpp/language/const_cast'),
	(r'dynamic_cast','https://en.cppreference.com/w/cpp/language/dynamic_cast'),
	(r'reinterpret_cast','https://en.cppreference.com/w/cpp/language/reinterpret_cast'),
	(r'static_cast','https://en.cppreference.com/w/cpp/language/static_cast'),
	(r'std::(?:basic_|w)?fstreams?', 'https://en.cppreference.com/w/cpp/io/basic_fstream'),
	(r'std::(?:basic_|w)?ifstreams?', 'https://en.cppreference.com/w/cpp/io/basic_ifstream'),
	(r'std::(?:basic_|w)?iostreams?', 'https://en.cppreference.com/w/cpp/io/basic_iostream'),
	(r'std::(?:basic_|w)?istreams?', 'https://en.cppreference.com/w/cpp/io/basic_istream'),
	(r'std::(?:basic_|w)?istringstreams?', 'https://en.cppreference.com/w/cpp/io/basic_istringstream'),
	(r'std::(?:basic_|w)?ofstreams?', 'https://en.cppreference.com/w/cpp/io/basic_ofstream'),
	(r'std::(?:basic_|w)?ostreams?', 'https://en.cppreference.com/w/cpp/io/basic_ostream'),
	(r'std::(?:basic_|w)?ostringstreams?', 'https://en.cppreference.com/w/cpp/io/basic_ostringstream'),
	(r'std::(?:basic_|w)?stringstreams?', 'https://en.cppreference.com/w/cpp/io/basic_stringstream'),
	(r'std::(?:basic_|w|u(?:8|16|32))?string_views?', 'https://en.cppreference.com/w/cpp/string/basic_string_view'),
	(r'std::(?:basic_|w|u(?:8|16|32))?strings?', 'https://en.cppreference.com/w/cpp/string/basic_string'),
	(r'std::[fl]?abs[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/abs'),
	(r'std::acos[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/acos'),
	(r'std::add_[lr]value_reference(?:_t)?', 'https://en.cppreference.com/w/cpp/types/add_reference'),
	(r'std::add_(?:cv|const|volatile)(?:_t)?', 'https://en.cppreference.com/w/cpp/types/add_cv'),
	(r'std::add_pointer(?:_t)?', 'https://en.cppreference.com/w/cpp/types/add_pointer'),
	(r'std::allocators?', 'https://en.cppreference.com/w/cpp/memory/allocator'),
	(r'std::arrays?', 'https://en.cppreference.com/w/cpp/container/array'),
	(r'std::as_(writable_)?bytes(?:\(\))?', 'https://en.cppreference.com/w/cpp/container/span/as_bytes'),
	(r'std::asin[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/asin'),
	(r'std::atan2[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/atan2'),
	(r'std::atan[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/atan'),
	(r'std::bad_alloc', 'https://en.cppreference.com/w/cpp/memory/new/bad_alloc'),
	(r'std::bit_cast(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/bit_cast'),
	(r'std::bit_ceil(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/bit_ceil'),
	(r'std::bit_floor(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/bit_floor'),
	(r'std::bit_width(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/bit_width'),
	(r'std::bytes?', 'https://en.cppreference.com/w/cpp/types/byte'),
	(r'std::ceil[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/ceil'),
	(r'std::char_traits', 'https://en.cppreference.com/w/cpp/string/char_traits'),
	(r'std::chrono::durations?', 'https://en.cppreference.com/w/cpp/chrono/duration'),
	(r'std::clamp(?:\(\))?', 'https://en.cppreference.com/w/cpp/algorithm/clamp'),
	(r'std::conditional(?:_t)?', 'https://en.cppreference.com/w/cpp/types/conditional'),
	(r'std::cos[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/cos'),
	(r'std::countl_one(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/countl_one'),
	(r'std::countl_zero(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/countl_zero'),
	(r'std::countr_one(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/countr_one'),
	(r'std::countr_zero(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/countr_zero'),
	(r'std::enable_if(?:_t)?', 'https://en.cppreference.com/w/cpp/types/enable_if'),
	(r'std::exceptions?', 'https://en.cppreference.com/w/cpp/error/exception'),
	(r'std::floor[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/floor'),
	(r'std::has_single_bit(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/has_single_bit'),
	(r'std::hash', 'https://en.cppreference.com/w/cpp/utility/hash'),
	(r'std::initializer_lists?', 'https://en.cppreference.com/w/cpp/utility/initializer_list'),
	(r'std::integral_constants?', 'https://en.cppreference.com/w/cpp/types/integral_constant'),
	(r'std::is_(?:nothrow_)?convertible(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_convertible'),
	(r'std::is_(?:nothrow_)?invocable(?:_r)?', 'https://en.cppreference.com/w/cpp/types/is_invocable'),
	(r'std::is_base_of(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_base_of'),
	(r'std::is_constant_evaluated(?:\(\))?', 'https://en.cppreference.com/w/cpp/types/is_constant_evaluated'),
	(r'std::is_enum(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_enum'),
	(r'std::is_floating_point(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_floating_point'),
	(r'std::is_integral(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_integral'),
	(r'std::is_pointer(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_pointer'),
	(r'std::is_reference(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_reference'),
	(r'std::is_same(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_same'),
	(r'std::is_signed(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_signed'),
	(r'std::is_unsigned(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_unsigned'),
	(r'std::is_void(?:_v)?', 'https://en.cppreference.com/w/cpp/types/is_void'),
	(r'std::launder(?:\(\))?', 'https://en.cppreference.com/w/cpp/utility/launder'),
	(r'std::lerp(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/lerp'),
	(r'std::maps?', 'https://en.cppreference.com/w/cpp/container/map'),
	(r'std::max(?:\(\))?', 'https://en.cppreference.com/w/cpp/algorithm/max'),
	(r'std::min(?:\(\))?', 'https://en.cppreference.com/w/cpp/algorithm/min'),
	(r'std::numeric_limits::lowest(?:\(\))?', 'https://en.cppreference.com/w/cpp/types/numeric_limits/lowest'),
	(r'std::numeric_limits', 'https://en.cppreference.com/w/cpp/types/numeric_limits'),
	(r'std::optionals?', 'https://en.cppreference.com/w/cpp/utility/optional'),
	(r'std::pairs?', 'https://en.cppreference.com/w/cpp/utility/pair'),
	(r'std::popcount(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/popcount'),
	(r'std::remove_cv(?:_t)?', 'https://en.cppreference.com/w/cpp/types/remove_cv'),
	(r'std::remove_reference(?:_t)?', 'https://en.cppreference.com/w/cpp/types/remove_reference'),
	(r'std::reverse_iterator', 'https://en.cppreference.com/w/cpp/iterator/reverse_iterator'),
	(r'std::runtime_errors?', 'https://en.cppreference.com/w/cpp/error/runtime_error'),
	(r'std::sets?', 'https://en.cppreference.com/w/cpp/container/set'),
	(r'std::shared_ptrs?', 'https://en.cppreference.com/w/cpp/memory/shared_ptr'),
	(r'std::sin[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/sin'),
	(r'std::spans?', 'https://en.cppreference.com/w/cpp/container/span'),
	(r'std::sqrt[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/sqrt'),
	(r'std::tan[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/tan'),
	(r'std::to_address(?:\(\))?', 'https://en.cppreference.com/w/cpp/memory/to_address'),
	(r'std::(?:true|false)_type', 'https://en.cppreference.com/w/cpp/types/integral_constant'),
	(r'std::trunc[fl]?(?:\(\))?', 'https://en.cppreference.com/w/cpp/numeric/math/trunc'),
	(r'std::tuple_element(?:_t)?', 'https://en.cppreference.com/w/cpp/utility/tuple/tuple_element'),
	(r'std::tuple_size(?:_v)?', 'https://en.cppreference.com/w/cpp/utility/tuple/tuple_size'),
	(r'std::tuples?', 'https://en.cppreference.com/w/cpp/utility/tuple'),
	(r'std::type_identity(?:_t)?', 'https://en.cppreference.com/w/cpp/types/type_identity'),
	(r'std::underlying_type(?:_t)?', 'https://en.cppreference.com/w/cpp/types/underlying_type'),
	(r'std::unique_ptrs?', 'https://en.cppreference.com/w/cpp/memory/unique_ptr'),
	(r'std::unordered_maps?', 'https://en.cppreference.com/w/cpp/container/unordered_map'),
	(r'std::unordered_sets?', 'https://en.cppreference.com/w/cpp/container/unordered_set'),
	(r'std::vectors?', 'https://en.cppreference.com/w/cpp/container/vector'),
	(
		r'std::atomic(?:_(?:'
			+ r'bool|[su]?char(?:8_t|16_t|32_t)?|u?short'
			+ r'|u?int(?:8_t|16_t|32_t|64_t)?|u?l?long'
			+ r'))?',
		'https://en.cppreference.com/w/cpp/atomic/atomic'
	),
	(
		r'(?:L?P)?(?:'
			+ r'D?WORD(?:32|64|_PTR)?|HANDLE|HMODULE|BOOL(?:EAN)?'
			+ r'|U?SHORT|U?LONG|U?INT(?:8|16|32|64)?'
			+ r'|BYTE|VOID|C[WT]?STR'
			+ r')',
		'https://docs.microsoft.com/en-us/windows/desktop/winprog/windows-data-types'
	),
	(
		r'(?:__INTELLISENSE__|_MSC_FULL_VER|_MSC_VER|_MSVC_LANG|_WIN32|_WIN64)',
		'https://docs.microsoft.com/en-us/cpp/preprocessor/predefined-macros?view=vs-2019'
	),
	(r'IUnknowns?', 'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nn-unknwn-iunknown'),
	(r'(?:IUnknown::)?QueryInterface?', 'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface(q)'),
	(r'(?:Legacy)?InputIterators?', 'https://en.cppreference.com/w/cpp/named_req/InputIterator'),
	(r'(?:Legacy)?OutputIterators?', 'https://en.cppreference.com/w/cpp/named_req/OutputIterator'),
	(r'(?:Legacy)?ForwardIterators?', 'https://en.cppreference.com/w/cpp/named_req/ForwardIterator'),
	(r'(?:Legacy)?BidirectionalIterators?', 'https://en.cppreference.com/w/cpp/named_req/BidirectionalIterator'),
	(r'(?:Legacy)?RandomAccessIterators?', 'https://en.cppreference.com/w/cpp/named_req/RandomAccessIterator'),
	(r'(?:Legacy)?ContiguousIterators?', 'https://en.cppreference.com/w/cpp/named_req/ContiguousIterator'),
	(
		r'(?:'
			+ r'__cplusplus|__STDC_HOSTED__'
			+ r'|__FILE__|__LINE__'
			+ r'|__DATE__|__TIME__'
			+ r'|__STDCPP_DEFAULT_NEW_ALIGNMENT__'
			+ r')',
		'https://en.cppreference.com/w/cpp/preprocessor/replace'
	),
	(r'(?:_Float|__fp)16s?','https://gcc.gnu.org/onlinedocs/gcc/Half-Precision.html'),
	(r'(?:_Float|__float)(128|80)s?','https://gcc.gnu.org/onlinedocs/gcc/Floating-Types.html')
)
_implementation_headers = tuple()
_badges = tuple()



#=== HTML DOCUMENT =====================================================================================================



class HTMLDocument(object):

	def __init__(self, path):
		self.__path = path
		with open(path, 'r', encoding='utf-8') as f:
			self.__doc = soup.BeautifulSoup(f, 'html5lib', from_encoding='utf-8')
		self.head = self.__doc.head
		self.body = self.__doc.body
		self.table_of_contents = None
		self.article_content = self.__doc.body.main.article.div.div.div
		toc_candidates = self.article_content('div', class_='m-block m-default', recursive=False)
		for div in toc_candidates:
			if div.h3 and div.h3.string == 'Contents':
				self.table_of_contents = div
				break
		self.sections = self.article_content('section', recursive=False)

	def smooth(self):
		self.__doc.smooth()

	def flush(self):
		with open(self.__path, 'w', encoding='utf-8', newline='\n') as f:
			f.write(str(self.__doc))

	def new_tag(self, name, parent=None, string=None, class_=None, index=None, before=None, after=None, **kwargs):
		tag = self.__doc.new_tag(name, **kwargs)
		if (string is not None):
			if (tag.string is not None):
				tag.string.replace_with(string)
			else:
				tag.string = soup.NavigableString(string)
		if (class_ is not None):
			tag['class'] = class_
		if (before is not None):
			before.insert_before(tag)
		elif (after is not None):
			after.insert_after(tag)
		elif (parent is not None):
			if (index is None or index < 0):
				parent.append(tag)
			else:
				parent.insert(index, tag)

		return tag

	def find_all_from_sections(self, name=None, select=None, section=None, include_toc=False, **kwargs):
		tags = []
		sections = None
		if (section is not None):
			sections = self.article_content('section', recursive=False, id='section')
		else:
			sections = self.sections
		if include_toc and self.table_of_contents is not None:
			sections = [self.table_of_contents, *sections]
		for sect in sections:
			matches = sect(name, **kwargs) if name is not None else [ sect ]
			if (select is not None):
				newMatches = []
				for match in matches:
					newMatches += match.select(select)
				matches = newMatches
			tags += matches
		return tags



def html_find_parent(tag, names, cutoff=None):
	if not is_collection(names):
		names = [ names ]
	parent = tag.parent
	while (parent is not None):
		if (cutoff is not None and parent is cutoff):
			return None
		if parent.name in names:
			return parent;
		parent = parent.parent
	return parent



def html_destroy_node(node):
	assert node is not None
	if (isinstance(node, soup.NavigableString)):
		node.extract()
	else:
		node.decompose()



def html_replace_tag(tag, new_tag_str):
	newTags = []
	if new_tag_str:
		doc = soup.BeautifulSoup(new_tag_str, 'html5lib')
		if (len(doc.body.contents) > 0):
			newTags = [f for f in doc.body.contents]
			newTags = [f.extract() for f in newTags]
			prev = tag
			for newTag in newTags:
				prev.insert_after(newTag)
				prev = newTag
	html_destroy_node(tag)
	return newTags



def html_shallow_search(starting_tag, names, filter = None):
	if isinstance(starting_tag, soup.NavigableString):
		return []

	if not is_collection(names):
		names = [ names ]

	if starting_tag.name in names:
		if filter is None or filter(starting_tag):
			return [ starting_tag ]

	results = []
	for tag in starting_tag.children:
		if isinstance(tag, soup.NavigableString):
			continue
		if tag.name in names:
			if filter is None or filter(tag):
				results.append(tag)
		else:
			results = results + html_shallow_search(tag, names, filter)
	return results



def html_string_descendants(starting_tag, filter = None):
	if isinstance(starting_tag, soup.NavigableString):
		if filter is None or filter(starting_tag):
			return [ starting_tag ]

	results = []
	for tag in starting_tag.children:
		if isinstance(tag, soup.NavigableString):
			if filter is None or filter(tag):
				results.append(tag)
		else:
			results = results + html_string_descendants(tag, filter)
	return results



def html_add_class(tag, classes):
	appended = False
	if 'class' not in tag.attrs:
		tag['class'] = []
	if not is_collection(classes):
		classes = (classes,)
	for class_ in classes:
		if class_ not in tag['class']:
			tag['class'].append(class_)
			appended = True
	return appended



def html_remove_class(tag, classes):
	removed = False
	if 'class' in tag.attrs:
		if not is_collection(classes):
			classes = (classes,)
		for class_ in classes:
			if class_ in tag['class']:
				tag['class'].remove(class_)
				removed = True
		if removed and len(tag['class']) == 0:
			del tag['class']
	return removed



def html_set_class(tag, classes):
	tag['class'] = []
	html_add_class(tag, classes)



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



# allows the injection of custom tags using square-bracketed proxies.
class CustomTagsFix(object):
	__double_tags = re.compile(r"\[\s*(span|div|aside|code|pre|h1|h2|h3|h4|h5|h6|em|strong|b|i|u|li|ul|ol)(.*?)\s*\](.*?)\[\s*/\s*\1\s*\]", re.I)
	__single_tags = re.compile(r"\[\s*(/?(?:span|div|aside|code|pre|emoji|set_name|(?:add|remove|set)_class|br|li|ul|ol|(?:html)?entity))(\s+[^\]]+?)?\s*\]", re.I)
	__allowed_parents = ('dd', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'aside')
	__emojis = None
	__emoji_codepoints = None
	__emoji_uri = re.compile(r".+unicode/([0-9a-fA-F]+)[.]png.*", re.I)

	@classmethod
	def __double_tags_substitute(cls, m, out):
		return f'<{m[1]}{html.unescape(m[2])}>{m[3]}</{m[1]}>'

	@classmethod
	def __single_tags_substitute(cls, m, out):
		tag_name = m[1].lower()
		tag_content = m[2].strip() if m[2] else ''
		if tag_name == 'htmlentity' or tag_name == 'entity':
			if not tag_content:
				return ''
			try:
				cp = int(tag_content, 16)
				if cp <= 0x10FFFF:
					return f'&#x{cp:X};'
			except:
				pass
			return f'&{tag_content};'
		elif tag_name == 'emoji':
			tag_content = tag_content.lower()
			if not tag_content:
				return ''
			if cls.__emojis is None:
				file_path = os.path.join(this_script_dir(), 'emojis_v2.json')
				cls.__emojis = json.loads(read_all_text_from_file(file_path, 'https://api.github.com/emojis'))
				if '__processed' not in cls.__emojis:
					emojis = {}
					cls.__emoji_codepoints = set()
					for key, uri in cls.__emojis.items():
						m2 = cls.__emoji_uri.fullmatch(uri)
						if m2:
							cp = int(m2[1], 16)
							emojis[key] = [ cp, uri ]
							cls.__emoji_codepoints.add(cp)
					aliases = [
						('sundae', 'ice_cream'),
						('info', 'information_source')
					]
					for alias, key in aliases:
						emojis[alias] = emojis[key]
					emojis['__codepoints'] = [cp for cp in cls.__emoji_codepoints]
					emojis['__processed'] = True
					with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
						f.write(json.dumps(emojis, sort_keys=True, indent=4))
					cls.__emojis = emojis
			if cls.__emoji_codepoints is None:
				cls.__emoji_codepoints = set()
				for cp in cls.__emojis['__codepoints']:
					cls.__emoji_codepoints.add(cp)
			for base in (16, 10):
				try:
					cp = int(tag_content, base)
					if cp in cls.__emoji_codepoints:
						return f'&#x{cp:X};&#xFE0F;'
				except:
					pass
			if tag_content in cls.__emojis:
				cp = cls.__emojis[tag_content][0]
				return f'&#x{cp:X};&#xFE0F;'
			return ''
		elif tag_name in ('add_class', 'remove_class', 'set_class'):
			classes = []
			if tag_content:
				for s in tag_content.split():
					if s:
						classes.append(s)
			if classes:
				out.append((tag_name, classes))
			return ''
		elif tag_name == 'set_name':
			if tag_content:
				out.append((tag_name, tag_content))
			return ''
		else:
			return f'<{m[1]}{(" " + tag_content) if tag_content else ""}>'

	def __call__(self, dir, file, doc):
		changed = False
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for name in self.__allowed_parents:
				tags = doc.article_content.find_all(name)
				for tag in tags:
					if len(tag.contents) == 0 or html_find_parent(tag, 'a', doc.article_content) is not None or tag.decomposed:
						continue
					replacer = RegexReplacer(self.__double_tags, self.__double_tags_substitute, str(tag))
					if replacer:
						changed_this_pass = True
						html_replace_tag(tag, str(replacer))
						continue
					replacer = RegexReplacer(self.__single_tags, self.__single_tags_substitute, str(tag))
					if replacer:
						changed_this_pass = True
						parent = tag.parent
						html_replace_tag(tag, str(replacer))
						for i in range(len(replacer)):
							if replacer[i][0] == 'add_class':
								if parent is not None:
									html_add_class(parent, replacer[i][1])
							elif replacer[i][0] == 'remove_class':
								if parent is not None:
									html_remove_class(parent, replacer[i][1])
							elif replacer[i][0] == 'set_class':
								if parent is not None:
									html_set_class(parent, replacer[i][1])
							elif replacer[i][0] == 'set_name':
								if parent is not None:
									parent.name = replacer[i][1]
						continue
			if changed_this_pass:
				doc.smooth()
				changed = True
		return changed



#=======================================================================================================================



# base type for modifier parsing fixers.
class ModifiersFixBase(object):
	_modifierRegex = r"defaulted|noexcept|constexpr|(?:pure )?virtual|protected|__(?:(?:vector|std|fast)call|cdecl)"
	_modifierClasses = {
		"defaulted" : "m-info",
		"noexcept" : "m-success",
		"constexpr" : "m-primary",
		"pure virtual" : "m-warning",
		"virtual" : "m-warning",
		"protected" : "m-warning",
		"__vectorcall" : "m-special",
		"__stdcall" : "m-special",
		"__fastcall" : "m-special",
		"__cdecl" : "m-special"
	}



#=======================================================================================================================



# fixes improperly-parsed modifiers on function signatures in the various 'detail view' sections.
class ModifiersFix1(ModifiersFixBase):

	__expression = re.compile(rf'(\s+)({ModifiersFixBase._modifierRegex})(\s+)')
	__sections = ('pub-static-methods', 'pub-methods', 'friends', 'func-members')

	@classmethod
	def __substitute(cls, m, out):
		return f'{m[1]}<span class="dox-injected m-label m-flat {cls._modifierClasses[m[2]]}">{m[2]}</span>{m[3]}'

	def __call__(self, dir, file, doc):
		changed = False
		for sect in self.__sections:
			tags = doc.find_all_from_sections('dt', select='span.m-doc-wrap', section=sect)
			for tag in tags:
				replacer = RegexReplacer(self.__expression, self.__substitute, str(tag))
				if (replacer):
					changed = True
					html_replace_tag(tag, str(replacer))
		return changed



#=======================================================================================================================



# fixes improperly-parsed modifiers on function signatures in the 'Function documentation' section.
class ModifiersFix2(ModifiersFixBase):

	__expression = re.compile(rf'\s+({ModifiersFixBase._modifierRegex})\s+')

	@classmethod
	def __substitute(cls, m, matches):
		matches.append(m[1])
		return ' '

	def __call__(self, dir, file, doc):
		changed = False
		sections = doc.find_all_from_sections(section=False) # all sections without an id
		section = None
		for s in sections:
			if (str(s.h2.string) == 'Function documentation'):
				section = s
				break
		if (section is not None):
			funcs = section(id=True)
			funcs = [f.find('h3') for f in funcs]
			for f in funcs:
				bumper = f.select_one('span.m-doc-wrap-bumper')
				end = f.select_one('span.m-doc-wrap').contents
				end = end[len(end)-1]
				matches = []
				bumperContent = self.__expression.sub(lambda m: self.__substitute(m, matches), str(bumper))
				if (matches):
					changed = True
					html_replace_tag(bumper, bumperContent)
					lastInserted = end.find('span')
					for match in matches:
						lastInserted = doc.new_tag('span',
							parent=end,
							string=match,
							class_=f'dox-injected m-label {self._modifierClasses[match]}',
							before=lastInserted
						)
						lastInserted.insert_after(' ')
		return changed



#=======================================================================================================================



# applies some basic fixes to index.html
class IndexPageFix(object):

	def __call__(self, dir, file, doc):
		global _badges
		if file != 'index.html':
			return False
		parent = doc.article_content
		banner = parent('img')
		if banner:
			banner = banner[0].extract()
			parent('h1')[0].replace_with(banner)
			parent = doc.new_tag('div', class_='gh-badges', after=banner)
			for (alt, src, href) in _badges:
				if alt is None and src is None and href is None:
					doc.new_tag('br', parent=parent)
				else:
					anchor = doc.new_tag('a', parent=parent, href=href, target='_blank')
					doc.new_tag('img', parent=anchor, src=src, alt=alt)
			html_add_class(banner, 'main_page_banner')
			return True
		return False



#=======================================================================================================================



# apply some fixes to code blocks
class CodeBlockFix(object):

	__keywords = (
		'alignas',
		'alignof',
		'bool',
		'char',
		'char16_t',
		'char32_t',
		'char8_t',
		'class',
		'const',
		'consteval',
		'constexpr',
		'constinit',
		'do',
		'double',
		'else',
		'explicit',
		'false',
		'float',
		'if',
		'inline',
		'int',
		'long',
		'mutable',
		'noexcept',
		'short',
		'signed',
		'sizeof',
		'struct',
		'template',
		'true',
		'typename',
		'unsigned',
		'void',
		'wchar_t',
		'while',
	)

	__ns_token_expr = re.compile(r'(?:::|[a-zA-Z_][a-zA-Z_0-9]*|::[a-zA-Z_][a-zA-Z_0-9]*|[a-zA-Z_][a-zA-Z_0-9]*::)')
	__ns_full_expr = re.compile(r'(?:::)?[a-zA-Z_][a-zA-Z_0-9]*(::[a-zA-Z_][a-zA-Z_0-9]*)*(?:::)?')

	def __init__(self):
		global _types
		global _macros
		self.__types = []
		self.__macros = []
		for expr in _types:
			self.__types.append(re.compile(expr))
		for expr in _macros:
			self.__macros.append(re.compile(expr))


	def __call__(self, dir, file, doc):
		global _namespaces
		global _string_literals

		# fix up syntax highlighting
		code_blocks = doc.body(('pre','code'), class_='m-code')
		changed = False
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for code_block in code_blocks:
				changed_this_block = False

				# c-style multi-line comments (doxygen butchers them)
				mlc_open = code_block.find('span', class_='o', string='/!*')
				while mlc_open is not None:
					mlc_close = mlc_open.find_next_sibling('span', class_='o', string='*!/')
					if mlc_close is None:
						break
					changed_this_block = True
					next_open = mlc_close.find_next_sibling('span', class_='o', string='/!*')

					tags = []
					current = mlc_open
					while current is not None:
						tags.append(current)
						if current is mlc_close:
							break
						current = current.next_sibling

					mlc_open.string = '/*'
					mlc_close.string = '*/'
					string = ''
					for tag in tags:
						string = string + tag.string
					mlc_open.string = string
					html_set_class(mlc_open, 'c1')
					while len(tags) > 1:
						html_destroy_node(tags.pop())

					mlc_open = next_open

				# collect all names
				names = [n for n in code_block('span', class_='n') if n.string is not None]

				# namespaces
				names_ = [n for n in names]
				for n in names:

					if (n.decomposed # handled by previous iteration
						or 'n' not in n['class'] 
						or self.__ns_token_expr.fullmatch(n.string) is None):
						continue

					current = n
					tags = [ current ]
					while True:
						prev = current.previous_sibling
						if (prev is None
							or prev.string is None
							or isinstance(prev, soup.NavigableString)
							or 'class' not in prev.attrs
							or ('n' not in prev['class'] and 'o' not in prev['class'])
							or self.__ns_token_expr.fullmatch(prev.string) is None):
							break
						current = prev
						tags.insert(0, current)

					current = n
					while True:
						next = current.next_sibling
						if (next is None
							or next.string is None
							or isinstance(next, soup.NavigableString)
							or 'class' not in next.attrs
							or ('n' not in next['class'] and 'o' not in next['class'])
							or self.__ns_token_expr.fullmatch(next.string) is None):
							break
						current = next
						tags.append(current)

					full_str = None
					while tags:
						full_str = ''.join([tag.string for tag in tags])
						if self.__ns_full_expr.fullmatch(current.string) is not None and full_str in _namespaces:
							break
						tags.pop()
					if not tags:
						continue

					while len(tags) > 1:
						t = tags.pop()
						try:
							names_.remove(t)
						except Exception:
							pass
						t.decompose()

					tags[0].string = full_str
					if not html_remove_class(tags[0], 'o'):
						html_remove_class(tags[0], 'n')
						names_.remove(tags[0])
					html_add_class(tags[0], 'ns')

					changed_this_block = True
				names = names_

				# string literals
				for i in range(len(names)-1, -1, -1):
					if (names[i].string not in _string_literals):
						continue
					prev = names[i].previous_sibling
					if (prev is None or 'class' not in prev.attrs or 's' not in prev['class']):
						continue
					names[i]['class'] = 'sa'
					del names[i]
					changed_this_block = True

				# preprocessor macros
				names = names + [n for n in code_block('span', class_='nc') if n.string is not None]
				names = names + [n for n in code_block('span', class_='nf') if n.string is not None]
				names = names + [n for n in code_block('span', class_='nl') if n.string is not None]
				if self.__macros:
					for i in range(len(names)-1, -1, -1):
						matched = False
						for expr in self.__macros:
							if expr.fullmatch(names[i].string) is not None:
								matched = True
								break
						if not matched:
							continue
						names[i]['class'] = 'm'
						del names[i]
						changed_this_block = True

				# types and typedefs
				names = names + [n for n in code_block('span', class_='kt') if n.string is not None]
				for i in range(len(names)-1, -1, -1):
					if (names[i].previous_sibling is not None and names[i].previous_sibling.string.endswith('~')):
						continue
					if (names[i].next_sibling is not None and names[i].next_sibling.string.startswith('(')):
						continue
					matched = False
					for expr in self.__types:
						if expr.fullmatch(names[i].string) is not None:
							matched = True
							break
					if not matched:
						continue
					names[i]['class'] = 'ut'
					del names[i]
					changed_this_block = True

				# misidentifed keywords
				for keywordClass in ['nf', 'nb', 'kt', 'ut', 'kr']:
					kws = code_block('span', class_=keywordClass)
					for kw in kws:
						if (kw.string is not None and kw.string in self.__keywords):
							kw['class'] = 'k'
							changed_this_block = True

				if changed_this_block:
					code_block.smooth()
					changed_this_pass = True
			changed = changed or changed_this_pass

		# fix doxygen butchering code blocks as inline nonsense
		code_blocks = doc.body('code', class_=('m-code', 'm-console'))
		changed = False
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for code_block in code_blocks:
				parent = code_block.parent
				if (parent is None
					or parent.name != 'p'
					or parent.parent is None
					or parent.parent.name != 'div'):
					continue
				changed_this_pass = True
				code_block.name = 'pre'
				parent.insert_before(code_block.extract())
				parent.smooth()
				if (not parent.contents
					or (len(parent.contents) == 1
						and parent.contents[0].string.strip() == '')):
					html_destroy_node(parent)

			changed = changed or changed_this_pass

		return changed



#=======================================================================================================================



# adds links to external sources where appropriate
class ExtDocLinksFix(object):

	__allowedNames = ('dd', 'p', 'dt', 'h3', 'td', 'div', 'figcaption')

	def __init__(self):
		global _external_links
		self.__expressions = []
		for expr, uri in _external_links:
			self.__expressions.append((re.compile('(?<![a-zA-Z_])' + expr + '(?![a-zA-Z_])'), uri))

	@classmethod
	def __substitute(cls, m, uri):
		external = uri.startswith('http')
		return rf'''<a href="{uri}" class="m-doc dox-injected{' dox-external' if external else ''}"{' target="_blank"' if external else ''}>{m[0]}</a>'''

	def __call__(self, dir, file, doc):
		changed = False
		tags = html_shallow_search(doc.article_content, self.__allowedNames, lambda t: html_find_parent(t, 'a', doc.article_content) is None)
		strings = []
		for tag in tags:
			strings = strings + html_string_descendants(tag, lambda t: html_find_parent(t, 'a', tag) is None)
		for expr, uri in self.__expressions:
			i = 0
			while i < len(strings):
				string = strings[i]
				parent = string.parent
				replacer = RegexReplacer(expr, lambda m, out: self.__substitute(m, uri), html.escape(str(string), quote=False))
				if replacer:
					repl_str = str(replacer)
					begins_with_ws = len(repl_str) > 0 and repl_str[:1].isspace()
					new_tags = html_replace_tag(string, repl_str)
					if (begins_with_ws and new_tags[0].string is not None and not new_tags[0].string[:1].isspace()):
						new_tags[0].insert_before(' ')
					changed = True
					del strings[i]
					for tag in new_tags:
						strings = strings + html_string_descendants(tag, lambda t: html_find_parent(t, 'a', parent) is None)
					continue
				i = i + 1
		return changed



#=======================================================================================================================



# fixes various minor issues with anchor tags
class LinksFix(object):

	__external_href = re.compile(r'^(?:https?|s?ftp|mailto)[:].+$', re.I)
	__internal_doc_id = re.compile(r'^[a-fA-F0-9]+$')
	__internal_doc_id_href = re.compile(r'^#([a-fA-F0-9]+)$')
	__godbolt = re.compile(r'^\s*https[:]//godbolt.org/z/.+?$', re.I)

	def __call__(self, dir, file, doc):
		changed = False
		for anchor in doc.body('a', recursive=True):
			if 'href' not in anchor.attrs:
				continue

			# make sure links to certain external sources are correctly marked as such
			if self.__external_href.fullmatch(anchor['href']) is not None:
				if 'target' not in anchor.attrs or anchor['target'] != '_blank':
					anchor['target'] = '_blank'
					changed = True
				changed = html_add_class(anchor, 'dox-external') or changed

				# do magic with godbolt.org links
				if self.__godbolt.fullmatch(anchor['href']):
					changed = html_add_class(anchor, 'godbolt') or changed
					if anchor.parent.name == 'p' and len(anchor.parent.contents) == 1:
						changed = html_add_class(anchor.parent, ('m-note', 'm-success', 'godbolt')) or changed
						if anchor.parent.next_sibling is not None and anchor.parent.next_sibling.name == 'pre':
							code_block = anchor.parent.next_sibling
							code_block.insert(0, anchor.parent.extract())
				continue

			# make sure internal documentation links actually have somewhere to go
			if 'class' in anchor.attrs and 'm-doc' in anchor['class']:
				m = self.__internal_doc_id_href.fullmatch(anchor['href'])
				if m is not None and doc.body.find(id=m[1], recursive=True) is None:
					html_remove_class(anchor, 'm-doc')
					html_add_class(anchor, 'm-doc-self')
					anchor['href'] = '#'
					parent_with_id = anchor.find_parent(id=True)
					while parent_with_id is not None:
						if self.__internal_doc_id.fullmatch(parent_with_id['id']) is not None:
							anchor['href'] = '#' + parent_with_id['id']
							break
						parent_with_id = parent_with_id.find_parent(id=True)


		return changed



#=======================================================================================================================



# spreads consecutive template <> declarations out over multiple lines
class TemplateTemplateFix(object):

	__expression = re.compile(r'(template&lt;.+?&gt;)\s+(template&lt;)', re.S)

	@classmethod
	def __substitute(cls, m):
		return f'{m[1]}<br>\n{m[2]}'

	def __call__(self, dir, file, doc):
		changed = False
		for template in doc.body('div', class_='m-doc-template'):
			replacer = RegexReplacer(self.__expression, lambda m, out: self.__substitute(m), str(template))
			if replacer:
				html_replace_tag(template, str(replacer))
				changed = True
		return changed



#=======================================================================================================================



# fix dead links to non-existent local files.
class DeadLinksFix(object):

	__href = re.compile(r'^([-_a-zA-Z0-9]+\.html?)(?:#(.*))?$')

	def __call__(self, dir, file, doc):
		changed = False
		for anchor in doc.body('a', recursive=True):
			match = self.__href.fullmatch(anchor['href'])
			if match and not os.path.exists(os.path.join(dir, match[1])):
				html_remove_class(anchor, 'm-doc')
				if anchor.parent is not None and anchor.parent.name in ('dt', 'div'):
					html_add_class(anchor, 'm-doc-self')
					id = None
					if 'id' in anchor.parent.attrs:
						id = anchor.parent['id']
					else:
						id = match[2]
						if not id:
							id = f'{multi_sha256(match[1], anchor.string)}'
						anchor.parent['id'] = id
					anchor['href'] = f'#{id}'
				changed = True
		return changed



#=======================================================================================================================



_thread_error = False
def postprocess_file(dir, file, fixes):

	global _thread_error
	if (_thread_error):
		return False
	print(f'Post-processing {file}')
	changed = False

	try:
		doc = HTMLDocument(os.path.join(dir, file))
		file = file.lower()
		for fix in fixes:
			if fix(dir, file, doc):
				doc.smooth()
				changed = True
		if (changed):
			doc.flush()

	except Exception as err:
		print_exception(err)
		_thread_error = True

	return changed



# this is a lightweight version of doxygen's escapeCharsInString()
# (see https://github.com/doxygen/doxygen/blob/master/src/util.cpp)
def doxygen_mangle_name(name):
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



def preprocess_xml(dir):
	global _inline_namespaces
	global _implementation_headers

	pretty_print_xml = False

	xml_parser = etree.XMLParser(
		encoding='utf-8',
		remove_blank_text=pretty_print_xml,
		recover=True,
		remove_comments=True,
		ns_clean=True
	)
	write_xml_to_file = lambda x, f: x.write(str(f), encoding='utf-8', xml_declaration=True, pretty_print=pretty_print_xml)

	inline_namespace_ids = None
	if _inline_namespaces:
		inline_namespace_ids = [f'namespace{doxygen_mangle_name(ns)}' for ns in _inline_namespaces]

	implementation_header_data = None
	implementation_header_mappings = None
	implementation_header_innernamespaces = None
	implementation_header_sectiondefs = None
	if _implementation_headers:
		implementation_header_data = [
			(
				hp,
				os.path.basename(hp),
				doxygen_mangle_name(os.path.basename(hp)),
				[(i, os.path.basename(i), doxygen_mangle_name(os.path.basename(i))) for i in impl]
			)
			for hp, impl in _implementation_headers
		]
		implementation_header_mappings = dict()
		implementation_header_innernamespaces = dict()
		implementation_header_sectiondefs = dict()
		for hdata in implementation_header_data:
			implementation_header_innernamespaces[hdata[2]] = []
			implementation_header_sectiondefs[hdata[2]] = []
			for (ip, ifn, iid) in hdata[3]:
				implementation_header_mappings[iid] = hdata

	if 1:
		extracted_implementation = False
		xml_files = get_all_files(dir, any=('*.xml'))
		for xml_file in xml_files:
			print(f'Pre-processing {xml_file}')
			xml = etree.parse(str(xml_file), parser=xml_parser)
			
			root = xml.getroot().find('compounddef')
			if root is None:
				continue

			changed = False

			# merge user-defined sections with the same name
			if root.get("kind") in ("namespace", "class", "struct", "enum", "file"):
				sectiondefs = [s for s in root.findall('sectiondef') if s.get("kind") == "user-defined"]
				sections = dict()
				for section in sectiondefs:
					header = section.find('header')
					if header is not None and header.text:
						if header.text not in sections:
							sections[header.text] = []
					sections[header.text].append(section)
				for key, vals in sections.items():
					if len(vals) > 1:
						first_section = vals.pop(0)
						for section in vals:
							for member in section.findall('memberdef'):
								section.remove(member)
								first_section.append(member)
							root.remove(section)
							changed = True

			# namespaces
			if root.get("kind") == "namespace" and _inline_namespaces:
				for nsid in inline_namespace_ids:
					if root.get("id") == nsid:
						root.set("inline", "yes")
						changed = True
						break

			# dirs
			if root.get("kind") == "dir" and _implementation_headers:
				innerfiles = root.findall('innerfile')
				for innerfile in innerfiles:
					if innerfile.get('refid') in implementation_header_mappings:
						root.remove(innerfile)
						changed = True

			# header files
			if root.get("kind") == "file" and _implementation_headers:
				# remove junk not required by m.css
				for tag in ('includes', 'includedby', 'incdepgraph', 'invincdepgraph'):
					tags = root.findall(tag)
					if tags:
						for t in tags:
							root.remove(t)
							changed = True

				# rip the good bits out of implementation headers
				if root.get("id") in implementation_header_mappings:
					hid = implementation_header_mappings[root.get("id")][2]
					innernamespaces = root.findall('innernamespace')
					if innernamespaces:
						implementation_header_innernamespaces[hid] = implementation_header_innernamespaces[hid] + innernamespaces
						extracted_implementation = True
						for tag in innernamespaces:
							root.remove(tag)
							changed = True
					sectiondefs = root.findall('sectiondef')
					if sectiondefs:
						implementation_header_sectiondefs[hid] = implementation_header_sectiondefs[hid] + sectiondefs
						extracted_implementation = True
						for tag in sectiondefs:
							root.remove(tag)
							changed = True

			if changed:
				write_xml_to_file(xml, xml_file)

		# merge extracted implementations
		if extracted_implementation:
			for (hp, hfn, hid, impl) in implementation_header_data:
				xml_file = os.path.join(dir, f'{hid}.xml')
				print(f'Merging implementation nodes into {xml_file}')
				xml = etree.parse(xml_file, parser=xml_parser)
				root = xml.getroot().find('compounddef')
				changed = False

				innernamespaces = root.findall('innernamespace')
				for new_tag in implementation_header_innernamespaces[hid]:
					matched = False
					for existing_tag in innernamespaces:
						if existing_tag.get('refid') == new_tag.get('refid'):
							matched = True
							break
					if not matched:
						root.append(new_tag)
						innernamespaces.append(new_tag)
						changed = True

				sectiondefs = root.findall('sectiondef')
				for new_section in implementation_header_sectiondefs[hid]:
					matched_section = False
					for existing_section in sectiondefs:
						if existing_section.get('kind') == new_section.get('kind'):
							matched_section = True

							memberdefs = existing_section.findall('memberdef')
							new_memberdefs = new_section.findall('memberdef')
							for new_memberdef in new_memberdefs:
								matched = False
								for existing_memberdef in memberdefs:
									if existing_memberdef.get('id') == new_memberdef.get('id'):
										matched = True
										break

								if not matched:
									new_section.remove(new_memberdef)
									existing_section.append(new_memberdef)
									memberdefs.append(new_memberdef)
									changed = True
							break

					if not matched_section:
						root.append(new_section)
						sectiondefs.append(new_section)
						changed = True

				if changed:
					write_xml_to_file(xml, xml_file)

	# delete the impl header xml files
	if 1 and _implementation_headers:
		for hdata in implementation_header_data:
			for (ip, ifn, iid) in hdata[3]:
				xml_file = os.path.join(dir, f'{iid}.xml')
				if (os.path.exists(xml_file)):
					print(f'Deleting {xml_file}')
					os.remove(xml_file)

	# scan through the files and substitute impl header ids and paths as appropriate
	if 1 and _implementation_headers:
		xml_files = get_all_files(dir, any=('*.xml'))
		for xml_file in xml_files:
			print(f"Re-linking implementation headers in '{xml_file}'")
			xml_text = read_all_text_from_file(xml_file)
			for (hp, hfn, hid, impl) in implementation_header_data:
				for (ip, ifn, iid) in impl:
					#xml_text = xml_text.replace(f'refid="{iid}"',f'refid="{hid}"')
					xml_text = xml_text.replace(f'compoundref="{iid}"',f'compoundref="{hid}"')
					xml_text = xml_text.replace(ip,hp)
			with BytesIO(bytes(xml_text, 'utf-8')) as b:
				xml = etree.parse(b, parser=xml_parser)
				write_xml_to_file(xml, xml_file)



def main():
	global _thread_error
	global _verbose
	global _namespaces
	global _inline_namespaces
	global _types
	global _macros
	global _string_literals
	global _external_links
	global _implementation_headers
	global _badges
	
	args = ArgumentParser(description='Generate fancy C++ documentation.')
	args.add_argument('config', type=Path, nargs='?', default=Path('./dox.toml'))
	args.add_argument('--verbose', '-v', action='store_true')
	args.add_argument('--threads', type=int, nargs='?', default=os.cpu_count())
	args.add_argument('--nocleanup', action='store_true')
	args = args.parse_args()
	_verbose = args.verbose
	vprint(" ".join(sys.argv))
	vprint(args)

	# get + check paths
	config_path = args.config.resolve()
	config_dir = config_path.parent
	xml_dir = Path(config_dir, 'xml')
	html_dir = Path(config_dir, 'html')
	mcss_dir = Path(this_script_dir(), 'external/mcss')
	assert_existing_file(config_path)
	assert_existing_file(Path(config_dir, 'Doxyfile'))
	assert_existing_file(Path(config_dir, 'Doxyfile-mcss'))
	assert_existing_directory(mcss_dir)
	assert_existing_file(Path(mcss_dir, 'documentation/doxygen.py'))
	
	# read config
	config = pytomlpp.loads(read_all_text_from_file(config_path))
	if 'namespaces' in config:
		_namespaces = tuple([ns for ns in _namespaces] + [str(ns) for ns in config['namespaces']])
		del config['namespaces']
	if 'inline_namespaces' in config:
		_inline_namespaces = tuple([str(ns) for ns in config['inline_namespaces']])
		del config['inline_namespaces']
	if 'types' in config:
		_types = tuple([t for t in _types] + [str(t) for t in config['types']])
		del config['types']
	if 'macros' in config:
		_macros = tuple([m for m in _macros] + [str(m) for m in config['macros']])
		del config['macros']
	if 'string_literals' in config:
		_string_literals = tuple([l for l in _string_literals] + [str(l) for l in config['string_literals']])
		del config['string_literals']
	if 'external_links' in config:
		_external_links = tuple([l for l in _external_links] + [(ext[0], ext[1]) for ext in config['external_links']])
		del config['external_links']
	if 'badges' in config:
		_badges = tuple([tuple(b) for b in config['badges']])
		del config['badges']
	if 'implementation_headers' in config:
		_implementation_headers = tuple([tuple(h) for h in config['implementation_headers']])
		del config['implementation_headers']
	for k, v in config.items():
		print(rf'WARNING: Unknown top-level config property {k}')
	
	# delete any leftovers from the previous run
	if 1:
		delete_directory(xml_dir)
		delete_directory(html_dir)

	# run doxygen to generate the xml
	if 1:
		subprocess.run(
			['doxygen', 'Doxyfile'],
			check=True,
			shell=True,
			cwd=str(config_dir)
		)

	# fix some shit that's broken in the xml
	if 1:
		preprocess_xml(xml_dir)

	# run doxygen.py (m.css) to generate the html
	if 1:
		doxy_args = [
			str(Path(config_dir, 'Doxyfile-mcss')),
			'--no-doxygen'
		]
		if _verbose:
			doxy_args.append('--debug')
		run_python_script(
			Path(mcss_dir, 'documentation/doxygen.py'),
			*doxy_args,
			cwd=config_dir
		)
		
	# copy additional files
	if 1:
		copy_file(Path(mcss_dir, 'css/m-dark+documentation.compiled.css'), Path(html_dir, 'm-dark+documentation.compiled.css'))
		copy_file(Path(this_script_dir(), 'dox.css'), Path(html_dir, 'dox.css'))
		copy_file(Path(this_script_dir(), 'github-icon.png'), Path(html_dir, 'github-icon.png'))

	# delete the xml
	if not args.nocleanup:
		delete_directory(xml_dir)

	# post-process html files
	if 1:
		fixes = [
			DeadLinksFix()
			, CustomTagsFix()
			, CodeBlockFix()
			, IndexPageFix()
			, ModifiersFix1()
			, ModifiersFix2()
			, ExtDocLinksFix()
			, LinksFix()
			, TemplateTemplateFix()
		]
		files = [os.path.split(str(f)) for f in get_all_files(html_dir, any=('*.html', '*.htm'))]
		if files:
			with futures.ThreadPoolExecutor(max_workers=max(1, min(64, args.threads))) as executor:
				jobs = { executor.submit(postprocess_file, dir, file, fixes) : file for dir, file in files }
				for job in futures.as_completed(jobs):
					if _thread_error:
						executor.shutdown(False)
						break
					else:
						file = jobs[job]
						print(f'Finished processing {file}.')
			if _thread_error:
				return 1


if __name__ == '__main__':
	try:
		result = main()
		if result is None:
			sys.exit(0)
		else:
			sys.exit(int(result))
	except Exception as err:
		print(
			'Fatal error: [{}] {}'.format(
				type(err).__name__,
				str(err)
			),
			file=sys.stderr
		)
		traceback.print_exc(file=sys.stderr)
		sys.exit(-1)