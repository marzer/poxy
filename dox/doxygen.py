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
from io import StringIO

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

def extract_value(doxyfile_text, key):
	m = re.search(rf'^\s*{key}\s*=\s*(.+?)\s*$', doxyfile_text, flags=re.M)
	while m:
		n = re.search(rf'^\s*{key}\s*=\s*(.+?)\s*$', doxyfile_text[m.end():], flags=re.M)
		if n:
			m = n
	if m:
		return m[1].strip(' "')
	return None

#=======================================================================================================================
# Doxyfile
#=======================================================================================================================

class Doxyfile(object):

	__include = re.compile(r'^\s*@INCLUDE\s*=\s*(.+?)\s*$', re.M)

	__aliases = (
		(r'cpp', r'@code{.cpp}'),
		(r'ecpp', r'@endcode'),
		(r'out', r'@code{.shell-session}'),
		(r'eout', r'@endcode'),
		(r'bash', r'@code{.sh}'),
		(r'ebash', r'@endcode'),
		(r'detail', r'@details'),
		(r'inline_subheading{1}', r'[h4]\1[/h4] ^^'),
		(r'conditional_return{1}', r'<strong><em>\1:</em></strong> ^^'),
		(r'inline_note', r'[set_class m-note m-info]'),
		(r'inline_warning', r'[set_class m-note m-danger]'),
		(r'inline_attention', r'[set_class m-note m-warning]'),
		(r'inline_remark', r'[set_class m-note m-default]'),
		(r'github{1}', r'<a href=\"https://github.com/\1\" target=\"_blank\">\1</a>'),
		(r'github{2}', r'<a href=\"https://github.com/\1\" target=\"_blank\">\2</a>'),
		(r'godbolt{1}', r'<a href=\"https://godbolt.org/z/\1\" target=\"_blank\">Try this code on Compiler Explorer</a>'),
		(r'flags_enum', r'@note This enum is a flags type; it is equipped with a full complement of bitwise operators. ^^'),
		(r'implementers', r'@par [parent_set_class m-block m-dim][emoji hammer][entity nbsp]Implementers: '),
		(r'optional', r'@par [parent_set_class m-block m-info]Optional field ^^'),
		(r'required', r'@par [parent_set_class m-block m-warning][emoji warning][entity nbsp]Required field ^^'),
		(r'availability', r'@par [parent_set_class m-block m-special]Conditional availability ^^'),
		(r'figure{1}', r'@image html \1'),
		(r'figure{2}', r'@image html \1 \"\2\"'),
		(r'm_div{1}', r'@xmlonly<mcss:div xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:class=\"\1\">@endxmlonly'),
		(r'm_enddiv', r'@xmlonly</mcss:div>@endxmlonly'),
		(r'm_span{1}', r'@xmlonly<mcss:span xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:class=\"\1\">@endxmlonly'),
		(r'm_endspan', r'@xmlonly</mcss:span>@endxmlonly'),
		(r'm_class{1}', r'@xmlonly<mcss:class xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:class=\"\1\" />@endxmlonly'),
		(r'm_footernavigation', r'@xmlonly<mcss:footernavigation xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" />@endxmlonly'),
		(r'm_examplenavigation{2}', r'@xmlonly<mcss:examplenavigation xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:page=\"\1\" mcss:prefix=\"\2\" />@endxmlonly'),
		(r'm_keywords{1}', r'@xmlonly<mcss:search xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:keywords=\"\1\" />@endxmlonly'),
		(r'm_keyword{3}', r'@xmlonly<mcss:search xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:keyword=\"\1\" mcss:title=\"\2\" mcss:suffix-length=\"\3\" />@endxmlonly'),
		(r'm_enum_values_as_keywords', r'@xmlonly<mcss:search xmlns:mcss=\"http://mcss.mosra.cz/doxygen/\" mcss:enum-values-as-keywords=\"true\" />@endxmlonly')
	)

	__default_overrides = (
		(r'CLASS_DIAGRAMS',			r'NO'),
		(r'DOXYFILE_ENCODING',		r'UTF-8'),
		(r'GENERATE_AUTOGEN_DEF',	r'NO'),
		(r'GENERATE_BUGLIST',		r'NO'),
		(r'GENERATE_CHI',			r'NO'),
		(r'GENERATE_DEPRECATEDLIST',r'NO'),
		(r'GENERATE_DOCBOOK',		r'NO'),
		(r'GENERATE_DOCSET',		r'NO'),
		(r'GENERATE_ECLIPSEHELP',	r'NO'),
		(r'GENERATE_HTML',			r'NO'),
		(r'GENERATE_HTMLHELP',		r'NO'),
		(r'GENERATE_LATEX',			r'NO'),
		(r'GENERATE_LEGEND',		r'NO'),
		(r'GENERATE_MAN',			r'NO'),
		(r'GENERATE_PERLMOD',		r'NO'),
		(r'GENERATE_QHP',			r'NO'),
		(r'GENERATE_RTF',			r'NO'),
		(r'GENERATE_TESTLIST',		r'NO'),
		(r'GENERATE_TODOLIST',		r'NO'),
		(r'GENERATE_TREEVIEW',		r'NO'),
		(r'GENERATE_XML',			r'YES'),
		(r'HIDE_UNDOC_MEMBERS',		r'YES'),
		(r'HIDE_UNDOC_CLASSES',		r'YES'),
		(r'HTML_OUTPUT',			r'html'),
		(r'INLINE_INHERITED_MEMB',	r'YES'),
		(r'INPUT_ENCODING',			r'UTF-8'),
		(r'OPTIMIZE_FOR_FORTRAN',	r'NO'),
		(r'OPTIMIZE_OUTPUT_FOR_C',	r'NO'),
		(r'OPTIMIZE_OUTPUT_JAVA',	r'NO'),
		(r'OPTIMIZE_OUTPUT_SLICE',	r'NO'),
		(r'OPTIMIZE_OUTPUT_VHDL',	r'NO'),
		(r'SORT_BRIEF_DOCS',		r'NO'),
		(r'SORT_BY_SCOPE_NAME',		r'YES'),
		(r'SORT_GROUP_NAMES',		r'YES'),
		(r'SORT_MEMBER_DOCS',		r'NO'),
		(r'SORT_MEMBERS_CTORS_1ST',	r'YES'),
		(r'SOURCE_BROWSER',			r'NO'),
		(r'TAB_SIZE',				r'4'),
		(r'TYPEDEF_HIDES_STRUCT',	r'NO'),
		(r'XML_NS_MEMB_FILE_SCOPE',	r'YES'),
		(r'XML_OUTPUT',				r'xml'),
		(r'XML_PROGRAMLISTING',		r'NO')
	)

	def __verbose(self, *args, file=sys.stdout, end='\n', sep=' '):
		if self.__context:
			self.__context.verbose(*args, file=file, end=end, sep=sep)

	def __init__(self, path, context=None, temp=False, temp_file_name=None):
		self.__context = context

		cwd = context.cwd if context is None else Path.cwd()
		self.__verbose(rf'Doxyfile.cwd:           {cwd}')

		assert path is not None
		if not isinstance(path, Path):
			path = Path(path)
		if not path.is_absolute():
			path = Path(cwd, path)
		path = path.resolve()

		# read in file
		text = ''
		if path.exists():
			if not path.is_file():
				raise Exception(f'{path} was not a file')
			text = read_all_text_from_file(path).strip()
		else:
			result = subprocess.run(
				r'doxygen -s -g -'.split(),
				check=True,
				capture_output=True,
				cwd=cwd,
				encoding='utf-8'
			)
			text = result.stdout.strip()

		# expand includes
		m = self.__include.search(text)
		while m:
			inc = m[1].strip(' "')
			sub = ''
			if inc:
				inc = Path(inc)
				if not inc.is_absolute():
					inc = Path(cwd, inc)
				inc = inc.resolve()
				sub = f'\n\n{read_all_text_from_file(inc).strip()}\n\n'
			text = text[:m.start()].strip() + sub + text[m.end():].strip()
			m = self.__include.search(text)

		# append overrides
		with StringIO(initial_value=text,newline='\n') as buf:
			buf.seek(0, 2)
			write = lambda s='',end='\n': print(s, file=buf,end=end)
			write('\n')
			write(r'##==========================================================================')
			write(r'## marzer/dox')
			write(r'##==========================================================================')
			if context:
				if context.name:
					write(rf'PROJECT_NAME           = "{context.name}"')
				else:
					context.name = extract_value(text, 'PROJECT_NAME')
				if context.description:
					write(rf'PROJECT_BRIEF          = "{context.description}"')
				else:
					context.name = extract_value(text, 'PROJECT_BRIEF')
			if context and context.generate_tagfile is not None:
				if context.generate_tagfile:
					if context.name:
						write(rf'GENERATE_TAGFILE       = {context.name.replace(" ","_")}.tag')
					else:
						write(rf'GENERATE_TAGFILE       = tagfile.tag')
				else:
					write(rf'GENERATE_TAGFILE       =')
			write( r'LOOKUP_CACHE_SIZE      = 2')
			write(rf'NUM_PROC_THREADS       = {context.threads}')
			write(rf'OUTPUT_DIRECTORY       = "."')
			write(rf'CLANG_OPTIONS         += -std=c++{context.cpp%100}')
			write(rf'CLANG_OPTIONS         += -Wno-everything')
			for k, v in self.__default_overrides:
				write(rf'{k:<23}= {v}')
			if context.show_includes is not None:
				write(rf'SHOW_INCLUDE_FILES     = {"YES" if context.show_includes else "NO"}')
			if context and context.tagfiles:
				write()
				for k, v in context.tagfiles.items():
					write(rf'TAGFILES              += "{k}={v}"')
			write()
			for k, v in self.__aliases:
				write(rf'ALIASES               += "{k}={v}"')
			write()
			for k, v in context.defines:
				write(rf'PREDEFINED            += "{k}={v}"')
			if text.find('M_LINKS_NAVBAR1') == -1:
				write()
				write(r'##! M_LINKS_NAVBAR1            = ''\\')
				write(r'##!     files ''\\')
				write(r'##!     namespaces')
			if text.find('M_LINKS_NAVBAR2') == -1:
				write()
				write(r'##! M_LINKS_NAVBAR2            = ''\\')
				write(r'##!     annotated ', end='')
				if context and context.github:
					write('\\')
					write(rf'##!     "<a target=\"_blank\" href=\"{context.github}\" class=\"github\">Github</a>"')
				else:
					write()
			if text.find('M_CLASS_TREE_EXPAND_LEVELS') == -1:
				write()
				write(r'##! M_CLASS_TREE_EXPAND_LEVELS = 3')
			if text.find('M_FILE_TREE_EXPAND_LEVELS') == -1:
				write()
				write(r'##! M_FILE_TREE_EXPAND_LEVELS  = 3')
			if text.find('M_SEARCH_DOWNLOAD_BINARY') == -1:
				write()
				write(r'##! M_SEARCH_DOWNLOAD_BINARY   = NO')
			if text.find('M_HTML_HEADER') == -1:
				write()
				write(r'##! M_HTML_HEADER              = ''\\')
				if context and context.description:
					write(rf'##!    <meta name="description" content="{context.description:}"> ''\\')
				write(r'##!    <link href="dox.css" rel="stylesheet"/>')
			if text.find('M_PAGE_FINE_PRINT') == -1:
				write()
				write(r'##! M_PAGE_FINE_PRINT          = ''\\')
				if context and context.github:
					write(rf'##!     <a href="https://github.com/{context.github}/">Github</a> &bull; ''\\')
					write(rf'##!     <a href="https://github.com/{context.github}/issues">Report an issue</a> ''\\')
					write(r'##!     <br><br> ''\\')
				write(r'##!     Documentation created using ''\\')
				write(r'##!     <a href="https://www.doxygen.nl/index.html">Doxygen</a> ''\\')
				write(r'##!     + <a href="https://mcss.mosra.cz/documentation/doxygen/">mosra/m.css</a> ''\\')
				write(r'##!     + <a href="https://github.com/marzer/dox/">marzer/dox</a>')
			self.__text = buf.getvalue().strip() + '\n'

		# output file path
		if temp:
			if temp_file_name:
				self.path = Path(temp_file_name)
			else:
				self.path = Path(str(path) + rf'.{sha1(self.__text)}.temp')
		else:
			self.path = path
		self.__verbose(rf'Doxyfile.path:          {self.path}')

	def flush(self):
		print(rf'Writing {self.path}')
		with open(self.path, 'w', encoding='utf-8', newline='\n') as f:
			f.write(self.__text)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if traceback is None:
			self.flush()
