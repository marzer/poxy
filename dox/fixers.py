#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

try:
	from dox.utils import *
	import dox.soup as soup
except:
	from utils import *
	import soup

import html

#=======================================================================================================================
# custom tags
#=======================================================================================================================

class CustomTagsFix(object):
	'''
	Modifies HTML using custom square-bracket [tags].
	'''
	__double_tags = re.compile(r"\[\s*(span|div|aside|code|pre|h1|h2|h3|h4|h5|h6|em|strong|b|i|u|li|ul|ol)(.*?)\s*\](.*?)\[\s*/\1\s*\]", re.I | re.S)
	__single_tags = re.compile(r"\[\s*(/?(?:span|div|aside|code|pre|emoji|(?:parent_)?set_name|(?:parent_)?(?:add|remove|set)_class|br|li|ul|ol|(?:html)?entity))(\s+[^\]]+?)?\s*\]", re.I | re.S)
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
			for base in (16, 10):
				try:
					cp = int(tag_content, base)
					if cp in context.emoji_codepoints:
						return f'&#x{cp:X};&#xFE0F;'
				except:
					pass
			if tag_content in context.emoji:
				cp = context.emoji[tag_content][0]
				return f'&#x{cp:X};&#xFE0F;'
			return ''
		elif tag_name in ('add_class', 'remove_class', 'set_class', 'parent_add_class', 'parent_remove_class', 'parent_set_class'):
			classes = []
			if tag_content:
				for s in tag_content.split():
					if s:
						classes.append(s)
			if classes:
				out.append((tag_name, classes))
			return ''
		elif tag_name in ('set_name', 'parent_set_name'):
			if tag_content:
				out.append((tag_name, tag_content))
			return ''
		else:
			return f'<{m[1]}{(" " + tag_content) if tag_content else ""}>'

	def __call__(self, doc, context):
		changed = False
		changed_this_pass = True
		while changed_this_pass:
			changed_this_pass = False
			for name in self.__allowed_parents:
				tags = doc.article_content.find_all(name)
				for tag in tags:
					if tag.decomposed or len(tag.contents) == 0 or soup.find_parent(tag, 'a', doc.article_content) is not None:
						continue
					replacer = RegexReplacer(self.__double_tags, lambda m, out: self.__double_tags_substitute(m, out, context), str(tag))
					if replacer:
						changed_this_pass = True
						soup.replace_tag(tag, str(replacer))
						continue
					replacer = RegexReplacer(self.__single_tags, lambda m, out: self.__single_tags_substitute(m, out, context), str(tag))
					if replacer:
						changed_this_pass = True
						parent = tag.parent
						new_tags = soup.replace_tag(tag, str(replacer))
						for i in range(len(replacer)):
							if replacer[i][0].startswith('parent_'):
								if parent is None:
									continue
								if replacer[i][0] == 'parent_add_class':
									soup.add_class(parent, replacer[i][1])
								elif replacer[i][0] == 'parent_remove_class':
									soup.remove_class(parent, replacer[i][1])
								elif replacer[i][0] == 'parent_set_class':
									soup.set_class(parent, replacer[i][1])
								elif replacer[i][0] == 'parent_set_name':
									parent.name = replacer[i][1]
							elif len(new_tags) == 1 and not isinstance(new_tags[0], soup.NavigableString):
								if replacer[i][0] == 'add_class':
									soup.add_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == 'remove_class':
									soup.remove_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == 'set_class':
									soup.set_class(new_tags[0], replacer[i][1])
								elif replacer[i][0] == 'set_name':
									new_tags[0].name = replacer[i][1]

						continue
			if changed_this_pass:
				doc.smooth()
				changed = True
		return changed

#=======================================================================================================================
# C++
#=======================================================================================================================

class _ModifiersFixBase(object):
	'''
	Base type for modifier parsing fixers.
	'''
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

