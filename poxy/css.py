#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions for working with CSS files.
"""

import re
import requests
from .utils import *
from typing import Tuple

RX_COMMENT = re.compile(r'''/[*].+?[*]/''', flags=re.DOTALL)
RX_IMPORT = re.compile(r'''@import\s+url\(\s*['"]?(.+?)['"]?\s*\)\s*;''')
RX_MCSS_FILE = re.compile(r'(?:m|pygments)-[a-zA-Z0-9_-]+[.]css')
RX_MCSS_THEME = re.compile(r'm-theme-([a-zA-Z0-9_-]+)[.]css')
RX_GOOGLE_FONT = re.compile(r'''url\(\s*['"]?(https://fonts[.]gstatic[.]com/[a-zA-Z0-9_/%+?:-]+?[.]woff2)['"]?\s*\)''')



def strip_comments(text) -> str:
	global RX_COMMENT
	return RX_COMMENT.sub('', text)



def strip_quotes(text):
	if text.startswith(r'"') or text.startswith(r"'"):
		text = text[1:]
	if text.endswith(r'"') or text.endswith(r"'"):
		text = text[:-2]
	return text



def resolve_imports(text, cwd=None, mcss_dir=None) -> Tuple[str, bool]:
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

		import_path = strip_quotes(m[1].strip())
		path = None
		path_ok = lambda: path is not None and path.exists() and path.is_file()

		# download + cache uris locally
		if is_uri(import_path):
			find_generated_dir().mkdir(exist_ok=True)
			path = Path(find_generated_dir(), rf'{sha1(import_path.lower())}.css')
			if not path_ok():
				print(rf"Downloading {import_path}")
				headers = {
					r'User-Agent': r'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0'
				}
				response = requests.get(import_path, headers=headers, timeout=10)
				with open(path, 'w', encoding='utf-8', newline='\n') as f:
					f.write(response.text)

		# m-css stylesheets get special handling;
		# - first we check for any identically-named versions in poxy's data dir
		# - then check the m-css css dir
		had_mcss_filename = False
		was_mcss_file = False
		if not path_ok() is None and RX_MCSS_FILE.fullmatch(import_path):
			path = Path(find_data_dir(), import_path)
			if not path_ok():
				path = Path(mcss_dir, r'css', import_path)
				was_mcss_file = True
			had_mcss_filename = True

		# otherwise just check cwd
		if not path_ok():
			path = Path(cwd, import_path)
			was_mcss_file = False

		# if we still haven't found a match just leave the @import statement as it was
		if not path_ok():
			return m[0]

		text = strip_comments(read_all_text_from_file(path, logger=True)).strip()
		header = rf'/*==== {import_path} {"="*(110-len(import_path))}*/'
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



def resolve_google_fonts(text) -> str:

	def match_handler(m):
		global RX_GOOGLE_FONT
		uri = strip_quotes(m[1].strip())
		file_name = uri[uri.rfind('/') + 1:]
		fonts_dir = Path(find_generated_dir(), 'fonts')
		fonts_dir.mkdir(exist_ok=True)
		path = Path(fonts_dir, rf'{file_name}')
		if not path.exists():
			print(rf"Downloading {uri}")
			headers = {
				r'User-Agent': r'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0'
			}
			response = requests.get(uri, headers=headers, timeout=10)
			with open(path, 'wb') as f:
				f.write(response.content)

		return rf"url('fonts/{file_name}')"

	global RX_GOOGLE_FONT
	return RX_GOOGLE_FONT.sub(match_handler, text)



def minify(text) -> str:
	text = text.replace('\t', ' ')
	text = re.sub(r'\n[ \t]*[{]', ' {\n', text)
	text = re.sub(r'[ \t]+\n', '\n', text)
	text = re.sub(r'\n\n+', '\n', text)

	pos = 0
	open_brackets = []
	while pos < len(text):
		if text[pos:pos + 2] == r'/*':
			pos += 2
			while pos < len(text) - 1:
				if text[pos:pos + 2] == r'*/':
					pos += 2
					break
				pos += 1
		else:
			if text[pos] == r'{':
				open_brackets.append(pos)
			elif text[pos] == r'}':
				if open_brackets:
					block_content = text[open_brackets[-1] + 1:pos].strip().replace('\n', ' ')
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
							text = text[:open_brackets[-1]] + new_block + text[pos + 1:]
							pos = open_brackets[-1] - 1 + len(new_block) - 1
					open_brackets.pop()
			pos += 1

	text = re.sub(r'[{]\s+?[}]', r'{}', text)
	text = re.sub(r'[ \t][ \t]+', ' ', text)
	return text



def regenerate_builtin_styles(mcss_dir=None):
	if mcss_dir is None:
		mcss_dir = find_mcss_dir()
	else:
		mcss_dir = coerce_path(mcss_dir).resolve()
		assert_existing_directory(mcss_dir)
		assert_existing_file(Path(mcss_dir, r'documentation/doxygen.py'))

	data_dir = find_data_dir()
	output_dir = find_generated_dir()
	output_dir.mkdir(exist_ok=True)

	THEMES = (Path(data_dir, 'poxy.css'), )
	for theme_source_file in THEMES:
		text = strip_comments(read_all_text_from_file(theme_source_file, logger=True))
		text, had_mcss_files = resolve_imports(text, theme_source_file.parent)
		text = resolve_google_fonts(text)
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
