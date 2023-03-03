#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
'Fixer' function objects used during various post-process steps.
"""

import html
from bs4 import NavigableString
from .utils import *
from .svg import SVG
from .project import Context
from . import soup
from trieregex import TrieRegEx

#=======================================================================================================================
# base classes
#=======================================================================================================================



class HTMLFixer(object):
	pass



class PlainTextFixer(object):
	pass



#=======================================================================================================================
# HTML post-processes
#=======================================================================================================================



class CustomTags(HTMLFixer):
	'''
	Modifies HTML using custom square-bracket [tags].
	'''
	__double_tags = re.compile(
		r'\[\s*(' + r'p|center|span|div|aside|code|pre|h1|h2|h3|h4|h5|h6|em|strong|b|i|u|li|ul|ol'
		+ r')(.*?)\s*\](.*?)\[\s*/\1\s*\]', re.I | re.S
	)
	__single_tags = re.compile(
		r'\[\s*(/?(?:' + r'p|img|span|div|aside|code|pre|emoji' + r'|(?:parent_)?set_(?:parent_)?(?:name|class)'
		+ r'|(?:parent_)?(?:add|remove)_(?:parent_)?class' + r'|br|li|ul|ol|(?:html)?entity)' + r')(\s+[^\]]+?)?\s*\]',
		re.I | re.S
	)
	__hex_entity = re.compile(r'(?:[0#]?[xX])?([a-fA-F0-9]+)')
	__allowed_parents = ('dd', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'aside', 'td')

	@classmethod
	def __double_tags_substitute(cls, m, out, context):
		return f'<{m[1]}{html.unescape(m[2])}>{m[3]}</{m[1]}>'

	@classmethod
	def __single_tags_substitute(cls, m, out, context):
		tag_name = m[1].lower()
		tag_content = m[2].strip() if m[2] else ''
		if tag_name == 'htmlentity' or tag_name == 'entity':
			if not tag_content:
				return ''
			hex_match = cls.__hex_entity.fullmatch(tag_content)
			if hex_match:
				try:
					cp = int(hex_match[1], 16)
					if cp <= 0x10FFFF:
						return f'&#x{hex_match[1]};'
				except:
					pass
			return f'&{tag_content};'
		elif tag_name == 'emoji':
			tag_content = tag_content.lower()
			if not tag_content:
				return ''
			emoji = None
			for base in (16, 10):
				try:
					emoji = context.emoji[int(tag_content, base)]
					if emoji is not None:
						break
				except:
					pass
			if emoji is None:
				emoji = context.emoji[tag_content]
			if emoji is not None:
				return str(emoji)
			return ''
		elif tag_name in (
			r'add_class', r'remove_class', r'set_class', r'parent_add_class', r'parent_remove_class',
			r'parent_set_class', r'add_parent_class', r'remove_parent_class', r'set_parent_class'
		):
			classes = []
			if tag_content:
				for s in tag_content.split():
					if s:
						classes.append(s)
			if classes:
				out.append((tag_name, classes))
			return ''
		elif tag_name in (r'set_name', r'parent_set_name', r'set_parent_name'):
			if tag_content:
				out.append((tag_name, tag_content))
			return ''
		else:
			return f'<{m[1]}{(" " + tag_content) if tag_content else ""}>'

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article_content is None:
			return False
		changed = False
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for name in self.__allowed_parents:
				tags = doc.article_content.find_all(name)
				for tag in tags:
					if tag.decomposed or len(tag.contents
												) == 0 or soup.find_parent(tag, 'a', doc.article_content) is not None:
						continue
					replacer = RegexReplacer(
						self.__double_tags, lambda m, out: self.__double_tags_substitute(m, out, context), str(tag)
					)
					if replacer:
						changed_this_pass = True
						soup.replace_tag(tag, str(replacer))
						continue
					replacer = RegexReplacer(
						self.__single_tags, lambda m, out: self.__single_tags_substitute(m, out, context), str(tag)
					)
					if replacer:
						changed_this_pass = True
						parent = tag.parent
						new_tags = soup.replace_tag(tag, str(replacer))
						for i in range(len(replacer)):
							if replacer[i][0].find(r'parent_') != -1:
								if parent is None:
									continue
								if replacer[i][0] in (r'parent_add_class', r'add_parent_class'):
									soup.add_class(parent, replacer[i][1])
								elif replacer[i][0] in (r'parent_remove_class', r'remove_parent_class'):
									soup.remove_class(parent, replacer[i][1])
								elif replacer[i][0] in (r'parent_set_class', r'set_parent_class'):
									soup.set_class(parent, replacer[i][1])
								elif replacer[i][0] in (r'parent_set_name', r'set_parent_name'):
									parent.name = replacer[i][1]
							elif len(new_tags) == 1 and not isinstance(new_tags[0], NavigableString):
								if replacer[i][0] == r'add_class':
									soup.add_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == r'remove_class':
									soup.remove_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == r'set_class':
									soup.set_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == r'set_name':
									new_tags[0].name = replacer[i][1]

						continue
			if changed_this_pass:
				doc.smooth()
				changed = True
		return changed



class _CPPModifiersBase(HTMLFixer):
	'''
	Base type for modifier parsing fixers.
	'''
	_modifierRegex = r"defaulted|noexcept|constexpr|(?:pure )?virtual|protected|__(?:(?:vector|std|fast)call|cdecl)"
	_modifierClasses = {
		"defaulted": "m-info",
		"noexcept": "m-success",
		"constexpr": "m-primary",
		"pure virtual": "m-warning",
		"virtual": "m-warning",
		"protected": "m-warning",
		"__vectorcall": "m-special",
		"__stdcall": "m-special",
		"__fastcall": "m-special",
		"__cdecl": "m-special"
	}



class CPPModifiers1(_CPPModifiersBase):
	'''
	Fixes improperly-parsed modifiers on function signatures in the various 'detail view' sections.
	'''
	__expression = re.compile(rf'(\s+)({_CPPModifiersBase._modifierRegex})(\s+)')
	__sections = ('pub-static-methods', 'pub-methods', 'friends', 'func-members')

	@classmethod
	def __substitute(cls, m, out):
		return f'{m[1]}<span class="poxy-injected m-label m-flat {cls._modifierClasses[m[2]]}">{m[2]}</span>{m[3]}'

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article_content is None:
			return False
		changed = False
		for sect in self.__sections:
			tags = doc.find_all_from_sections('dt', select='span.m-doc-wrap', section=sect)
			for tag in tags:
				replacer = RegexReplacer(self.__expression, self.__substitute, str(tag))
				if (replacer):
					changed = True
					soup.replace_tag(tag, str(replacer))
		return changed



class CPPModifiers2(_CPPModifiersBase):
	'''
	Fixes improperly-parsed modifiers on function signatures in the 'Function documentation' section.
	'''
	__expression = re.compile(rf'\s+({_CPPModifiersBase._modifierRegex})\s+')

	@classmethod
	def __substitute(cls, m, matches):
		matches.append(m[1])
		return ' '

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article_content is None:
			return False
		changed = False
		sections = doc.find_all_from_sections(section=False)  # all sections without an id
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
				end = end[len(end) - 1]
				matches = []
				bumperContent = self.__expression.sub(lambda m: self.__substitute(m, matches), str(bumper))
				if (matches):
					changed = True
					soup.replace_tag(bumper, bumperContent)
					lastInserted = end.find('span')
					for match in matches:
						lastInserted = doc.new_tag(
							'span',
							parent=end,
							string=match,
							class_=f'poxy-injected m-label {self._modifierClasses[match]}',
							before=lastInserted
						)
						lastInserted.insert_after(' ')
		return changed



class CPPTemplateTemplate(HTMLFixer):
	'''
	Spreads consecutive template <> declarations out over multiple lines.
	'''
	__expression = re.compile(r'(template&lt;.+?&gt;)\s+(template&lt;)', re.S)

	@classmethod
	def __substitute(cls, m):
		return f'{m[1]}<br>\n{m[2]}'

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		changed = False
		for template in doc.body('div', class_='m-doc-template'):
			replacer = RegexReplacer(self.__expression, lambda m, out: self.__substitute(m), str(template))
			if replacer:
				soup.replace_tag(template, str(replacer))
				changed = True
		return changed



class StripIncludes(HTMLFixer):
	'''
	Strips #include <paths/to/headers.h> based on context.sources.strip_includes.
	'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article is None or not context.sources.strip_includes:
			return False
		changed = False
		for include_div in doc.article.find_all(r'div', class_=r'm-doc-include'):
			anchor = include_div.find('a', href=True, class_=r'cpf')
			if anchor is None:
				continue
			text = anchor.get_text()
			if not (text.startswith('<') and text.endswith('>')):
				continue
			text = text[1:-1].strip()
			for strip in context.sources.strip_includes:
				if len(text) < len(strip) or not text.startswith(strip):
					continue
				if len(text) == len(strip):
					soup.destroy_node(include_div)
				else:
					anchor.contents.clear()
					anchor.contents.append(NavigableString(rf'<{text[len(strip):]}>'))
				changed = True
				break
		return changed



class Banner(HTMLFixer):
	'''
	Makes the first image on index.html a 'banner'
	'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article_content is None or path.name.lower() != 'index.html':
			return False
		parent = doc.article_content

		h1 = parent.find('h1', recursive=False)
		banner = parent.find('img', recursive=False)
		if not banner or not h1 or r'src' not in banner.attrs or not banner[r'src']:
			return False

		# ensure it's the first image in the page, before any subsections or headings
		for sibling_tag in ('section', 'h2', 'h3', 'h4', 'h5', 'h6'):
			sibling = banner.find_previous_sibling(sibling_tag)
			if sibling is not None:
				return False

		banner = banner.extract()
		h1.replace_with(banner)
		banner[r'id'] = r'poxy-main-banner'
		soup.add_class(doc.body, r'poxy-has-main-banner')

		if context.badges:
			soup.add_class(doc.body, r'poxy-has-badges')
			span_size = 0
			span_size = 2 if not span_size and (len(context.badges) % 2) == 0 else span_size
			span_size = 3 if not span_size and (len(context.badges) % 3) == 0 else span_size
			span_size = 2 if not span_size else span_size
			idx = 0
			span = None
			parent = doc.new_tag(r'div', id=r'poxy-badges', after=banner)
			for (alt, src, href) in context.badges:
				if span is None or (idx % span_size) == 0:
					span = doc.new_tag(r'span', parent=parent)
				img_parent = span
				if href:
					img_parent = doc.new_tag(r'a', parent=span, href=href, target=r'_blank')
				img = doc.new_tag(r'img', parent=img_parent, src=src)
				if alt:
					img[r'alt'] = alt
				idx += 1
		return True



class CodeBlocks(HTMLFixer):
	'''
	Fixes various issues and improves syntax highlighting in <code> blocks.
	'''
	__keywords = (
		r'alignas',
		r'alignof',
		r'bool',
		r'char',
		r'char16_t',
		r'char32_t',
		r'char8_t',
		r'class',
		r'const',
		r'consteval',
		r'constexpr',
		r'constinit',
		r'do',
		r'double',
		r'else',
		r'explicit',
		r'false',
		r'float',
		r'if',
		r'inline',
		r'int',
		r'long',
		r'mutable',
		r'noexcept',
		r'short',
		r'signed',
		r'sizeof',
		r'struct',
		r'template',
		r'true',
		r'typename',
		r'unsigned',
		r'void',
		r'wchar_t',
		r'while',
	)

	__ns_token_expr = re.compile(r'(?:::|[a-zA-Z_][a-zA-Z_0-9]*|::[a-zA-Z_][a-zA-Z_0-9]*|[a-zA-Z_][a-zA-Z_0-9]*::)')
	__ns_full_expr = re.compile(r'(?:::)?[a-zA-Z_][a-zA-Z_0-9]*(::[a-zA-Z_][a-zA-Z_0-9]*)*(?:::)?')
	__compound_starter_classes = ( # must not contain: fm, o, p, nc, mi, nf, nn
		r'n', r'no', r'nl', r'ne', r'nx', r'kt', r'kr', r'nb'
	)
	__compound_classes = (*__compound_starter_classes, r'mi', r'nf', r'nc', r'nn')  # must not contain:  fm, o, p
	__func_name = re.compile(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*$')
	__func_bracket = re.compile(r'^\s*[(]')

	@classmethod
	def __colourize_compound_def(cls, tags, context) -> bool:
		assert tags
		assert tags[0].string != '::'
		assert len(tags) == 1 or tags[-1].string != '::'
		full_str = ''.join([tag.get_text() for tag in tags])

		def colourize_case(c: str) -> bool:
			nonlocal cls
			nonlocal tags
			changed = False
			if soup.get_classes(tags[-1]) != [c]:
				soup.set_class(tags[-1], c)
				changed = True
			del tags[-1]
			while tags and tags[-1].string == r'::':
				del tags[-1]
			if tags:
				changed = cls.__colourize_compound_def(tags, context) or changed
			return changed

		if context.code_blocks.enums.fullmatch(full_str):
			return colourize_case(r'mi')  # Literal.Number.Integer

		if context.code_blocks.functions.fullmatch(full_str):
			return colourize_case(r'nf')  # Name.Function

		if context.code_blocks.types.fullmatch(full_str):
			return colourize_case(r'nc')  # Name.Class

		while not context.code_blocks.namespaces.fullmatch(full_str):
			del tags[-1]
			while tags and tags[-1].string == r'::':
				del tags[-1]
			if not tags:
				break
			full_str = ''.join([tag.get_text() for tag in tags])

		if tags:
			changed = False
			while len(tags) > 1:
				tags.pop(-1).decompose()
				changed = True
			changed = changed or tags[-1].string != full_str
			tags[-1].string = full_str
			if soup.get_classes(tags[-1]) != [r'nn']:  # Name.Namespace
				soup.set_class(tags[-1], r'nn')
				return True
			return changed

		return False

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		changed = False

		# fix up syntax highlighting
		code_blocks = doc.body(('pre', 'code'), class_='m-code')
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
						string = string + tag.get_text()
					mlc_open.string = string
					soup.set_class(mlc_open, 'cm')
					while len(tags) > 1:
						soup.destroy_node(tags.pop())

					mlc_open = next_open

				# macros
				spans = code_block(r'span', class_=self.__compound_classes, string=True)
				for span in spans:
					if context.code_blocks.macros.fullmatch(span.get_text()):
						soup.set_class(span, r'fm')  # Name.Function.Magic
						changed_this_block = True

				if 1:
					# collect all names and glom them all together as compound names
					spans = code_block(r'span', class_=self.__compound_starter_classes, string=True)
					compound_names = []
					compound_name_evaluated_tags = set()
					for i in range(0, len(spans)):

						current = spans[i]
						if id(current) in compound_name_evaluated_tags:
							continue

						compound_name_evaluated_tags.add(id(current))
						tags = [current]
						while True:
							prev = current.previous_sibling
							if (
								prev is None or prev.string is None or isinstance(prev, NavigableString)
								or not soup.has_any_classes(prev, *self.__compound_classes, r'o', r'p')
								or not self.__ns_token_expr.fullmatch(prev.string)
							):
								break
							current = prev
							tags.insert(0, current)
							compound_name_evaluated_tags.add(id(current))

						current = spans[i]
						while True:
							nxt = current.next_sibling
							if (
								nxt is None or nxt.string is None or isinstance(nxt, NavigableString)
								or not soup.has_any_classes(nxt, *self.__compound_classes, r'o', r'p')
								or not self.__ns_token_expr.fullmatch(nxt.string)
							):
								break
							current = nxt
							tags.append(current)
							compound_name_evaluated_tags.add(id(current))

						full_str = ''.join([tag.get_text() for tag in tags])
						if self.__ns_full_expr.fullmatch(full_str):
							while tags and tags[0].string == '::':
								del tags[0]
							while tags and tags[-1].string == '::':
								del tags[-1]
							if tags:
								compound_names.append(tags)

					# types, namespaces, enums, free functions
					for tags in compound_names:
						if self.__colourize_compound_def(tags, context):
							changed_this_block = True

				# functions:
				if 1:
					spans = code_block(r'span', class_=(r'n', r'nc'), string=True)
					for func in spans:
						if not self.__func_name.fullmatch(func.string):
							continue
						bracket = func.next_sibling
						if (
							bracket is None  #
							or isinstance(bracket, NavigableString)  #
							or r'p' not in soup.get_classes(bracket)  #
							or not self.__func_bracket.search(bracket.string)
						):
							continue
						soup.set_class(func, r'nf')
						changed_this_block = True

				# keywords
				spans = code_block(r'span', class_=self.__compound_classes, string=True)
				for span in spans:
					if (span.string in self.__keywords):
						soup.set_class(span, r'k')  # Keyword
						changed_this_block = True

				if changed_this_block:
					code_block.smooth()
					changed_this_pass = True
			changed = changed or changed_this_pass

		# fix doxygen butchering code blocks as inline nonsense
		code_blocks = doc.body('code', class_=('m-code', 'm-console'))
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for code_block in code_blocks:
				parent = code_block.parent
				if (
					parent is None or parent.name != r'p' or parent.parent is None
					or parent.parent.name not in (r'div', r'section')
				):
					continue
				changed_this_pass = True
				code_block.name = 'pre'
				parent.insert_before(code_block.extract())
				parent.smooth()
				if (not parent.contents or (len(parent.contents) == 1 and parent.contents[0].string.strip() == '')):
					soup.destroy_node(parent)
			changed = changed or changed_this_pass

		return changed



class AutoDocLinks(HTMLFixer):
	'''
	Adds links to additional sources where appropriate.
	'''
	__allowedNames = ('dd', 'p', 'dt', 'h3', 'td', 'div', 'figcaption')

	@classmethod
	def __substitute(cls, m, uri):
		external = uri.startswith('http')
		return rf'''<a href="{uri}" class="m-doc poxy-injected{' poxy-external' if external else ''}"{' target="_blank"' if external else ''}>{m[0]}</a>'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.article_content is None:
			return False

		changed = False

		# first check all existing doc links to make sure they aren't erroneously linked to the wrong thing
		if 1:

			def m_doc_anchor_tags(tag):
				return (
					tag.name == 'a' and tag.has_attr('class')
					and ('m-doc' in tag['class'])  # or 'm-doc-self' in tag['class'])
					and (tag.string is not None or tag.strings is not None)
				)

			existing_doc_links = doc.article_content.find_all(m_doc_anchor_tags)
			for link in existing_doc_links:
				done = False
				s = link.get_text()
				for expr, uri in context.autolinks:
					# check that it's a match for the replacement expression
					if not expr.fullmatch(s):
						continue
					# check the existing href against the target first
					if link.has_attr('href'):
						href = str(link['href'])
						anchor = href.rfind('#')
						if anchor == 0:
							continue  # don't override internal self-links
						if anchor != -1:
							href = href[:anchor]
						if href == uri or href == path.name:  # don't override internal self-links
							continue
					link['href'] = uri
					soup.set_class(link, ['m-doc', 'poxy-injected'])
					if uri.startswith('http'):
						soup.add_class(link, 'poxy-external')
					done = True
					changed = True
					break
				if done:
					continue

		# now search the document for any other potential links
		if 1:
			tags = soup.shallow_search(
				doc.article_content, self.__allowedNames,
				lambda t: soup.find_parent(t, 'a', doc.article_content) is None
			)
			strings = []
			for tag in tags:
				strings = strings + soup.string_descendants(tag, lambda t: soup.find_parent(t, 'a', tag) is None)
			strings = [s for s in strings if s.parent is not None]
			for expr, uri in context.autolinks:
				if uri == path.name:  # don't create unnecessary self-links
					continue
				i = 0
				while i < len(strings):
					string = strings[i]
					parent = string.parent
					replacer = RegexReplacer(
						expr, lambda m, out: self.__substitute(m, uri), html.escape(str(string), quote=False)
					)
					if replacer:
						repl_str = str(replacer)
						begins_with_ws = len(repl_str) > 0 and repl_str[:1].isspace()
						new_tags = soup.replace_tag(string, repl_str)
						if (begins_with_ws and new_tags[0].string is not None and not new_tags[0].string[:1].isspace()):
							new_tags[0].insert_before(' ')
						changed = True
						del strings[i]
						for tag in new_tags:
							strings = strings + soup.string_descendants(
								tag, lambda t: soup.find_parent(t, 'a', parent) is None
							)
						continue
					i = i + 1
		return changed



class Links(HTMLFixer):
	'''
	Fixes various minor issues with anchor tags.
	'''
	__external_href = re.compile(r'^(?:https?|s?ftp|mailto)[:].+$', re.I)
	__internal_doc_id = re.compile(r'^[a-fA-F0-9]+$')
	__godbolt = re.compile(r'^\s*https[:]//godbolt.org/z/.+?$', re.I)
	__local_href = re.compile(r'^([-/_a-zA-Z0-9]+\.[a-zA-Z]+)(?:#(.*))?$')

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		changed = False
		for anchor in doc.body('a', href=True):
			href = anchor['href']

			# make sure links to external sources are correctly marked as such
			if self.__external_href.fullmatch(href) is not None:
				if 'target' not in anchor.attrs or anchor['target'] != '_blank':
					anchor['target'] = '_blank'
					changed = True
				changed = soup.add_class(anchor, 'poxy-external') or changed

				# do magic with godbolt.org links
				if self.__godbolt.fullmatch(href):
					changed = soup.add_class(anchor, 'godbolt') or changed
					if (
						anchor.parent.name == 'p' and len(anchor.parent.contents) == 1
						and anchor.parent.next_sibling is not None and anchor.parent.next_sibling.name == 'pre'
					):
						soup.add_class(anchor.parent, ('m-note', 'm-success', 'godbolt'))
						code_block = anchor.parent.next_sibling
						code_block.insert(0, anchor.parent.extract())
						changed = True
				continue

			is_mdoc = r'class' in anchor.attrs and (r'm-doc' in anchor['class'] or r'm-doc-self' in anchor['class'])

			# make sure links to local files point to actual existing files
			match = self.__local_href.fullmatch(href)
			if match and not coerce_path(path.parent, match[1]).exists():
				changed = True
				if is_mdoc:
					href = r'#'
					anchor[r'href'] = r'#'  # will by fixed by the next step
				else:
					for attr in (
						r'download', r'href', r'hreflang', r'media', r'ping', r'referrerpolicy', r'rel', r'target',
						r'type'
					):
						if attr in anchor.attrs:
							del anchor[attr]
					anchor.name = r'span'
					continue

			# make sure internal documentation #id links actually have somewhere to go
			if (is_mdoc and href.startswith(r'#') and (len(href) == 1 or doc.body.find(id=href[1:]) is None)):
				changed = True
				soup.remove_class(anchor, 'm-doc')
				soup.add_class(anchor, 'm-doc-self')
				anchor['href'] = '#'
				parent_with_id = anchor.find_parent(id=self.__internal_doc_id)
				if parent_with_id is None:
					parent_with_id = anchor.find_parent((r'dt', r'tr'), id=False)
					if parent_with_id is not None:
						parent_with_id['id'] = sha256(parent_with_id.get_text())
				if parent_with_id is None:
					parent_with_id = anchor.find_parent(id=True)
				if parent_with_id is not None:
					anchor['href'] = '#' + parent_with_id['id']
				continue

		return changed



class EmptyTags(HTMLFixer):
	'''
	Prunes the tree of various empty tags (happens as a side-effect of some other operations).
	'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		changed = False
		for tag in doc.body((r'p', r'span')):
			if not tag.contents or (
				len(tag.contents) == 1 and isinstance(tag.contents[0], NavigableString) and not tag.string
			):
				soup.destroy_node(tag)
				changed = True
		return changed



class MarkTOC(HTMLFixer):
	'''
	Marks any table-of-contents with a custom class.
	'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		if doc.table_of_contents is None:
			return False
		soup.add_class(doc.table_of_contents, r'poxy-toc')
		doc.table_of_contents['id'] = r'poxy-toc'
		soup.add_class(doc.body, r'poxy-has-toc')
		return True



class InjectSVGs(HTMLFixer):
	'''
	Injects the contents of SVG <img> tags directly into the document.
	'''

	def __call__(self, context: Context, doc: soup.HTMLDocument, path: Path):
		imgs = doc.body.find_all(r'img')
		if not imgs:
			return False
		imgs = [
			i for i in imgs
			if r'src' in i.attrs and i[r'src'] and not is_uri(i[r'src']) and i[r'src'].lower().endswith(r'.svg')
		]
		count = 0
		for img in imgs:
			src = Path(path.parent, img[r'src'])
			if not src.exists() or not src.is_file() or src.stat().st_size > (1024 * 16):  # max 16 kb
				continue
			svg = SVG(
				src,  #
				logger=context.verbose_logger,
				root_id=img[r'id'] if r'id' in img.attrs else rf'poxy-injected-svg-{count}',
				root_classes=(*soup.get_classes(img), r'poxy-injected-svg')
			)
			img = soup.replace_tag(img, str(svg))[0]
			count += 1
		return count > 0



#=======================================================================================================================
# plain text post-processes
#=======================================================================================================================



class ImplementationDetails(PlainTextFixer):
	'''
	Replaces implementation details with appropriate shorthands.
	'''
	__shorthands = ((r'POXY_IMPLEMENTATION_DETAIL_IMPL', r'<code class="m-note m-dim poxy-impl">/* ... */</code>'), )

	def __call__(self, context: Context, text: str, path: Path) -> str:
		for shorthand, replacement in self.__shorthands:
			idx = text.find(shorthand)
			while idx >= 0:
				text = text[:idx] + replacement + text[idx + len(shorthand):]
				idx = text.find(shorthand)
		return text



class MarkdownPages(PlainTextFixer):
	'''
	Cleans up some HTML snafus from markdown-based pages.
	'''

	def __call__(self, context: Context, text: str, path: Path) -> str:
		if path.name.lower().startswith(r'md_') or path.name.lower().startswith(r'm_d__'):
			WBR = r'(?:<wbr[ \t]*/?>)?'
			PREFIX = rf'_{WBR}_{WBR}poxy_{WBR}thiswasan_{WBR}'
			text = re.sub(rf'{PREFIX}amp', r'&amp;', text)
			text = re.sub(rf'{PREFIX}at', r'@', text)
			text = re.sub(rf'{PREFIX}fe0f', r'&#xFE0F;', text)
		return text



BUILTIN_LITERALS = TrieRegEx()
for l in (r'l', r'L'):
	BUILTIN_LITERALS.add(l)  # long
	for l2 in (r'l', r'L'):
		BUILTIN_LITERALS.add(rf'{l}{l2}')  # long long
		for u in (r'u', r'U'):
			BUILTIN_LITERALS.add(rf'{u}{l}{l2}')  # unsigned long long
	for u in (r'u', r'U'):
		BUILTIN_LITERALS.add(rf'{u}{l}')  # unsigned long
for f in (r'f', r'F'):
	BUILTIN_LITERALS.add(f)  # float
for q in (r'q', r'Q'):
	BUILTIN_LITERALS.add(f)  # quad
# std::chrono
BUILTIN_LITERALS.add(r'd')
BUILTIN_LITERALS.add(r'h')
BUILTIN_LITERALS.add(r'min')
BUILTIN_LITERALS.add(r'ms')
BUILTIN_LITERALS.add(r'ns')
BUILTIN_LITERALS.add(r's')
BUILTIN_LITERALS.add(r'us')
BUILTIN_LITERALS.add(r'y')
# std::complex
BUILTIN_LITERALS.add(r'i')
BUILTIN_LITERALS.add(r'if')
BUILTIN_LITERALS.add(r'il')
# std::string(view)
BUILTIN_LITERALS.add(r's')
BUILTIN_LITERALS.add(r'sv')
BUILTIN_LITERALS = BUILTIN_LITERALS.regex()



class Pygments(PlainTextFixer):
	'''
	Fixes minor issues with pygments-generated markup.
	'''

	def __call__(self, context: Context, text: str, path: Path) -> str:
		if re.search(r'class="[^"]*?m-code[^"]*?"', text):

			# at some point pygments started adding markup to whitespace,
			# causing an awful lot of markup bloat. m.css does not style this markup
			# so we can safely strip it away.
			text = re.sub(r'<span class="w">(\s+)</span>', r'\1', text)

			# fix numeric UDLs being treated as a separate token
			text = re.sub(
				rf'<span\s+class="(m[bfhio])"\s*>(.*?)</span><span class="n">((?:_[a-zA-Z0-9_]*)|{BUILTIN_LITERALS})</span>',  #
				r'<span class="\1">\2\3</span>',
				text
			)

			# fix string UDLs being treated as a separate token
			text = re.sub(
				rf'<span\s+class="s"\s*>(.*?)</span><span class="n">((?:_[a-zA-Z0-9_]*)|{BUILTIN_LITERALS})</span>',  #
				r'<span class="s">\1\2</span>',
				text
			)

			# hack to make some basic #ifs, #defines etc. look nice
			text = re.sub(
				r'<span\s+class="cp"\s*>(\s*#\s*(?:(?:el)?if(?:n?def)?|define|undef)\s+)([a-zA-Z_][a-zA-Z_0-9]*?)([^a-zA-Z_0-9])',  #
				r'<span class="cp">\1</span><span class="fm">\2</span><span class="cp">\3',
				text
			)

		return text



class InstallSearchShim(PlainTextFixer):
	'''
	Installs our shim around m.css' showSearch().
	'''

	def __call__(self, context: Context, text: str, path: Path) -> str:
		return re.sub(
			r'<\s*script\s+src="search-v2[.]js"\s*>\s*</script>',
			r'<script src="search-v2.js"></script><script>install_mcss_search_shim();</script>',
			text,
			flags=re.DOTALL
		)