class ModifiersFix1(_ModifiersFixBase):
	'''
	Fixes improperly-parsed modifiers on function signatures in the various 'detail view' sections.
	'''
	__expression = re.compile(rf'(\s+)({_ModifiersFixBase._modifierRegex})(\s+)')
	__sections = ('pub-static-methods', 'pub-methods', 'friends', 'func-members')

	@classmethod
	def __substitute(cls, m, out):
		return f'{m[1]}<span class="dox-injected m-label m-flat {cls._modifierClasses[m[2]]}">{m[2]}</span>{m[3]}'

	def __call__(self, doc, context):
		changed = False
		for sect in self.__sections:
			tags = doc.find_all_from_sections('dt', select='span.m-doc-wrap', section=sect)
			for tag in tags:
				replacer = RegexReplacer(self.__expression, self.__substitute, str(tag))
				if (replacer):
					changed = True
					soup.replace_tag(tag, str(replacer))
		return changed

class ModifiersFix2(_ModifiersFixBase):
	'''
	Fixes improperly-parsed modifiers on function signatures in the 'Function documentation' section.
	'''
	__expression = re.compile(rf'\s+({_ModifiersFixBase._modifierRegex})\s+')

	@classmethod
	def __substitute(cls, m, matches):
		matches.append(m[1])
		return ' '

	def __call__(self, doc, context):
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
					soup.replace_tag(bumper, bumperContent)
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

class TemplateTemplateFix(object):
	'''
	Spreads consecutive template <> declarations out over multiple lines.
	'''
	__expression = re.compile(r'(template&lt;.+?&gt;)\s+(template&lt;)', re.S)

	@classmethod
	def __substitute(cls, m):
		return f'{m[1]}<br>\n{m[2]}'

	def __call__(self, doc, context):
		changed = False
		for template in doc.body('div', class_='m-doc-template'):
			replacer = RegexReplacer(self.__expression, lambda m, out: self.__substitute(m), str(template))
			if replacer:
				soup.replace_tag(template, str(replacer))
				changed = True
		return changed

#=======================================================================================================================
# index.html
#=======================================================================================================================

class IndexPageFix(object):
	'''
	Applies some basic fixes to index.html
	'''
	def __call__(self, doc, context):
		if doc.path.name.lower() != 'index.html':
			return False
		parent = doc.article_content
		banner = parent.find('img')
		if banner:
			banner = banner.extract()
			parent.find('h1').replace_with(banner)
			if context.badges:
				parent = doc.new_tag('div', class_='gh-badges', after=banner)
				for (alt, src, href) in context.badges:
					if alt is None and src is None and href is None:
						doc.new_tag('br', parent=parent)
					else:
						anchor = doc.new_tag('a', parent=parent, href=href, target='_blank')
						doc.new_tag('img', parent=anchor, src=src, alt=alt)
				soup.add_class(banner, 'main_page_banner')
			return True
		return False

#=======================================================================================================================
# <code> blocks
#=======================================================================================================================

