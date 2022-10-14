#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
The 'actually do the thing' module.
"""

import os
import subprocess
import concurrent.futures as futures
import tempfile
from lxml import etree
from io import BytesIO, StringIO
from .utils import *
from .project import Context
from . import doxygen
from . import soup
from . import fixers
from . import graph
from .svg import SVG
from distutils.dir_util import copy_tree

#=======================================================================================================================
# HELPERS
#=======================================================================================================================



def make_temp_file():
	return tempfile.SpooledTemporaryFile(mode='w+', newline='\n', encoding='utf-8')



#=======================================================================================================================
# PRE/POST PROCESSORS
#=======================================================================================================================

DOXYGEN_DEFAULTS = (
	(r'ALLEXTERNALS', False),
	(r'ALLOW_UNICODE_NAMES', False),
	(r'ALWAYS_DETAILED_SEC', False),
	(r'AUTOLINK_SUPPORT', True),
	(r'BUILTIN_STL_SUPPORT', False),
	(r'CASE_SENSE_NAMES', False),
	(r'CLASS_DIAGRAMS', False),
	(r'CPP_CLI_SUPPORT', False),
	(r'CREATE_SUBDIRS', False),
	(r'DISTRIBUTE_GROUP_DOC', False),
	(r'DOXYFILE_ENCODING', r'UTF-8'),
	(r'DOT_FONTNAME', r'Source Sans Pro'),
	(r'DOT_FONTSIZE', 16),
	(r'ENABLE_PREPROCESSING', True),
	(r'EXAMPLE_RECURSIVE', False),
	(r'EXCLUDE_SYMLINKS', False),
	(r'EXPAND_ONLY_PREDEF', False),
	(r'EXTERNAL_GROUPS', False),
	(r'EXTERNAL_PAGES', False),
	(r'EXTRACT_ANON_NSPACES', False),
	(r'EXTRACT_LOCAL_CLASSES', False),
	(r'EXTRACT_LOCAL_METHODS', False),
	(r'EXTRACT_PACKAGE', False),
	(r'EXTRACT_PRIV_VIRTUAL', True),
	(r'EXTRACT_PRIVATE', False),
	(r'EXTRACT_STATIC', False),
	(r'FILTER_PATTERNS', None),
	(r'FILTER_SOURCE_FILES', False),
	(r'FILTER_SOURCE_PATTERNS', None),
	(r'FORCE_LOCAL_INCLUDES', False),
	(r'FULL_PATH_NAMES', True),
	(r'GENERATE_AUTOGEN_DEF', False),
	(r'GENERATE_BUGLIST', False),
	(r'GENERATE_CHI', False),
	(r'GENERATE_DEPRECATEDLIST', False),
	(r'GENERATE_DOCBOOK', False),
	(r'GENERATE_DOCSET', False),
	(r'GENERATE_ECLIPSEHELP', False),
	(r'GENERATE_HTML', False),
	(r'GENERATE_HTMLHELP', False),
	(r'GENERATE_LATEX', False),
	(r'GENERATE_LEGEND', False),
	(r'GENERATE_MAN', False),
	(r'GENERATE_PERLMOD', False),
	(r'GENERATE_QHP', False),
	(r'GENERATE_RTF', False),
	(r'GENERATE_SQLITE3', False),
	(r'GENERATE_TESTLIST', False),
	(r'GENERATE_TODOLIST', False),
	(r'GENERATE_TREEVIEW', False),
	(r'GENERATE_XML', True),
	(r'HAVE_DOT', False),
	(r'HIDE_COMPOUND_REFERENCE', False),
	(r'HIDE_FRIEND_COMPOUNDS', False),
	(r'HIDE_IN_BODY_DOCS', False),
	(r'HIDE_SCOPE_NAMES', False),
	(r'HIDE_UNDOC_CLASSES', True),
	(r'HIDE_UNDOC_MEMBERS', True),
	(r'HTML_EXTRA_STYLESHEET', None),
	(r'HTML_FILE_EXTENSION', r'.html'),
	(r'HTML_OUTPUT', r'html'),
	(r'IDL_PROPERTY_SUPPORT', False),
	(r'INHERIT_DOCS', True),
	(r'INLINE_GROUPED_CLASSES', False),
	(r'INLINE_INFO', True),
	(r'INLINE_INHERITED_MEMB', True),
	(r'INLINE_SIMPLE_STRUCTS', False),
	(r'INLINE_SOURCES', False),
	(r'INPUT_ENCODING', r'UTF-8'),
	(r'INPUT_FILTER', None),
	(r'LOOKUP_CACHE_SIZE', 2),
	(r'MACRO_EXPANSION', True),
	(r'MARKDOWN_SUPPORT', True),
	(r'OPTIMIZE_FOR_FORTRAN', False),
	(r'OPTIMIZE_OUTPUT_FOR_C', False),
	(r'OPTIMIZE_OUTPUT_JAVA', False),
	(r'OPTIMIZE_OUTPUT_SLICE', False),
	(r'OPTIMIZE_OUTPUT_VHDL', False),
	(r'PYTHON_DOCSTRING', True),
	(r'QUIET', False),
	(r'RECURSIVE', False),
	(r'REFERENCES_LINK_SOURCE', False),
	(r'RESOLVE_UNNAMED_PARAMS', True),
	(r'SEARCH_INCLUDES', False),
	(r'SEPARATE_MEMBER_PAGES', False),
	(r'SHORT_NAMES', False),
	(r'SHOW_GROUPED_MEMB_INC', False),
	(r'SHOW_USED_FILES', False),
	(r'SIP_SUPPORT', False),
	(r'SKIP_FUNCTION_MACROS', False),
	(r'SORT_BRIEF_DOCS', False),
	(r'SORT_BY_SCOPE_NAME', False),
	(r'SORT_GROUP_NAMES', True),
	(r'SORT_MEMBER_DOCS', False),
	(r'SORT_MEMBERS_CTORS_1ST', True),
	(r'SOURCE_BROWSER', False),
	(r'STRICT_PROTO_MATCHING', False),
	(r'STRIP_FROM_INC_PATH', None),  # we handle this
	(r'SUBGROUPING', True),
	(r'TAB_SIZE', 4),
	(r'TOC_INCLUDE_HEADINGS', 3),
	(r'TYPEDEF_HIDES_STRUCT', False),
	(r'UML_LOOK', False),
	(r'USE_HTAGS', False),
	(r'USE_MDFILE_AS_MAINPAGE', None),
	(r'VERBATIM_HEADERS', False),
	(r'WARN_AS_ERROR', False),  # we handle this
	(r'WARN_IF_DOC_ERROR', True),
	(r'WARN_IF_INCOMPLETE_DOC', True),
	(r'WARN_LOGFILE', None),
	(r'XML_NS_MEMB_FILE_SCOPE', True),
	(r'XML_PROGRAMLISTING', False),
)



def preprocess_doxyfile(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	with doxygen.Doxyfile(
		input_path=None, output_path=context.doxyfile_path, cwd=context.input_dir, logger=context.verbose_logger
	) as df:

		df.append()
		df.append(r'#---------------------------------------------------------------------------')
		df.append(r'# marzer/poxy')
		df.append(r'#---------------------------------------------------------------------------', end='\n\n')

		df.append(r'# doxygen defaults', end='\n\n')  # ----------------------------------------

		for k, v in DOXYGEN_DEFAULTS:
			df.set_value(k, v)

		df.append()
		df.append(r'# general config', end='\n\n')  # ---------------------------------------------------

		df.set_value(r'OUTPUT_DIRECTORY', context.output_dir)
		df.set_value(r'XML_OUTPUT', context.temp_xml_dir)
		df.set_value(r'PROJECT_NAME', context.name)
		df.set_value(r'PROJECT_BRIEF', context.description)
		df.set_value(r'PROJECT_LOGO', context.logo)
		df.set_value(r'SHOW_INCLUDE_FILES', context.show_includes)
		df.set_value(r'INTERNAL_DOCS', context.internal_docs)
		df.add_value(
			r'ENABLED_SECTIONS', (r'private', r'internal') if context.internal_docs else (r'public', r'external')
		)
		df.add_value(r'ENABLED_SECTIONS', r'poxy_supports_concepts')
		if context.xml_v2:
			df.set_value(r'INLINE_INHERITED_MEMB', False)

		if context.generate_tagfile:
			df.set_value(r'GENERATE_TAGFILE', context.tagfile_path)
		else:
			df.set_value(r'GENERATE_TAGFILE', None)

		df.set_value(r'NUM_PROC_THREADS', min(context.threads, 32))
		df.add_value(r'CLANG_OPTIONS', rf'-std=c++{context.cpp%100}')
		df.add_value(r'CLANG_OPTIONS', r'-Wno-everything')

		home_md_path = None
		for home_md in (r'HOME.md', r'home.md', r'INDEX.md', r'index.md', r'README.md', r'readme.md'):
			p = Path(context.input_dir, home_md)
			if p.exists() and p.is_file():
				home_md_path = p
				break
		if home_md_path is not None:
			home_md_temp_path = Path(context.temp_pages_dir, r'home.md')
			copy_file(home_md_path, home_md_temp_path, logger=context.verbose_logger)
			df.set_value(r'USE_MDFILE_AS_MAINPAGE', home_md_temp_path)

		df.append()
		df.append(r'# context.warnings', end='\n\n')  # ---------------------------------------------------

		df.set_value(r'WARNINGS', context.warnings.enabled)
		df.set_value(r'WARN_IF_UNDOCUMENTED', context.warnings.undocumented)

		df.append()
		df.append(r'# context.sources', end='\n\n')  # ----------------------------------------------------

		df.add_value(r'INPUT', context.sources.paths)
		df.set_value(r'FILE_PATTERNS', context.sources.patterns)
		df.add_value(r'EXCLUDE', context.html_dir)
		df.add_value(r'STRIP_FROM_PATH', context.sources.strip_paths)
		df.set_value(r'EXTRACT_ALL', context.sources.extract_all)

		df.append()
		df.append(r'# context.examples', end='\n\n')  # ----------------------------------------------------

		df.add_value(r'EXAMPLE_PATH', context.examples.paths)
		df.set_value(r'EXAMPLE_PATTERNS', context.examples.patterns)

		if context.images.paths:  # ----------------------------------------------------
			df.append()
			df.append(r'# context.images', end='\n\n')
			df.add_value(r'IMAGE_PATH', context.images.paths)

		if context.tagfiles:  # ----------------------------------------------------
			df.append()
			df.append(r'# context.tagfiles', end='\n\n')
			df.add_value(r'TAGFILES', [rf'{file}={dest}' for _, (file, dest) in context.tagfiles.items()])

		if context.aliases:  # ----------------------------------------------------
			df.append()
			df.append(r'# context.aliases', end='\n\n')
			df.add_value(r'ALIASES', [rf'{k}={v}' for k, v in context.aliases.items()])

		if context.macros:  # ----------------------------------------------------
			df.append()
			df.append(r'# context.macros', end='\n\n')
			df.add_value(r'PREDEFINED', [rf'{k}={v}' for k, v in context.macros.items()])

		df.cleanup()
		context.verbose(r'Doxyfile:')
		context.verbose(df.get_text(), indent=r'    ')



def preprocess_changelog(context: Context):
	assert context is not None
	assert isinstance(context, Context)
	if not context.changelog:
		return

	# make sure we're working with a temp copy, not the user's actual changelog
	# (the actual copying should already be done in the context's initialization)
	assert context.changelog.parent == context.temp_pages_dir
	assert_existing_file(context.changelog)

	text = read_all_text_from_file(context.changelog, logger=context.verbose_logger).strip()
	text = text.replace('\r\n', '\n')
	text = re.sub(r'\n<br[ \t]*/?><br[ \t]*/?>\n', r'', text)
	if context.repo:
		text = re.sub(r'#([0-9]+)', lambda m: rf'[#{m[1]}]({context.repo.make_issue_uri(m[1])})', text)
		text = re.sub(r'!([0-9]+)', lambda m: rf'[!{m[1]}]({context.repo.make_pull_request_uri(m[1])})', text)
		text = re.sub(r'@([a-zA-Z0-9_-]+)', lambda m: rf'[@{m[1]}]({context.repo.make_user_uri(m[1])})', text)
	text = text.replace(r'&amp;', r'__poxy_thiswasan_amp')
	text = text.replace(r'&#xFE0F;', r'__poxy_thiswasan_fe0f')
	text = text.replace(r'@', r'__poxy_thiswasan_at')
	text = f'\n{text}\n'
	text = re.sub('\n#[^#].+?\n', '\n', text)
	text = f'@page poxy_changelog Changelog\n\n@tableofcontents\n\n{text}'
	text = text.rstrip()
	text += '\n\n'
	context.verbose(rf'Writing {context.changelog}')
	with open(context.changelog, r'w', encoding=r'utf-8', newline='\n') as f:
		f.write(text)



def preprocess_tagfiles(context: Context):
	assert context is not None
	assert isinstance(context, Context)
	if not context.unresolved_tagfiles:
		return
	with ScopeTimer(r'Resolving remote tagfiles', print_start=True, print_end=context.verbose_logger) as t:
		for source, (file, _) in context.tagfiles.items():
			if file.exists() or not is_uri(source):
				continue
			context.verbose(rf'Downloading {source}')
			text = download_text(source, timeout=30)
			context.verbose(rf'Writing {file}')
			with open(file, 'w', encoding='utf-8', newline='\n') as f:
				f.write(text)



def postprocess_xml(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	xml_files = get_all_files(context.temp_xml_dir, any=(r'*.xml'))
	if not xml_files:
		return

	context.info(rf'Post-processing {len(xml_files) + len(context.tagfiles)} XML files...')

	pretty_print_xml = False
	xml_parser = etree.XMLParser(
		encoding='utf-8', remove_blank_text=pretty_print_xml, recover=True, remove_comments=True, ns_clean=True
	)
	write_xml_to_file = lambda xml, f: xml.write(
		str(f), encoding='utf-8', xml_declaration=True, pretty_print=pretty_print_xml
	)

	inline_namespace_ids = None
	if context.inline_namespaces:
		inline_namespace_ids = [f'namespace{doxygen.mangle_name(ns)}' for ns in context.inline_namespaces]

	implementation_header_data = None
	implementation_header_mappings = None
	implementation_header_innernamespaces = None
	implementation_header_sectiondefs = None
	implementation_header_unused_keys = None
	implementation_header_unused_values = None
	if context.implementation_headers:
		implementation_header_data = [(
			hp, os.path.basename(hp), doxygen.mangle_name(os.path.basename(hp)),
			[(i, os.path.basename(i), doxygen.mangle_name(os.path.basename(i))) for i in impl]
		) for hp, impl in context.implementation_headers]
		implementation_header_unused_keys = set()
		for hp, impl in context.implementation_headers:
			implementation_header_unused_keys.add(hp)
		implementation_header_unused_values = dict()
		for hdata in implementation_header_data:
			for (ip, ifn, iid) in hdata[3]:
				implementation_header_unused_values[iid] = (ip, hdata[0])
		implementation_header_mappings = dict()
		implementation_header_innernamespaces = dict()
		implementation_header_sectiondefs = dict()
		for hdata in implementation_header_data:
			implementation_header_innernamespaces[hdata[2]] = []
			implementation_header_sectiondefs[hdata[2]] = []
			for (ip, ifn, iid) in hdata[3]:
				implementation_header_mappings[iid] = hdata

	context.compound_pages = dict()
	context.compound_kinds = set()

	# process xml files
	if 1:

		# pre-pass to delete junk files
		if 1:
			# 'file' entries for markdown and dox files
			dox_files = [rf'*{doxygen.mangle_name(ext)}.xml' for ext in (r'.dox', r'.md')]
			dox_files.append(r'md_home.xml')
			for xml_file in get_all_files(context.temp_xml_dir, any=dox_files):
				delete_file(xml_file, logger=context.verbose_logger)

			# 'dir' entries for empty directories
			deleted = True
			while deleted:
				deleted = False
				for xml_file in get_all_files(context.temp_xml_dir, all=(r'dir*.xml')):
					xml = etree.parse(str(xml_file), parser=xml_parser)
					compounddef = xml.getroot().find(r'compounddef')
					if compounddef is None or compounddef.get(r'kind') != r'dir':
						continue
					existing_inners = 0
					for subtype in (r'innerfile', r'innerdir'):
						for inner in compounddef.findall(subtype):
							ref_file = Path(context.temp_xml_dir, rf'{inner.get(r"refid")}.xml')
							if ref_file.exists():
								existing_inners = existing_inners + 1
					if not existing_inners:
						delete_file(xml_file, logger=context.verbose_logger)
						deleted = True

		extracted_implementation = False
		tentative_macros = regex_or(context.code_blocks.macros)
		macros = set()
		cpp_tree = CppTree()
		xml_files = get_all_files(context.temp_xml_dir, any=(r'*.xml'))
		tagfiles = [f for _, (f, _) in context.tagfiles.items()]
		xml_files = xml_files + tagfiles
		all_inners_by_type = {r'namespace': set(), r'class': set(), r'concept': set()}
		for xml_file in xml_files:

			context.verbose(rf'Pre-processing {xml_file}')
			if xml_file.name == r'Doxyfile.xml':
				continue

			xml = etree.parse(str(xml_file), parser=xml_parser)
			root = xml.getroot()
			changed = False

			# the doxygen index
			if root.tag == r'doxygenindex':

				# remove entries for files we might have explicitly deleted above
				for compound in [
					tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'file', r'dir', r'concept')
				]:
					ref_file = Path(context.temp_xml_dir, rf'{compound.get(r"refid")}.xml')
					if not ref_file.exists():
						root.remove(compound)
						changed = True

				# extract namespaces, types and enum values for syntax highlighting
				scopes = [
					tag for tag in root.findall(r'compound')
					if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union')
				]
				for scope in scopes:
					scope_name = scope.find(r'name').text

					# skip template members because they'll break the regex matchers
					if scope_name.find(r'<') != -1:
						continue

					# regular types and namespaces
					if scope.get(r'kind') in (r'class', r'struct', r'union'):
						cpp_tree.add_type(scope_name)
					elif scope.get(r'kind') == r'namespace':
						cpp_tree.add_namespace(scope_name)

					# nested enums
					enum_tags = [tag for tag in scope.findall(r'member') if tag.get(r'kind') in (r'enum', r'enumvalue')]
					enum_name = ''
					for tag in enum_tags:
						if tag.get(r'kind') == r'enum':
							enum_name = rf'{scope_name}::{tag.find("name").text}'
							cpp_tree.add_type(enum_name)
						else:
							assert enum_name
							cpp_tree.add_enum_value(rf'{enum_name}::{tag.find("name").text}')

					# nested typedefs
					typedefs = [tag for tag in scope.findall(r'member') if tag.get(r'kind') == r'typedef']
					for typedef in typedefs:
						cpp_tree.add_type(rf'{scope_name}::{typedef.find("name").text}')

				# enumerate all compound pages and their types for later (e.g. HTML post-process)
				for tag in root.findall(r'compound'):
					refid = tag.get(r'refid')
					filename = refid
					if filename == r'indexpage':
						filename = r'index'
					filename = filename + r'.html'
					context.compound_pages[filename] = {
						r'kind': tag.get(r'kind'),
						r'name': tag.find(r'name').text,
						r'refid': refid
					}
					context.compound_kinds.add(tag.get(r'kind'))
				context.verbose_value(r'Context.compound_pages', context.compound_pages)
				context.verbose_value(r'Context.compound_kinds', context.compound_kinds)

			# a tag file
			elif root.tag == r'tagfile':
				for compound in [
					tag for tag in root.findall(r'compound')
					if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union', r'concept')
				]:

					compound_name = compound.find(r'name').text
					if compound_name.find(r'<') != -1:
						continue

					compound_type = compound.get(r'kind')
					if compound_type in (r'class', r'struct', r'union', r'concept'):
						cpp_tree.add_type(compound_name)
					else:
						cpp_tree.add_namespace(compound_name)

					for member in [
						tag for tag in compound.findall(r'member')
						if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union', r'concept')
					]:

						member_name = member.find(r'name').text
						if member_name.find(r'<') != -1:
							continue

						member_type = member.get(r'kind')
						if member_type in (r'class', r'struct', r'union', r'concept'):
							cpp_tree.add_type(compound_name)
						else:
							cpp_tree.add_namespace(compound_name)

			# some other compound definition
			else:
				compounddef = root.find(r'compounddef')
				if compounddef is None:
					context.warning(rf'{xml_file} did not contain a <compounddef>!')
					continue

				compound_id = compounddef.get(r'id')
				if compound_id is None or not compound_id:
					context.warning(rf'{xml_file} did not have attribute "id"!')
					continue

				compound_kind = compounddef.get(r'kind')
				if compound_kind is None or not compound_kind:
					context.warning(rf'{xml_file} did not have attribute "kind"!')
					continue

				compound_name = compounddef.find(r'compoundname')
				if compound_name is None or not compound_name.text:
					context.warning(rf'{xml_file} did not contain a valid <compoundname>!')
					continue
				compound_name = str(compound_name.text).strip()

				if compound_kind != r'page':

					# merge user-defined sections with the same name
					sectiondefs = [s for s in compounddef.findall(r'sectiondef') if s.get(r'kind') == r'user-defined']
					sections = dict()
					for section in sectiondefs:
						header = section.find(r'header')
						if header is not None and header.text:
							if header.text not in sections:
								sections[header.text] = []
						sections[header.text].append(section)
					for key, vals in sections.items():
						if len(vals) > 1:
							first_section = vals.pop(0)
							for section in vals:
								for member in section.findall(r'memberdef'):
									section.remove(member)
									first_section.append(member)
								compounddef.remove(section)
								changed = True

					# sort user-defined sections based on their name
					sectiondefs = [s for s in compounddef.findall(r'sectiondef') if s.get(r'kind') == r'user-defined']
					sectiondefs = [s for s in sectiondefs if s.find(r'header') is not None]
					for section in sectiondefs:
						compounddef.remove(section)
					sectiondefs.sort(key=lambda s: s.find(r'header').text)
					for section in sectiondefs:
						compounddef.append(section)
						changed = True

					# per-section stuff
					for section in compounddef.findall(r'sectiondef'):

						# remove members which are listed multiple times because doxygen is idiotic:
						members = [tag for tag in section.findall(r'memberdef')]
						for i in range(len(members) - 1, 0, -1):
							for j in range(i):
								if members[i].get(r'id') == members[j].get(r'id'):
									section.remove(members[i])
									changed = True
									break

						# fixes for functions:
						# - goofy parsing of trailing return types
						# - keywords like 'friend' erroneously included in the return type
						if 1:

							members = [
								m for m in section.findall(r'memberdef') if m.get(r'kind') in (r'friend', r'function')
							]

							# trailing return type bug (https://github.com/mosra/m.css/issues/94)
							for member in members:
								type_elem = member.find(r'type')
								if type_elem is None or type_elem.text != r'auto':
									continue
								args_elem = member.find(r'argsstring')
								if args_elem is None or not args_elem.text or args_elem.text.find(r'decltype') != -1:
									continue
								match = re.search(r'^(.*?)\s*->\s*([a-zA-Z][a-zA-Z0-9_::*&<>\s]+?)\s*$', args_elem.text)
								if match:
									args_elem.text = str(match[1])
									trailing_return_type = str(match[2]).strip()
									trailing_return_type = re.sub(r'\s+', r' ', trailing_return_type)
									trailing_return_type = re.sub(r'(::|[<>*&])\s+', r'\1', trailing_return_type)
									trailing_return_type = re.sub(r'\s+(::|[<>*&])', r'\1', trailing_return_type)
									type_elem.text = trailing_return_type
									changed = True

							# leaked keywords
							attribute_keywords = (
								(r'constexpr', r'constexpr', r'yes'),  #
								(r'consteval', r'consteval', r'yes'),
								(r'explicit', r'explicit', r'yes'),
								(r'static', r'static', r'yes'),
								(r'friend', None, None),
								(r'inline', r'inline', r'yes'),
								(r'virtual', r'virt', r'virtual')
							)
							for member in members:
								type = member.find(r'type')
								if type is None or type.text is None:
									continue
								matched_bad_keyword = True
								while matched_bad_keyword:
									matched_bad_keyword = False
									for kw, attr, attr_value in attribute_keywords:
										if type.text == kw:  # constructors
											type.text = ''
										elif type.text.startswith(kw + ' '):
											type.text = type.text[len(kw):].strip()
										elif type.text.endswith(' ' + kw):
											type.text = type.text[:len(kw)].strip()
										else:
											continue
										matched_bad_keyword = True
										changed = True
										if attr is not None:
											member.set(attr, attr_value)
										elif kw == r'friend':
											member.set(r'kind', r'friend')

						# re-sort members to override Doxygen's weird and stupid sorting 'rules'
						if 1:
							sort_members_by_name = lambda tag: tag.find(r'name').text
							members = [tag for tag in section.findall(r'memberdef')]
							for tag in members:
								section.remove(tag)
							# fmt: off
							# yapf: disable
							groups = [
								([tag for tag in members if tag.get(r'kind') == r'define'], True),  #
								([tag for tag in members if tag.get(r'kind') == r'typedef'], True),
								([tag for tag in members if tag.get(r'kind') == r'concept'], True),
								([tag for tag in members if tag.get(r'kind') == r'enum'], True),
								([tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'yes'], True),
								([tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'no'], compound_kind not in (r'class', r'struct', r'union')),
								([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'yes'], True),
								([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'no'], True),
								([tag for tag in members if tag.get(r'kind') == r'friend'], True)
							]
							# yapf: enable
							# fmt: on
							for group, sort in groups:
								if sort:
									group.sort(key=sort_members_by_name)
								for tag in group:
									members.remove(tag)
									section.append(tag)
									changed = True
							# if we've missed any groups just glob them on the end
							if members:
								members.sort(key=sort_members_by_name)
								changed = True
								for tag in members:
									section.append(tag)

				# namespaces
				if compound_kind == r'namespace':

					# set inline namespaces
					if context.inline_namespaces:
						for nsid in inline_namespace_ids:
							if compound_id == nsid:
								compounddef.set(r'inline', r'yes')
								changed = True
								break

				# dirs
				if compound_kind == r'dir':

					# remove implementation headers
					if context.implementation_headers:
						for innerfile in compounddef.findall(r'innerfile'):
							if innerfile.get(r'refid') in implementation_header_mappings:
								compounddef.remove(innerfile)
								changed = True

				# files
				if compound_kind == r'file':

					# simplify the XML by removing unnecessary junk
					for tag in (r'includes', r'includedby', r'incdepgraph', r'invincdepgraph'):
						for t in compounddef.findall(tag):
							compounddef.remove(t)
							changed = True

					# get any macros for the syntax highlighter
					for sectiondef in [
						tag for tag in compounddef.findall(r'sectiondef') if tag.get(r'kind') == r'define'
					]:
						for memberdef in [
							tag for tag in sectiondef.findall(r'memberdef') if tag.get(r'kind') == r'define'
						]:
							macro = memberdef.find(r'name').text
							if not tentative_macros.fullmatch(macro):
								macros.add(macro)

					# rip the good bits out of implementation headers
					if context.implementation_headers:
						iid = compound_id
						if iid in implementation_header_mappings:
							hid = implementation_header_mappings[iid][2]
							innernamespaces = compounddef.findall(r'innernamespace')
							if innernamespaces:
								implementation_header_innernamespaces[
									hid] = implementation_header_innernamespaces[hid] + innernamespaces
								extracted_implementation = True
								if iid in implementation_header_unused_values:
									del implementation_header_unused_values[iid]
								for tag in innernamespaces:
									compounddef.remove(tag)
									changed = True
							sectiondefs = compounddef.findall(r'sectiondef')
							if sectiondefs:
								implementation_header_sectiondefs[
									hid] = implementation_header_sectiondefs[hid] + sectiondefs
								extracted_implementation = True
								if iid in implementation_header_unused_values:
									del implementation_header_unused_values[iid]
								for tag in sectiondefs:
									compounddef.remove(tag)
									changed = True

				# groups and namespaces
				if compound_kind in (r'group', r'namespace'):

					# fix inner(class|namespace|group|concept) sorting
					inners = [tag for tag in compounddef.iterchildren() if tag.tag.startswith(r'inner')]
					if inners:
						changed = True
						for tag in inners:
							compounddef.remove(tag)
						inners.sort(key=lambda tag: tag.text)
						for tag in inners:
							compounddef.append(tag)

				# all namespace 'innerXXXXXX'
				if compound_kind in (r'namespace', r'struct', r'class', r'union', r'concept'):
					if compound_name.rfind(r'::') != -1:
						all_inners_by_type[r'class' if compound_kind in (r'struct', r'union') else compound_kind].add(
							(compound_id, compound_name)
						)

			if changed and xml_file not in tagfiles:  # tagfiles are read-only - ensure we don't modify them
				write_xml_to_file(xml, xml_file)

		# add to syntax highlighter
		context.code_blocks.namespaces.add(cpp_tree.matcher(CppTree.NAMESPACES))
		context.code_blocks.types.add(cpp_tree.matcher(CppTree.TYPES))
		context.code_blocks.enums.add(cpp_tree.matcher(CppTree.ENUM_VALUES))
		for macro in macros:
			context.code_blocks.macros.add(macro)
		context.verbose_object(r'Context.code_blocks', context.code_blocks)

		# fix up namespaces/classes that are missing <innerXXXX> nodes
		if 1:
			outer_namespaces = dict()
			for inner_type, ids_and_names in all_inners_by_type.items():
				for id, name in ids_and_names:
					ns = name[:name.rfind(r'::')]
					assert ns
					if ns not in outer_namespaces:
						outer_namespaces[ns] = []
					outer_namespaces[ns].append((inner_type, id, name))
			for ns, vals in outer_namespaces.items():
				xml_file = None
				for outer_type in (r'namespace', r'struct', r'class', r'union'):
					f = Path(context.temp_xml_dir, rf'{outer_type}{doxygen.mangle_name(ns)}.xml')
					if f.exists():
						xml_file = f
						break
				if not xml_file:
					continue
				xml = etree.parse(str(xml_file), parser=xml_parser)
				compounddef = xml.getroot().find(r'compounddef')
				if compounddef is None:
					continue
				changed = False
				existing_inner_ids = set()
				for inner_type in (r'class', r'namespace', r'concept'):
					for elem in compounddef.findall(rf'inner{inner_type}'):
						id = elem.get(r'refid')
						if id:
							existing_inner_ids.add(str(id))
				for (inner_type, id, name) in vals:
					if id not in existing_inner_ids:
						elem = etree.SubElement(compounddef, rf'inner{inner_type}')
						elem.text = name
						elem.set(r'refid', id)
						elem.set(r'prot', r'public')  # todo: this isn't necessarily correct
						existing_inner_ids.add(id)
						changed = True
				if changed:
					write_xml_to_file(xml, xml_file)

		# merge extracted implementations
		if extracted_implementation:
			for (hp, hfn, hid, impl) in implementation_header_data:
				xml_file = Path(context.temp_xml_dir, rf'{hid}.xml')
				context.verbose(rf'Merging implementation nodes into {xml_file}')
				xml = etree.parse(str(xml_file), parser=xml_parser)
				compounddef = xml.getroot().find(r'compounddef')
				changed = False

				innernamespaces = compounddef.findall(r'innernamespace')
				for new_tag in implementation_header_innernamespaces[hid]:
					matched = False
					for existing_tag in innernamespaces:
						if existing_tag.get(r'refid') == new_tag.get(r'refid'):
							matched = True
							break
					if not matched:
						compounddef.append(new_tag)
						innernamespaces.append(new_tag)
						changed = True

				sectiondefs = compounddef.findall(r'sectiondef')
				for new_section in implementation_header_sectiondefs[hid]:
					matched_section = False
					for existing_section in sectiondefs:
						if existing_section.get(r'kind') == new_section.get(r'kind'):
							matched_section = True

							memberdefs = existing_section.findall(r'memberdef')
							new_memberdefs = new_section.findall(r'memberdef')
							for new_memberdef in new_memberdefs:
								matched = False
								for existing_memberdef in memberdefs:
									if existing_memberdef.get(r'id') == new_memberdef.get(r'id'):
										matched = True
										break

								if not matched:
									new_section.remove(new_memberdef)
									existing_section.append(new_memberdef)
									memberdefs.append(new_memberdef)
									changed = True
							break

					if not matched_section:
						compounddef.append(new_section)
						sectiondefs.append(new_section)
						changed = True

				if changed:
					implementation_header_unused_keys.remove(hp)
					write_xml_to_file(xml, xml_file)

		# sanity-check implementation header state
		if implementation_header_unused_keys:
			for key in implementation_header_unused_keys:
				context.warning(rf"implementation_header: nothing extracted for '{key}'")
		if implementation_header_unused_values:
			for iid, idata in implementation_header_unused_values.items():
				context.warning(rf"implementation_header: nothing extracted from '{idata[0]}' for '{idata[1]}'")

	# delete the impl header xml files
	if 1 and context.implementation_headers:
		for hdata in implementation_header_data:
			for (ip, ifn, iid) in hdata[3]:
				delete_file(Path(context.temp_xml_dir, rf'{iid}.xml'), logger=context.verbose_logger)

	# scan through the files and substitute impl header ids and paths as appropriate
	if 1 and context.implementation_headers:
		xml_files = get_all_files(context.temp_xml_dir, any=('*.xml'))
		for xml_file in xml_files:
			context.verbose(rf"Re-linking implementation headers in '{xml_file}'")
			xml_text = read_all_text_from_file(xml_file, logger=context.verbose_logger)
			for (hp, hfn, hid, impl) in implementation_header_data:
				for (ip, ifn, iid) in impl:
					#xml_text = xml_text.replace(f'refid="{iid}"',f'refid="{hid}"')
					xml_text = xml_text.replace(rf'compoundref="{iid}"', f'compoundref="{hid}"')
					xml_text = xml_text.replace(ip, hp)
			with BytesIO(bytes(xml_text, 'utf-8')) as b:
				xml = etree.parse(b, parser=xml_parser)
				write_xml_to_file(xml, xml_file)



def postprocess_xml_v2(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	log_func = lambda m: context.verbose(m)

	g = doxygen.read_graph_from_xml(context.temp_xml_dir, log_func=log_func)

	# delete 'file' nodes for markdown and dox files
	g.remove(filter=lambda n: n.type is graph.File and re.search(r'[.](?:md|dox)$', n.local_name, flags=re.I))

	# delete empty 'dir' nodes
	g.remove(filter=lambda n: n.type is graph.Directory and not len(list(n(graph.File, graph.Directory))))

	# todo:
	# - extract namespaces, types and enum values for syntax highlighting
	# - enumerate all compound pages and their types for later (e.g. HTML post-process)
	# - merge user-defined sections with the same name
	# - sort user-defined sections based on their name
	# - implementation headers

	for f in enumerate_files(context.temp_xml_dir, any=r'*.xml'):
		delete_file(f, logger=log_func)
	doxygen.write_graph_to_xml(g, context.temp_xml_dir, log_func=log_func)



def compile_syntax_highlighter_regexes(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	context.code_blocks.namespaces = regex_or(
		context.code_blocks.namespaces, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?'
	)
	context.code_blocks.types = regex_or(context.code_blocks.types, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
	context.code_blocks.enums = regex_or(context.code_blocks.enums, pattern_prefix='(?:::)?')
	context.code_blocks.macros = regex_or(context.code_blocks.macros)
	context.autolinks = tuple([(re.compile('(?<![a-zA-Z_])' + expr + '(?![a-zA-Z_])'), uri)
		for expr, uri in context.autolinks])



def preprocess_mcss_config(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	# build HTML_HEADER
	html_header = ''
	if 1:
		# stylesheets
		for stylesheet in context.stylesheets:
			html_header += f'<link href="{stylesheet}" rel="stylesheet" referrerpolicy="no-referrer" />\n'
		# scripts
		for script in context.scripts:
			html_header += f'<script src="{script}"></script>\n'
		if context.theme != r'custom':
			html_header += f'<script>initialize_theme("{context.theme}");</script>\n'
		# metadata
		def add_meta_kvp(key_name, key, content):
			nonlocal html_header
			html_header += f'<meta {key_name}="{key}" content="{content}">\n'

		add_meta = lambda key, content: add_meta_kvp(r'name', key, content)
		add_property = lambda key, content: add_meta_kvp(r'property', key, content)
		add_itemprop = lambda key, content: add_meta_kvp(r'itemprop', key, content)
		# metadata - project name
		if context.name:
			if r'twitter:title' not in context.meta_tags:
				add_meta(r'twitter:title', context.name)
			add_property(r'og:title', context.name)
			add_itemprop(r'name', context.name)
		# metadata - project author
		if context.author:
			if r'author' not in context.meta_tags:
				add_meta(r'author', context.author)
			add_property(r'article:author', context.author)
		# metadata - project description
		if context.description:
			if r'description' not in context.meta_tags:
				add_meta(r'description', context.description)
			if r'twitter:description' not in context.meta_tags:
				add_meta(r'twitter:description', context.description)
			add_property(r'og:description', context.description)
			add_itemprop(r'description', context.description)
		# metadata - robots
		if not context.robots:
			if r'robots' not in context.meta_tags:
				add_meta(r'robots', r'noindex, nofollow')
			if r'googlebot' not in context.meta_tags:
				add_meta(r'googlebot', r'noindex, nofollow')
		# metadata - misc
		if r'format-detection' not in context.meta_tags:
			add_meta(r'format-detection', r'telephone=no')
		if r'generator' not in context.meta_tags:
			add_meta(r'generator', rf'Poxy v{context.version_string}')
		if r'referrer' not in context.meta_tags:
			add_meta(r'referrer', r'strict-origin-when-cross-origin')
		# metadata - additional user-specified tags
		for name, content in context.meta_tags.items():
			add_meta(name, content)
		# html_header
		if context.html_header:
			html_header += f'{context.html_header}\n'
		html_header = html_header.rstrip()

	# build + write conf.py
	with StringIO(newline='\n') as conf_py:
		conf = lambda s='', end='\n': print(reindent(s, indent=''), file=conf_py, end=end)

		# basic properties
		conf(rf"DOXYFILE = r'{context.doxyfile_path}'")
		conf(r"STYLESHEETS = []")  # suppress the default behaviour
		conf(rf'HTML_HEADER = """{html_header}"""')
		if context.theme == r'dark':
			conf(r"THEME_COLOR = '#22272e'")
		elif context.theme == r'light':
			conf(r"THEME_COLOR = '#cb4b16'")
		if context.favicon:
			conf(rf"FAVICON = r'{context.favicon}'")
		elif context.theme == r'dark':
			conf(rf"FAVICON = 'favicon-dark.png'")
		elif context.theme == r'light':
			conf(rf"FAVICON = 'favicon-light.png'")
		conf(rf'SHOW_UNDOCUMENTED = {context.sources.extract_all}')
		conf(r'CLASS_INDEX_EXPAND_LEVELS = 3')
		conf(r'FILE_INDEX_EXPAND_LEVELS = 3')
		conf(r'CLASS_INDEX_EXPAND_INNER = True')
		conf(r'SEARCH_DOWNLOAD_BINARY = False')
		conf(r'SEARCH_DISABLED = False')

		# navbar
		NAVBAR_ALIASES = {
			# poxy -> doxygen
			r'classes': r'annotated',
			r'groups': r'modules'
		}
		NAVBAR_TO_KIND = {
			r'annotated': (r'class', r'struct', r'union'),
			r'concepts': (r'concept', ),
			r'namespaces': (r'namespace', ),
			r'pages': (r'page', ),
			r'modules': (r'group', ),
			r'files': (r'file', r'dir')
		}
		navbar = ([], [])
		if context.navbar:
			# populate the navbar
			bar = [(NAVBAR_ALIASES[b] if b in NAVBAR_ALIASES else b) for b in context.navbar]
			# remove links to index pages that will have no entries
			for i in range(len(bar)):
				if bar[i] not in NAVBAR_TO_KIND:
					continue
				found = False
				for kind in NAVBAR_TO_KIND[bar[i]]:
					if kind in context.compound_kinds:
						found = True
						break
				if not found:
					bar[i] = None
			bar = [b for b in bar if b is not None]
			# handle theme and repo links
			for i in range(len(bar)):
				if bar[i] == r'repo' and context.repo:
					icon_path = Path(dirs.DATA, context.repo.icon_filename)
					if icon_path.exists():
						svg = SVG(icon_path, logger=context.verbose_logger, root_id=r'poxy-repo-icon')
						bar[i] = (
							rf'<a title="View on {type(context.repo).__name__}" '
							+ rf'target="_blank" href="{context.repo.uri}" '
							+ rf'class="poxy-icon repo {context.repo.KEY}">{svg}</a>', []
						)
					else:
						bar[i] = None
				elif bar[i] == r'theme':
					svg = SVG(
						Path(dirs.DATA, r'poxy-icon-theme.svg'),
						logger=context.verbose_logger,
						root_id=r'poxy-theme-switch-img'
					)
					bar[i] = (
						r'<a title="Toggle dark and light themes" '
						+ r'id="poxy-theme-switch" href="javascript:void(null);" role="button" '
						+ rf'class="poxy-icon theme" onClick="toggle_theme(); return false;">{svg}</a>', []
					)
			bar = [b for b in bar if b is not None]
			# automatically overflow onto the second row
			split = min(max(int(len(bar) / 2) + len(bar) % 2, 2), len(bar))
			for b, i in ((bar[:split], 0), (bar[split:], 1)):
				for j in range(len(b)):
					if isinstance(b[j], tuple):
						navbar[i].append(b[j])
					else:
						navbar[i].append((None, b[j], []))
		for i in (0, 1):
			if navbar[i]:
				conf(f'LINKS_NAVBAR{i+1} = [\n\t', end='')
				conf(',\n\t'.join([rf'{b}' for b in navbar[i]]))
				conf(r']')
			else:
				conf(rf'LINKS_NAVBAR{i+1} = []')

		# footer
		conf(r"FINE_PRINT = r'''")
		footer = []
		if context.repo:
			footer.append(rf'<a href="{context.repo.uri}" target="_blank">{type(context.repo).__name__}</a>')
			footer.append(rf'<a href="{context.repo.issues_uri}" target="_blank">Report an issue</a>')
		if context.changelog:
			footer.append(rf'<a href="md_poxy_changelog.html">Changelog</a>')
		if context.license and context.license[r'uri']:
			footer.append(rf'<a href="{context.license["uri"]}" target="_blank">License</a>')
		if context.generate_tagfile:
			footer.append(
				rf'<a href="{context.tagfile_path.name}" target="_blank" type="text/xml" download>Doxygen tagfile</a>'
			)
		if footer:
			for i in range(1, len(footer)):
				footer[i] = r' &bull; ' + footer[i]
			footer.append(r'<br><br>')
		footer.append(r'Site generated using <a href="https://github.com/marzer/poxy/">Poxy</a>')
		for i in range(len(footer)):
			conf(rf"    {footer[i]}")
		conf(r"'''")

		conf_py_text = conf_py.getvalue()
		context.verbose(r'm.css conf.py:')
		context.verbose(conf_py_text, indent=r'   ')

		# write conf.py
		context.verbose(rf'Writing {context.mcss_conf_path}')
		with open(context.mcss_conf_path, r'w', encoding=r'utf-8', newline='\n') as f:
			f.write(conf_py_text)



_worker_context = None



def _initialize_worker(context):
	global _worker_context
	_worker_context = context



def postprocess_html_file(path, context: Context = None):
	assert path is not None
	assert isinstance(path, Path)
	assert path.is_absolute()
	assert path.exists()

	if context is None:
		global _worker_context
		context = _worker_context
	assert context is not None
	assert isinstance(context, Context)

	context.info(rf'Post-processing {path}')
	text = None
	html = None

	def switch_to_html():
		nonlocal context
		nonlocal text
		nonlocal html
		if html is not None:
			return
		html = soup.HTMLDocument(text, logger=context.verbose_logger)

	def switch_to_text():
		nonlocal context
		nonlocal text
		nonlocal html
		if html is None:
			return
		html.smooth()
		text = str(html)
		html = None

	try:
		text = read_all_text_from_file(path, logger=context.verbose_logger)
		changed = False

		for fix in context.fixers:
			if isinstance(fix, fixers.HTMLFixer):
				switch_to_html()
				if fix(context, html, path):
					changed = True
					html.smooth()
			elif isinstance(fix, fixers.PlainTextFixer):
				switch_to_text()
				prev_text = text
				text = fix(context, prev_text, path)
				changed = changed or prev_text != text

		if changed:
			switch_to_text()
			context.verbose(rf'Writing {path}')
			with open(path, 'w', encoding='utf-8', newline='\n') as f:
				f.write(text)

	except Exception as e:
		context.info(rf'{type(e).__name__} raised while post-processing {path}')
		raise
	except:
		context.info(rf'Error occurred while post-processing {path}')
		raise



def postprocess_html(context: Context):
	assert context is not None
	assert isinstance(context, Context)

	files = filter_filenames(
		get_all_files(context.html_dir, any=('*.html', '*.htm')), context.html_include, context.html_exclude
	)
	if not files:
		return

	context.fixers = (
		fixers.MarkTOC(),
		fixers.Pygments(),
		fixers.CodeBlocks(),
		fixers.Banner(),
		fixers.CPPModifiers1(),
		fixers.CPPModifiers2(),
		fixers.CPPTemplateTemplate(),
		fixers.StripIncludes(),
		fixers.AutoDocLinks(),
		fixers.Links(),
		fixers.CustomTags(),
		fixers.EmptyTags(),
		fixers.ImplementationDetails(),
		fixers.MarkdownPages(),
		fixers.InjectSVGs(),
	)

	threads = min(len(files), context.threads, 16)
	context.info(rf'Post-processing {len(files)} HTML files on {threads} thread{"s" if threads > 1 else ""}...')
	if threads > 1:
		with futures.ProcessPoolExecutor(
			max_workers=threads, initializer=_initialize_worker, initargs=(context, )
		) as executor:
			jobs = [executor.submit(postprocess_html_file, file) for file in files]
			for future in futures.as_completed(jobs):
				try:
					future.result()
				except:
					try:
						executor.shutdown(wait=False, cancel_futures=True)
					except TypeError:
						executor.shutdown(wait=False)
					raise

	else:
		for file in files:
			postprocess_html_file(file, context)



#=======================================================================================================================
# RUN
#=======================================================================================================================



def read_output_streams(stdout, stderr):
	stdout.seek(0)
	stderr.seek(0)
	return {r'stdout': stdout.read().strip(), r'stderr': stderr.read().strip()}



def dump_output_streams(context, outputs, source=''):
	if source:
		source = rf'{source} '
	if outputs[r'stdout']:
		context.info(rf'{source}stdout:')
		context.info(outputs[r'stdout'], indent=r'    ')
	if outputs[r'stderr']:
		context.info(rf'{source}stderr:')
		context.info(outputs[r'stderr'], indent=r'    ')



_warnings_regexes = (
	# doxygen
	re.compile(r'^(?P<file>.+?):(?P<line>[0-9]+): warning:\s*(?P<text>.+?)\s*$', re.I),
	# m.css
	re.compile(r'^WARNING:root:(?P<file>.+[.]xml):\s*(?P<text>.+?)\s*$', re.I),
	re.compile(r'^WARNING:root:\s*(?P<text>.+?)\s*$', re.I),
	# catch-all
	re.compile(r'^(?:Warning|Error):\s*(?P<text>.+?)\s*$', re.I)
)
_warnings_trim_suffixes = (r'Skipping it...', )
_warnings_substitutions = ((r'does not exist or is not a file', r'did not exist or was not a file'), )
_warnings_ignored = (r'inline code has multiple lines, fallback to a code block', r'libgs not found')



def extract_warnings(outputs):
	if not outputs:
		return []

	global _warnings_regexes
	global _warnings_ignored
	global _warnings_trim_suffixes
	global _warnings_substitutions

	warnings = []
	for k, v in outputs.items():
		if not v:
			continue
		output = v.split('\n')
		for o in output:
			for regex in _warnings_regexes:
				m = regex.fullmatch(o)
				if m:
					text = m[r'text'].strip()
					for suffix in _warnings_trim_suffixes:
						if text.endswith(suffix):
							text = text[:-len(suffix)].strip()
							break
					for old, new in _warnings_substitutions:
						text = text.replace(old, new)
					if not text or text in _warnings_ignored:
						break
					groups = m.groupdict()
					if r'file' in groups:
						if r'line' in groups:
							warnings.append(rf"{m[r'file']}:{m[r'line']}: {text}")
						else:
							warnings.append(rf"{m[r'file']}: {text}")
					else:
						warnings.append(text)
					break
	return warnings



def run_doxygen(context: Context):
	assert context is not None
	assert isinstance(context, Context)
	with make_temp_file() as stdout, make_temp_file() as stderr:
		try:
			subprocess.run([str(doxygen.path()), str(context.doxyfile_path)],
				check=True,
				stdout=stdout,
				stderr=stderr,
				cwd=context.input_dir)
		except:
			context.info(r'Doxygen failed!')
			dump_output_streams(context, read_output_streams(stdout, stderr), source=r'Doxygen')
			raise
		if context.is_verbose() or context.warnings.enabled:
			outputs = read_output_streams(stdout, stderr)
			if context.is_verbose():
				dump_output_streams(context, outputs, source=r'Doxygen')
			if context.warnings.enabled:
				warnings = extract_warnings(outputs)
				for w in warnings:
					context.warning(w)

	# remove the local paths from the tagfile since they're meaningless (and a privacy breach)
	if context.tagfile_path:
		text = read_all_text_from_file(context.tagfile_path, logger=context.verbose_logger)
		text = re.sub(r'\n\s*?<path>.+?</path>\s*?\n', '\n', text, re.S)
		context.verbose(rf'Writing {context.tagfile_path}')
		with open(context.tagfile_path, 'w', encoding='utf-8', newline='\n') as f:
			f.write(text)



def run_mcss(context: Context):
	assert context is not None
	assert isinstance(context, Context)
	with make_temp_file() as stdout, make_temp_file() as stderr:
		doxy_args = [str(context.mcss_conf_path), r'--no-doxygen', r'--sort-globbed-files']
		if context.is_verbose():
			doxy_args.append(r'--debug')
		try:
			run_python_script(
				Path(dirs.MCSS, r'documentation/doxygen.py'),
				*doxy_args,
				stdout=stdout,
				stderr=stderr,
				cwd=context.input_dir
			)
		except:
			context.info(r'm.css failed!')
			dump_output_streams(context, read_output_streams(stdout, stderr), source=r'm.css')
			raise
		if context.is_verbose() or context.warnings.enabled:
			outputs = read_output_streams(stdout, stderr)
			if context.is_verbose():
				dump_output_streams(context, outputs, source=r'm.css')
			if context.warnings.enabled:
				warnings = extract_warnings(outputs)
				for w in warnings:
					context.warning(w)



def run(
	config_path: Path = None,
	output_dir: Path = '.',
	output_html: bool = True,
	output_xml: bool = False,
	threads: int = -1,
	cleanup: bool = True,
	verbose: bool = False,
	logger=None,
	html_include: str = None,
	html_exclude: str = None,
	treat_warnings_as_errors: bool = None,
	theme: str = None,
	copy_assets: bool = True,
	**kwargs
):

	timer = lambda desc: ScopeTimer(desc, print_start=True, print_end=context.verbose_logger)

	with Context(
		config_path=config_path,
		output_dir=output_dir,
		output_html=output_html,
		output_xml=output_xml,
		threads=threads,
		cleanup=cleanup,
		verbose=verbose,
		logger=logger,
		html_include=html_include,
		html_exclude=html_exclude,
		treat_warnings_as_errors=treat_warnings_as_errors,
		theme=theme,
		copy_assets=copy_assets,
		**kwargs
	) as context:

		preprocess_doxyfile(context)
		preprocess_tagfiles(context)
		preprocess_changelog(context)

		if not context.output_html and not context.output_xml:
			return

		# generate + postprocess XML in temp_xml_dir
		# (we always do this even when output_xml is false because it is required by the html)
		with timer(rf'Generating XML files with Doxygen {doxygen.version()}') as t:
			run_doxygen(context)
		with timer(r'Post-processing XML files') as t:
			if context.xml_v2:
				postprocess_xml_v2(context)
			else:
				postprocess_xml(context)

		# postprocess_xml extracts type information so now we can compile the highlighter regexes
		compile_syntax_highlighter_regexes(context)

		# XML (the user-requested copy)
		if context.output_xml:

			with ScopeTimer(r'Copying XML', print_start=True, print_end=context.verbose_logger) as t:
				copy_tree(str(context.temp_xml_dir), str(context.xml_dir))

			# copy tagfile
			if context.generate_tagfile:
				copy_file(context.tagfile_path, context.xml_dir, logger=context.verbose_logger)

		# HTML
		if context.output_html:

			# generate HTML with mcss
			preprocess_mcss_config(context)
			with timer(r'Generating HTML files with m.css') as t:
				run_mcss(context)

			# copy extra_files
			with ScopeTimer(r'Copying extra_files', print_start=True, print_end=context.verbose_logger) as t:
				for dest_name, source_path in context.extra_files.items():
					dest_path = Path(context.html_dir, dest_name).resolve()
					dest_path.parent.mkdir(exist_ok=True)
					copy_file(source_path, dest_path, logger=context.verbose_logger)

			# copy fonts
			if context.copy_assets:
				with ScopeTimer(r'Copying fonts', print_start=True, print_end=context.verbose_logger) as t:
					copy_tree(str(dirs.FONTS), str(Path(context.assets_dir, r'fonts')))

			# copy tagfile
			if context.generate_tagfile:
				copy_file(context.tagfile_path, context.html_dir, logger=context.verbose_logger)

			# post-process html files
			with timer(r'Post-processing HTML files') as t:
				postprocess_html(context)
