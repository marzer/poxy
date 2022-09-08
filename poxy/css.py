#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

"""
Functions for working with CSS files.
"""

import re
from .utils import *
from typing import Tuple


RX_COMMENT = re.compile(r'''/[*].+?[*]/''', flags=re.DOTALL)
RX_IMPORT = re.compile(r'''@import\s+url\(\s*['"](.+?)['"]\s*\)\s*;''')
RX_MCSS_FILE = re.compile(r'(?:m|pygments)-[a-zA-Z0-9_-]+[.]css')
RX_MCSS_THEME = re.compile(r'm-theme-([a-zA-Z0-9_-]+)[.]css')



def strip_comments(text) -> str:
	global RX_COMMENT
	return RX_COMMENT.sub('', text)



def resolve_imports(text, cwd=None, mcss_dir = None) -> Tuple[str, bool]:
	if cwd is None:
		cwd = Path.cwd()
	cwd = coerce_path(cwd).resolve()
	assert_existing_directory(cwd)

	if mcss_dir is None:
		mcss_dir = find_mcss_dir()
	else:
		mcss_dir = coerce_path(mcss_dir).resolve()
		assert_existing_directory(mcss_dir)
		assert_existing_file(Path(mcss_dir, r'documentation/doxygen.py'))

	had_mcss_files = False
	def match_handler(m):
		global RX_MCSS_THEME
		global RX_MCSS_FILE
		nonlocal cwd
		nonlocal mcss_dir
		nonlocal had_mcss_files

		# skip uris altogether for now (todo: cache them? unroll google fonts?)
		if is_uri(m[1]):
			return m[0]

		path = None

		# m-css stylesheets get special handling;
		# - first we check for any identically-named versions in poxy's data dir
		# - then check the m-css css dir
		had_mcss_filename = False
		was_mcss_file = False
		if RX_MCSS_FILE.fullmatch(m[1]):
			path = Path(find_data_dir(), m[1])
			if not path.exists() or not path.is_file():
				path = Path(mcss_dir, 'css', m[1])
				was_mcss_file = True
			had_mcss_filename = True

		# otherwise just check cwd
		if path is None or not path.exists() or not path.is_file():
			path = Path(cwd, m[1])
			was_mcss_file = False

		# if we still haven't found a match just leave the @import statement as it was
		if not path.exists() or not path.is_file():
			return m[0]

		text = strip_comments(read_all_text_from_file(path, logger=True)).strip()
		header = rf'/*==== {m[1]} {"="*(110-len(m[1]))}*/'
		text = f'\n\n{header}\n{text}\n\n'

		# more m.css special-handling
		if was_mcss_file:
			had_mcss_files = True
		if had_mcss_filename:
			# replace the :root node in the m.css theme bases with the poxy equivalent
			theme = RX_MCSS_THEME.fullmatch(path.name)
			if theme:
				text = text.replace(r':root', rf'.poxy-theme-{theme[1]}')

		res = resolve_imports(text, cwd=path.parent)
		had_mcss_files = had_mcss_files or res[1]
		return res[0]

	global RX_IMPORT
	return (RX_IMPORT.sub(match_handler, text), had_mcss_files)



def minify(text) -> str:
	text = text.replace('\t', ' ')
	text = re.sub(r'\n[ \t]*[{]', ' {\n', text)
	text = re.sub(r'[ \t]+\n', '\n', text)
	text = re.sub(r'\n\n+', '\n', text)

	pos = 0
	open_brackets = []
	while pos < len(text):
		if text[pos:pos+2] == r'/*':
			pos += 2
			while pos < len(text)-1:
				if text[pos:pos+2] == r'*/':
					pos += 2
					break
				pos += 1
		else:
			if text[pos] == r'{':
				open_brackets.append(pos)
			elif text[pos] == r'}':
				if open_brackets:
					block_content = text[open_brackets[-1]+1:pos].strip().replace('\n', ' ')
					block_content = re.sub(r'[ \t][ \t]+', ' ', block_content)
					if r'{' not in block_content and r'}' not in block_content:
						semis = 0
						for c in block_content:
							if c == ';':
								semis += 1
							if semis >= 4:
								break
						if semis <= 4 and len(block_content) <= 100:
							new_block = rf'{{ {block_content} }}'
							text = text[:open_brackets[-1]] + new_block + text[pos+1:]
							pos = open_brackets[-1] - 1 + len(new_block) - 1
					open_brackets.pop()
			pos += 1

	text = re.sub(r'[{]\s+?[}]', r'{}', text)
	text = re.sub(r'[ \t][ \t]+', ' ', text)

	return text



def regenerate_builtin_styles(mcss_dir = None):
	if mcss_dir is None:
		mcss_dir = find_mcss_dir()
	else:
		mcss_dir = coerce_path(mcss_dir).resolve()
		assert_existing_directory(mcss_dir)
		assert_existing_file(Path(mcss_dir, r'documentation/doxygen.py'))

	data_dir = find_data_dir()
	output_dir = Path(data_dir, 'generated')
	output_dir.mkdir(exist_ok=True)

	THEMES = (
		Path(data_dir, 'poxy.css'),
	)
	for theme_source_file in THEMES:
		text = strip_comments(read_all_text_from_file(theme_source_file, logger=True))
		text, had_mcss_files = resolve_imports(text, theme_source_file.parent)
		text = re.sub(r':(before|after)', r'::\1', text)
		text = re.sub(r':::+(before|after)', r'::\1', text)
		text = text.replace('\r\n', '\n')
		text = text.replace('\r', '\n')
		text = minify(text)
		if had_mcss_files:
			mcss_license = read_all_text_from_file(Path(mcss_dir, 'COPYING'), logger=True).strip()
			text = rf'''/*
This file was automatically generated from multiple sources,
some of which included stylesheets from mosra/m.css.
The license for that project is as follows:

{mcss_license}
*/
{text}
'''
		theme_dest_file = Path(output_dir, theme_source_file.name)
		print(rf'Writing {theme_dest_file}')
		with open(theme_dest_file, r'w', encoding=r'utf-8', newline='\n') as f:
			f.write(text)


	pass