class CodeBlockFix(object):
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

	@classmethod
	def __colourize_compound_def(cls, tags, context):
		assert tags
		assert tags[0].string != '::'
		assert len(tags) == 1 or tags[-1].string != '::'
		full_str = ''.join([tag.get_text() for tag in tags])

		if context.highlighting.enums.fullmatch(full_str):
			soup.set_class(tags[-1], 'ne')
			del tags[-1]
			while tags and tags[-1].string == '::':
				del tags[-1]
			if tags:
				cls.__colourize_compound_def(tags, context)
			return True

		if context.highlighting.types.fullmatch(full_str):
			soup.set_class(tags[-1], 'ut')
			del tags[-1]
			while tags and tags[-1].string == '::':
				del tags[-1]
			if tags:
				cls.__colourize_compound_def(tags, context)
			return True

		while not context.highlighting.namespaces.fullmatch(full_str):
			del tags[-1]
			while tags and tags[-1].string == '::':
				del tags[-1]
			if not tags:
				break
			full_str = ''.join([tag.get_text() for tag in tags])

		if tags:
			while len(tags) > 1:
				tags.pop().decompose()
			tags[0].string = full_str
			if soup.remove_class(tags[0], ('n', 'nl', 'kt')):
				soup.add_class(tags[0], 'ns')
			return True

		return False

	def __call__(self, doc, context):
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
						string = string + tag.get_text()
					mlc_open.string = string
					soup.set_class(mlc_open, 'cm')
					while len(tags) > 1:
						soup.destroy_node(tags.pop())

					mlc_open = next_open

				# collect all names and glom them all together as compound names
				spans = code_block('span', class_=('n', 'nl', 'kt'), string=True)
				compound_names = []
				compound_name_evaluated_tags = set()
				for i in range(0, len(spans)):

					current = spans[i]
					if current in compound_name_evaluated_tags:
						continue

					compound_name_evaluated_tags.add(current)
					tags = [ current ]
					while True:
						prev = current.previous_sibling
						if (prev is None
							or prev.string is None
							or isinstance(prev, soup.NavigableString)
							or 'class' not in prev.attrs
							or prev['class'][0] not in ('n', 'nl', 'kt', 'o')
							or not self.__ns_token_expr.fullmatch(prev.string)):
							break
						current = prev
						tags.insert(0, current)
						compound_name_evaluated_tags.add(current)

					current = spans[i]
					while True:
						nxt = current.next_sibling
						if (nxt is None
							or nxt.string is None
							or isinstance(nxt, soup.NavigableString)
							or 'class' not in nxt.attrs
							or nxt['class'][0] not in ('n', 'nl', 'kt', 'o')
							or not self.__ns_token_expr.fullmatch(nxt.string)):
							break
						current = nxt
						tags.append(current)
						compound_name_evaluated_tags.add(current)

					full_str = ''.join([tag.get_text() for tag in tags])
					if self.__ns_full_expr.fullmatch(full_str):
						while tags and tags[0].string == '::':
							del tags[0]
						while tags and tags[-1].string == '::':
							del tags[-1]
						if tags:
							compound_names.append(tags)

				# types and namespaces
				for tags in compound_names:
					if self.__colourize_compound_def(tags, context):
						changed_this_block = True

				# string and numeric literals
				spans = code_block('span', class_='n', string=True)
				for span in spans:
					prev = span.previous_sibling
					if (prev is None
						or isinstance(prev, soup.NavigableString)
						or 'class' not in prev.attrs):
						continue
					if ('s' in prev['class'] and context.highlighting.string_literals.fullmatch(span.get_text())):
						soup.set_class(span, 'sa')
						changed_this_block = True
					elif (prev['class'][0] in ('mf', 'mi', 'mb', 'mh') and context.highlighting.numeric_literals.fullmatch(span.get_text())):
						soup.set_class(span, prev['class'][0])
						changed_this_block = True

				# preprocessor macros
				spans = code_block('span', class_=('n', 'nl', 'kt', 'nc', 'nf'), string=True)
				for span in spans:
					if context.highlighting.macros.fullmatch(span.get_text()):
						soup.set_class(span, 'm')
						changed_this_block = True

				# misidentifed keywords
				spans = code_block('span', class_=('nf', 'nb', 'kt', 'ut', 'kr'), string=True)
				for span in spans:
					if (span.string in self.__keywords):
						span['class'] = 'k'
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
					soup.destroy_node(parent)

			changed = changed or changed_this_pass

		return changed

#=======================================================================================================================
# <a> tags
#=======================================================================================================================

def _m_doc_anchor_tags(tag):
	return (tag.name == 'a'
		and tag.has_attr('class')
		and ('m-doc' in tag['class'] or 'm-doc-self' in tag['class'])
		and (tag.string is not None or tag.strings is not None)
	)

class AutoDocLinksFix(object):
	'''
	Adds links to additional sources where appropriate.
	'''
	__allowedNames = ('dd', 'p', 'dt', 'h3', 'td', 'div', 'figcaption')

	@classmethod
	def __substitute(cls, m, uri):
		external = uri.startswith('http')
		return rf'''<a href="{uri}" class="m-doc dox-injected{' dox-external' if external else ''}"{' target="_blank"' if external else ''}>{m[0]}</a>'''

	def __call__(self, doc, context):
		changed = False

		# first check all existing doc links to make sure they aren't erroneously linked to the wrong thing
		if 1:
			existing_doc_links = doc.article_content.find_all(_m_doc_anchor_tags)
			for link in existing_doc_links:
				done = False
				s = link.get_text()
				for expr, uri in context.autolinks:
					if ((not link.has_attr('href') or link['href'] != uri) and expr.fullmatch(s)):
						link['href'] = uri
						soup.set_class(link, ['m-doc', 'dox-injected'])
						if uri.startswith('http'):
							soup.add_class(link, 'dox-external')
						done = True
						changed = True
						break
				if done:
					continue

		# now search the document for any other potential links
		if 1:
			tags = soup.shallow_search(doc.article_content, self.__allowedNames, lambda t: soup.find_parent(t, 'a', doc.article_content) is None)
			strings = []
			for tag in tags:
				strings = strings + soup.string_descendants(tag, lambda t: soup.find_parent(t, 'a', tag) is None)
			for expr, uri in context.autolinks:
				i = 0
				while i < len(strings):
					string = strings[i]
					parent = string.parent
					replacer = RegexReplacer(expr, lambda m, out: self.__substitute(m, uri), html.escape(str(string), quote=False))
					if replacer:
						repl_str = str(replacer)
						begins_with_ws = len(repl_str) > 0 and repl_str[:1].isspace()
						new_tags = soup.replace_tag(string, repl_str)
						if (begins_with_ws and new_tags[0].string is not None and not new_tags[0].string[:1].isspace()):
							new_tags[0].insert_before(' ')
						changed = True
						del strings[i]
						for tag in new_tags:
							strings = strings + soup.string_descendants(tag, lambda t: soup.find_parent(t, 'a', parent) is None)
						continue
					i = i + 1
		return changed

class LinksFix(object):
	'''
	Fixes various minor issues with anchor tags.
	'''
	__external_href = re.compile(r'^(?:https?|s?ftp|mailto)[:].+$', re.I)
	__internal_doc_id = re.compile(r'^[a-fA-F0-9]+$')
	__internal_doc_id_href = re.compile(r'^#([a-fA-F0-9]+)$')
	__godbolt = re.compile(r'^\s*https[:]//godbolt.org/z/.+?$', re.I)

	def __call__(self, doc, context):
		changed = False
		for anchor in doc.body('a', recursive=True):
			if 'href' not in anchor.attrs:
				continue

			# make sure links to certain external sources are correctly marked as such
			if self.__external_href.fullmatch(anchor['href']) is not None:
				if 'target' not in anchor.attrs or anchor['target'] != '_blank':
					anchor['target'] = '_blank'
					changed = True
				changed = soup.add_class(anchor, 'dox-external') or changed

				# do magic with godbolt.org links
				if self.__godbolt.fullmatch(anchor['href']):
					changed = soup.add_class(anchor, 'godbolt') or changed
					if anchor.parent.name == 'p' and len(anchor.parent.contents) == 1:
						changed = soup.add_class(anchor.parent, ('m-note', 'm-success', 'godbolt')) or changed
						if anchor.parent.next_sibling is not None and anchor.parent.next_sibling.name == 'pre':
							code_block = anchor.parent.next_sibling
							code_block.insert(0, anchor.parent.extract())
				continue

			# make sure internal documentation links actually have somewhere to go
			if 'class' in anchor.attrs and 'm-doc' in anchor['class']:
				m = self.__internal_doc_id_href.fullmatch(anchor['href'])
				if m is not None and doc.body.find(id=m[1], recursive=True) is None:
					soup.remove_class(anchor, 'm-doc')
					soup.add_class(anchor, 'm-doc-self')
					anchor['href'] = '#'
					parent_with_id = anchor.find_parent(id=True)
					while parent_with_id is not None:
						if self.__internal_doc_id.fullmatch(parent_with_id['id']) is not None:
							anchor['href'] = '#' + parent_with_id['id']
							break
						parent_with_id = parent_with_id.find_parent(id=True)

		return changed

class DeadLinksFix(object):
	'''
	Fixes dead links to non-existent local files.
	'''
	__href = re.compile(r'^([-_a-zA-Z0-9]+\.html?)(?:#(.*))?$')

	def __call__(self, doc, context):
		changed = False
		for anchor in doc.body('a', recursive=True):
			match = self.__href.fullmatch(anchor['href'])
			if match and not Path(doc.path.parent, match[1]).exists():
				soup.remove_class(anchor, 'm-doc')
				if anchor.parent is not None and anchor.parent.name in ('dt', 'div'):
					soup.add_class(anchor, 'm-doc-self')
					id = None
					if 'id' in anchor.parent.attrs:
						id = anchor.parent['id']
					else:
						id = match[2]
						if not id:
							id = f'{sha1(match[1], anchor.string)}'
						anchor.parent['id'] = id
					anchor['href'] = f'#{id}'
				changed = True
		return changed

