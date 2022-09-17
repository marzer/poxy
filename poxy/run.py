#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

"""
The 'actually do the thing' module.
"""

from distutils.dir_util import copy_tree
import os
import subprocess
import concurrent.futures as futures
import tempfile
import requests
from lxml import etree
from io import BytesIO, StringIO
from .utils import *
from . import project
from . import doxyfile
from . import soup
from . import fixers

__all__ = []


#=======================================================================================================================
# PRE/POST PROCESSORS
#=======================================================================================================================

_doxygen_overrides  = (
		(r'ALLEXTERNALS',			False),
		(r'ALLOW_UNICODE_NAMES',	False),
		(r'ALWAYS_DETAILED_SEC',	False),
		(r'AUTOLINK_SUPPORT',		True),
		(r'BUILTIN_STL_SUPPORT',	False),
		(r'CASE_SENSE_NAMES',		False),
		(r'CLASS_DIAGRAMS',			False),
		(r'CPP_CLI_SUPPORT',		False),
		(r'CREATE_SUBDIRS',			False),
		(r'DISTRIBUTE_GROUP_DOC',	False),
		(r'DOXYFILE_ENCODING',		r'UTF-8'),
		(r'DOT_FONTNAME',			r'Source Sans Pro'),
		(r'DOT_FONTSIZE',			16),
		(r'ENABLE_PREPROCESSING',	True),
		(r'EXAMPLE_RECURSIVE',		False),
		(r'EXCLUDE_SYMLINKS', 		False),
		(r'EXPAND_ONLY_PREDEF', 	False),
		(r'EXTERNAL_GROUPS', 		False),
		(r'EXTERNAL_PAGES', 		False),
		(r'EXTRACT_ANON_NSPACES',	False),
		(r'EXTRACT_LOCAL_CLASSES',	False),
		(r'EXTRACT_LOCAL_METHODS',	False),
		(r'EXTRACT_PACKAGE',		False),
		(r'EXTRACT_PRIV_VIRTUAL',	True),
		(r'EXTRACT_PRIVATE',		False),
		(r'EXTRACT_STATIC',			False),
		(r'FILTER_PATTERNS',		None),
		(r'FILTER_SOURCE_FILES',	False),
		(r'FILTER_SOURCE_PATTERNS',	None),
		(r'FORCE_LOCAL_INCLUDES',	False),
		(r'FULL_PATH_NAMES',		True),
		(r'GENERATE_AUTOGEN_DEF',	False),
		(r'GENERATE_BUGLIST',		False),
		(r'GENERATE_CHI',			False),
		(r'GENERATE_DEPRECATEDLIST',False),
		(r'GENERATE_DOCBOOK',		False),
		(r'GENERATE_DOCSET',		False),
		(r'GENERATE_ECLIPSEHELP',	False),
		(r'GENERATE_HTML',			False),
		(r'GENERATE_HTMLHELP',		False),
		(r'GENERATE_LATEX',			False),
		(r'GENERATE_LEGEND',		False),
		(r'GENERATE_MAN',			False),
		(r'GENERATE_PERLMOD',		False),
		(r'GENERATE_QHP',			False),
		(r'GENERATE_RTF',			False),
		(r'GENERATE_SQLITE3',		False),
		(r'GENERATE_TESTLIST',		False),
		(r'GENERATE_TODOLIST',		False),
		(r'GENERATE_TREEVIEW',		False),
		(r'GENERATE_XML',			True),
		(r'HAVE_DOT',				False),
		(r'HIDE_COMPOUND_REFERENCE',False),
		(r'HIDE_FRIEND_COMPOUNDS',	False),
		(r'HIDE_IN_BODY_DOCS',		False),
		(r'HIDE_SCOPE_NAMES',		False),
		(r'HIDE_UNDOC_CLASSES',		True),
		(r'HIDE_UNDOC_MEMBERS',		True),
		(r'HTML_EXTRA_STYLESHEET',	None),
		(r'HTML_FILE_EXTENSION',	r'.html'),
		(r'HTML_OUTPUT',			r'html'),
		(r'IDL_PROPERTY_SUPPORT',	False),
		(r'INHERIT_DOCS', 			True),
		(r'INLINE_GROUPED_CLASSES',	False),
		(r'INLINE_INFO',			True),
		(r'INLINE_INHERITED_MEMB',	True),
		(r'INLINE_SIMPLE_STRUCTS',	False),
		(r'INLINE_SOURCES',			False),
		(r'INPUT_ENCODING',			r'UTF-8'),
		(r'INPUT_FILTER',			None),
		(r'LOOKUP_CACHE_SIZE',		2),
		(r'MACRO_EXPANSION',		True),
		(r'MARKDOWN_SUPPORT',		True),
		(r'OPTIMIZE_FOR_FORTRAN',	False),
		(r'OPTIMIZE_OUTPUT_FOR_C',	False),
		(r'OPTIMIZE_OUTPUT_JAVA',	False),
		(r'OPTIMIZE_OUTPUT_SLICE',	False),
		(r'OPTIMIZE_OUTPUT_VHDL',	False),
		(r'PYTHON_DOCSTRING', 		True),
		(r'QUIET',					False),
		(r'RECURSIVE',				False),
		(r'REFERENCES_LINK_SOURCE',	False),
		(r'RESOLVE_UNNAMED_PARAMS',	True),
		(r'SEARCH_INCLUDES',		False),
		(r'SEPARATE_MEMBER_PAGES',	False),
		(r'SHORT_NAMES',			False),
		(r'SHOW_GROUPED_MEMB_INC',	False),
		(r'SHOW_USED_FILES',		False),
		(r'SIP_SUPPORT',			False),
		(r'SKIP_FUNCTION_MACROS', 	False),
		(r'SORT_BRIEF_DOCS',		False),
		(r'SORT_BY_SCOPE_NAME',		False),
		(r'SORT_GROUP_NAMES',		True),
		(r'SORT_MEMBER_DOCS',		False),
		(r'SORT_MEMBERS_CTORS_1ST',	True),
		(r'SOURCE_BROWSER',			False),
		(r'STRICT_PROTO_MATCHING',	False),
		(r'SUBGROUPING', 			True),
		(r'TAB_SIZE',				4),
		(r'TOC_INCLUDE_HEADINGS',	3),
		(r'TYPEDEF_HIDES_STRUCT',	False),
		(r'UML_LOOK',				False),
		(r'USE_HTAGS',				False),
		(r'USE_MDFILE_AS_MAINPAGE',	None),
		(r'VERBATIM_HEADERS',		False),
		(r'WARN_IF_DOC_ERROR',		True),
		(r'WARN_IF_INCOMPLETE_DOC',	True),
		(r'WARN_LOGFILE',			None),
		(r'XML_NS_MEMB_FILE_SCOPE',	True),
		(r'XML_PROGRAMLISTING',		False),
	)



def preprocess_doxyfile(context):
	assert context is not None
	assert isinstance(context, project.Context)

	with doxyfile.Doxyfile(
			doxyfile_path = context.doxyfile_path,
			cwd = context.input_dir,
			logger = context.verbose_logger,
			doxygen_path = context.doxygen_path,
			flush_at_exit = not context.dry_run
		) as df, StringIO(newline='\n') as conf_py:

		# redirect to temp dir
		df.path = Path(context.temp_dir, rf'Doxyfile')
		context.doxyfile_path = df.path
		context.verbose_value(r'Context.doxyfile_path', context.doxyfile_path)

		df.append()
		df.append(r'#---------------------------------------------------------------------------')
		df.append(r'# marzer/poxy')
		df.append(r'#---------------------------------------------------------------------------', end='\n\n')

		# apply regular doxygen settings
		if 1:

			df.append(r'# doxygen default overrides', end='\n\n') # ----------------------------------------

			global _doxygen_overrides
			for k, v in _doxygen_overrides:
				df.set_value(k, v)

			df.append()
			df.append(r'# general config', end='\n\n') # ---------------------------------------------------

			df.set_value(r'OUTPUT_DIRECTORY', context.output_dir)
			df.set_value(r'XML_OUTPUT', context.xml_dir)
			if not context.name:
				context.name = df.get_value(r'PROJECT_NAME', fallback='')
			df.set_value(r'PROJECT_NAME', context.name)

			if not context.description:
				context.description = df.get_value(r'PROJECT_BRIEF', fallback='')
			df.set_value(r'PROJECT_BRIEF', context.description)

			if context.logo is None:
				context.logo = df.get_value(r'PROJECT_LOGO', fallback=None)
				if context.logo is not None:
					context.logo = Path(str(context.logo))
					if not context.logo.is_absolute():
						context.logo = Path(context.input_dir, context.logo)
					context.logo = context.logo.resolve()
					context.verbose_value(r'Context.logo', context.logo)
			df.set_value(r'PROJECT_LOGO', context.logo)

			if context.show_includes is None:
				context.show_includes = df.get_boolean(r'SHOW_INCLUDE_FILES', fallback=True)
				context.verbose_value(r'Context.show_includes', context.show_includes)
			df.set_value(r'SHOW_INCLUDE_FILES', context.show_includes)

			if context.internal_docs is None:
				context.internal_docs = df.get_boolean(r'INTERNAL_DOCS', fallback=False)
				context.verbose_value(r'Context.internal_docs', context.internal_docs)
			df.set_value(r'INTERNAL_DOCS', context.internal_docs)
			df.add_value(r'ENABLED_SECTIONS', (r'private', r'internal') if context.internal_docs else (r'public', r'external'))

			if context.generate_tagfile is None:
				context.generate_tagfile = not (context.private_repo or context.internal_docs)
				context.verbose_value(r'Context.generate_tagfile', context.generate_tagfile)
			if context.generate_tagfile:
				context.tagfile_path = Path(context.output_dir, rf'{context.name.replace(" ","_")}.tagfile.xml' if context.name else r'tagfile.xml')
				df.set_value(r'GENERATE_TAGFILE', context.tagfile_path.name)
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
				if not context.dry_run:
					copy_file(home_md_path, home_md_temp_path, logger=context.verbose_logger)
				df.set_value(r'USE_MDFILE_AS_MAINPAGE', home_md_temp_path)

			df.append()
			df.append(r'# context.warnings', end='\n\n') # ---------------------------------------------------

			if context.warnings.enabled is None:
				context.warnings.enabled = df.get_boolean(r'WARNINGS', fallback=True)
				context.verbose_value(r'Context.warnings.enabled', context.warnings.enabled)
			df.set_value(r'WARNINGS', context.warnings.enabled)

			if context.warnings.treat_as_errors is None:
				context.warnings.treat_as_errors = df.get_boolean(r'WARN_AS_ERROR', fallback=False)
				context.verbose_value(r'Context.warnings.treat_as_errors', context.warnings.treat_as_errors)
			df.set_value(r'WARN_AS_ERROR', False) # we do this ourself

			if context.warnings.undocumented is None:
				context.warnings.undocumented = df.get_boolean(r'WARN_IF_UNDOCUMENTED', fallback=True)
				context.verbose_value(r'Context.warnings.undocumented', context.warnings.undocumented)
			df.set_value(r'WARN_IF_UNDOCUMENTED', context.warnings.undocumented)

			df.append()
			df.append(r'# context.sources', end='\n\n') # ----------------------------------------------------

			df.add_value(r'INPUT', context.sources.paths)
			df.set_value(r'FILE_PATTERNS', context.sources.patterns)
			df.add_value(r'EXCLUDE', context.html_dir)
			df.add_value(r'STRIP_FROM_PATH', context.sources.strip_paths)

			if context.sources.extract_all is None:
				context.sources.extract_all = df.get_boolean(r'EXTRACT_ALL', fallback=False)
				context.verbose_value(r'Context.sources.extract_all', context.sources.extract_all)
			df.set_value(r'EXTRACT_ALL', context.sources.extract_all)

			df.append()
			df.append(r'# context.examples', end='\n\n') # ----------------------------------------------------

			df.add_value(r'EXAMPLE_PATH', context.examples.paths)
			df.set_value(r'EXAMPLE_PATTERNS', context.examples.patterns)

			if context.images.paths: # ----------------------------------------------------
				df.append()
				df.append(r'# context.images', end='\n\n')
				df.add_value(r'IMAGE_PATH', context.images.paths)

			if context.tagfiles: # ----------------------------------------------------
				df.append()
				df.append(r'# context.tagfiles', end='\n\n')
				df.add_value(r'TAGFILES', [rf'{file}={dest}' for _,(file, dest) in context.tagfiles.items()])

			if context.aliases: # ----------------------------------------------------
				df.append()
				df.append(r'# context.aliases', end='\n\n')
				df.add_value(r'ALIASES', [rf'{k}={v}' for k,v in context.aliases.items()])

			if context.macros: # ----------------------------------------------------
				df.append()
				df.append(r'# context.macros', end='\n\n')
				df.add_value(r'PREDEFINED', [rf'{k}={v}' for k,v in context.macros.items()])

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


		# build m.css conf.py
		if 1:
			conf = lambda s='', end='\n': print(reindent(s, indent=''), file=conf_py, end=end)
			conf(rf"DOXYFILE = r'{context.doxyfile_path}'")
			conf(r"STYLESHEETS = []") # suppress the default behaviour
			conf(rf'HTML_HEADER = """{html_header}"""')
			if context.theme == r'dark':
				conf(r"THEME_COLOR = '#22272e'")
			elif context.theme == r'light':
				conf(r"THEME_COLOR = '#cb4b16'")
			if not df.contains(r'M_FAVICON'):
				if context.favicon:
					conf(rf"FAVICON = r'{context.favicon}'")
				elif context.theme == r'dark':
					conf(rf"FAVICON = 'favicon-dark.png'")
				elif context.theme == r'light':
					conf(rf"FAVICON = 'favicon-light.png'")
			if not df.contains(r'M_SHOW_UNDOCUMENTED'):
				conf(rf'SHOW_UNDOCUMENTED = {context.sources.extract_all}')
			if not df.contains(r'M_CLASS_TREE_EXPAND_LEVELS'):
				conf(r'CLASS_INDEX_EXPAND_LEVELS = 3')
			if not df.contains(r'M_FILE_TREE_EXPAND_LEVELS'):
				conf(r'FILE_INDEX_EXPAND_LEVELS = 3')
			if not df.contains(r'M_EXPAND_INNER_TYPES'):
				conf(r'CLASS_INDEX_EXPAND_INNER = True')
			if not df.contains(r'M_SEARCH_DOWNLOAD_BINARY'):
				conf(r'SEARCH_DOWNLOAD_BINARY = False')
			if not df.contains(r'M_SEARCH_DISABLED'):
				conf(r'SEARCH_DISABLED = False')
			if not df.contains(r'M_LINKS_NAVBAR1') and not df.contains(r'M_LINKS_NAVBAR2'):
				navbars = ([],[])
				if context.navbar:
					bar = [v for v in context.navbar]
					for i in range(len(bar)):
						if bar[i] == r'github':
							bar[i] = (rf'<a target="_blank" href="https://github.com/{context.github}/" class="poxy-icon github">{read_all_text_from_file(Path(context.data_dir, "poxy-icon-github.svg"), logger=context.verbose_logger)}</a>', [])
						elif bar[i] == r'theme':
							bar[i] = (rf'<a id="poxy-theme-switch" href="#poxy-theme-switch" class="poxy-icon theme" onClick="toggle_theme();">{read_all_text_from_file(Path(context.data_dir, "poxy-icon-theme.svg"), logger=context.verbose_logger)}</a>', [])
					bar = [b for b in bar if b is not None]
					split = min(max(int(len(bar)/2) + len(bar)%2, 2), len(bar))
					for b, i in ((bar[:split], 0), (bar[split:], 1)):
						for j in range(len(b)):
							if isinstance(b[j], tuple):
								navbars[i].append(b[j])
							else:
								navbars[i].append((None, b[j], []))
				for i in (0, 1):
					if navbars[i]:
						conf(f'LINKS_NAVBAR{i+1} = [\n\t', end='')
						conf(',\n\t'.join([rf'{b}' for b in navbars[i]]))
						conf(r']')
					else:
						conf(rf'LINKS_NAVBAR{i+1} = []')
			if not df.contains(r'M_PAGE_FINE_PRINT'):
				conf(r"FINE_PRINT = r'''")
				footer = []
				if context.github:
					footer.append(rf'<a href="https://github.com/{context.github}/">Github</a>')
					footer.append(rf'<a href="https://github.com/{context.github}/issues">Report an issue</a>')
				if context.changelog:
					footer.append(rf'<a href="md_poxy_changelog.html">Changelog</a>')
				if context.license and context.license[r'uri']:
					footer.append(rf'<a href="{context.license["uri"]}" target="_blank">License</a>')
				if context.generate_tagfile:
					footer.append(rf'<a href="{context.tagfile_path.name}" target="_blank" type="text/xml" download>Doxygen tagfile</a>')
				if footer:
					for i in range(1, len(footer)):
						footer[i] = r' &bull; ' + footer[i]
					footer.append(r'<br><br>')
				footer.append(r'Site generated using <a href="https://github.com/marzer/poxy/">Poxy</a>')
				for i in range(len(footer)):
					conf(rf"    {footer[i]}")
				conf(r"'''")

		conf_py_text = conf_py.getvalue()

		# write conf.py
		if not context.dry_run:
			context.verbose(rf'Writing {context.mcss_conf_path}')
			with open(context.mcss_conf_path, r'w', encoding=r'utf-8', newline='\n') as f:
				f.write(conf_py_text)

		# clean and debug dump final doxyfile
		df.cleanup()
		if context.dry_run:
			context.info(r'#====================================================================================')
			context.info(rf'# generated by Poxy v{context.version_string}')
			context.info(r'#====================================================================================')
			context.info(df.get_text())
			context.info(r'## ---------------------------------------------------------------------------------')
			context.info(r'## m.css conf.py:')
			context.info(r'## ---------------------------------------------------------------------------------')
			context.info(conf_py_text, indent='## ')
			context.info(r'#====================================================================================')
		else:
			context.verbose(r'Effective Doxyfile:')
			context.verbose(df.get_text(), indent=r'    ')
			context.verbose(r'    ## --------------------------------------------------------------------------')
			context.verbose(r'    ## m.css conf.py:')
			context.verbose(r'    ## --------------------------------------------------------------------------')
			context.verbose(conf_py_text, indent='## ')



def postprocess_xml(context):
	assert context is not None
	assert isinstance(context, project.Context)

	xml_files = get_all_files(context.xml_dir, any=(r'*.xml'))
	if not xml_files:
		return

	with ScopeTimer(rf'Post-processing {len(xml_files) + len(context.tagfiles)} XML files', print_start=True, print_end=context.verbose_logger):

		pretty_print_xml = False
		xml_parser = etree.XMLParser(
			encoding='utf-8',
			remove_blank_text=pretty_print_xml,
			recover=True,
			remove_comments=True,
			ns_clean=True
		)
		write_xml_to_file = lambda xml, f: xml.write(str(f), encoding='utf-8', xml_declaration=True, pretty_print=pretty_print_xml)

		inline_namespace_ids = None
		if context.inline_namespaces:
			inline_namespace_ids = [f'namespace{doxyfile.mangle_name(ns)}' for ns in context.inline_namespaces]

		implementation_header_data = None
		implementation_header_mappings = None
		implementation_header_innernamespaces = None
		implementation_header_sectiondefs = None
		implementation_header_unused_keys = None
		implementation_header_unused_values = None
		if context.implementation_headers:
			implementation_header_data = [
				(
					hp,
					os.path.basename(hp),
					doxyfile.mangle_name(os.path.basename(hp)),
					[(i, os.path.basename(i), doxyfile.mangle_name(os.path.basename(i))) for i in impl]
				)
				for hp, impl in context.implementation_headers
			]
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

		# process xml files
		if 1:

			# pre-pass to delete junk files
			if 1:
				# 'file' entries for markdown and dox files
				dox_files = [rf'*{doxyfile.mangle_name(ext)}.xml' for ext in (r'.dox', r'.md')]
				dox_files.append(r'md_home.xml')
				for xml_file in get_all_files(context.xml_dir, any=dox_files):
					delete_file(xml_file, logger=context.verbose_logger)

				# 'dir' entries for empty directories
				deleted = True
				while deleted:
					deleted = False
					for xml_file in get_all_files(context.xml_dir, all=(r'dir*.xml')):
						xml = etree.parse(str(xml_file), parser=xml_parser)
						compounddef = xml.getroot().find(r'compounddef')
						if compounddef is None or compounddef.get(r'kind') != r'dir':
							continue
						existing_inners = 0
						for subtype in (r'innerfile', r'innerdir'):
							for inner in compounddef.findall(subtype):
								ref_file = Path(context.xml_dir, rf'{inner.get(r"refid")}.xml')
								if ref_file.exists():
									existing_inners = existing_inners + 1
						if not existing_inners:
							delete_file(xml_file, logger=context.verbose_logger)
							deleted = True

				# concepts - not currently supported by m.css
				if not context.xml_only:
					for xml_file in get_all_files(context.xml_dir, all=(r'concept*.xml')):
						xml = etree.parse(str(xml_file), parser=xml_parser)
						compounddef = xml.getroot().find(r'compounddef')
						if compounddef is None or compounddef.get(r'kind') != r'concept':
							continue
						compoundname = compounddef.find(r'compoundname')
						assert compoundname is not None
						assert compoundname.text
						context.warning(
							rf"C++20 concepts are not currently supported! No documentation will be generated for '{compoundname.text}'."
							+ r" Surround your concepts in a '@cond poxy_supports_concepts' block to suppress this warning until"
							+ r" poxy is updated to support them.")
						delete_file(xml_file, logger=context.verbose_logger)

			extracted_implementation = False
			tentative_macros = regex_or(context.code_blocks.macros)
			macros = set()
			cpp_tree = CppTree()
			xml_files = get_all_files(context.xml_dir, any=(r'*.xml'))
			tagfiles = [f for _,(f,_) in context.tagfiles.items()]
			xml_files = xml_files + tagfiles
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
					for compound in [tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'file', r'dir', r'concept')]:
						ref_file = Path(context.xml_dir, rf'{compound.get(r"refid")}.xml')
						if not ref_file.exists():
							root.remove(compound)
							changed = True

					# extract namespaces, types and enum values for syntax highlighting
					scopes = [tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union')]
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

					# enumerate all compound pages and their types for use later in the HTML post-process
					pages = {}
					for tag in root.findall(r'compound'):
						refid = tag.get(r'refid')
						filename = refid
						if filename == r'indexpage':
							filename = r'index'
						filename = filename + r'.html'
						pages[filename] = { r'kind' : tag.get(r'kind'), r'name' : tag.find(r'name').text, r'refid' : refid }
					context.__dict__[r'compound_pages'] = pages
					context.verbose_value(r'Context.compound_pages', pages)

				# a tag file
				elif root.tag == r'tagfile':
					for compound in [tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union')]:

						compound_name = compound.find(r'name').text
						if compound_name.find(r'<') != -1:
							continue

						compound_type = compound.get(r'kind')
						if compound_type in (r'class', r'struct', r'union'):
							cpp_tree.add_type(compound_name)
						else:
							cpp_tree.add_namespace(compound_name)

						for member in [tag for tag in compound.findall(r'member') if tag.get(r'kind') in (r'namespace', r'class', r'struct', r'union')]:

							member_name = member.find(r'name').text
							if member_name.find(r'<') != -1:
								continue

							member_type = member.get(r'kind')
							if member_type in (r'class', r'struct', r'union'):
								cpp_tree.add_type(compound_name)
							else:
								cpp_tree.add_namespace(compound_name)

				# some other compound definition
				else:
					compounddef = root.find(r'compounddef')
					if compounddef is None:
						context.warning(rf'{xml_file} did not contain a <compounddef>!')
						continue
					compoundname = compounddef.find(r'compoundname')
					assert compoundname is not None
					assert compoundname.text

					if compounddef.get(r'kind') in (r'namespace', r'class', r'struct', r'union', r'enum', r'file', r'group'):

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
							for i in range(len(members)-1, 0, -1):
								for j in range(i):
									if members[i].get(r'id') == members[j].get(r'id'):
										section.remove(members[i])
										changed = True
										break

							# fix functions where keywords like 'friend' have been erroneously included in the return type
							if 1:
								members = [m for m in section.findall(r'memberdef') if m.get(r'kind') in (r'friend', r'function')]
								attribute_keywords = (
									(r'constexpr', r'constexpr', r'yes'),
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
											if type.text == kw: # constructors
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
								groups = [
									([tag for tag in members if tag.get(r'kind') == r'define'], True),
									([tag for tag in members if tag.get(r'kind') == r'typedef'], True),
									([tag for tag in members if tag.get(r'kind') == r'enum'], True),
									([tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'yes'], True),
									(
										[tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'no'],
										compounddef.get(r'kind') not in (r'class', r'struct', r'union')
									),
									([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'yes'], True),
									([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'no'], True),
									([tag for tag in members if tag.get(r'kind') == r'friend'], True)
								]
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
					if compounddef.get(r'kind') == r'namespace':

						# set inline namespaces
						if context.inline_namespaces:
							for nsid in inline_namespace_ids:
								if compounddef.get(r'id') == nsid:
									compounddef.set(r'inline', r'yes')
									changed = True
									break

					# dirs
					if compounddef.get(r'kind') == r'dir':

						# remove implementation headers
						if context.implementation_headers:
							for innerfile in compounddef.findall(r'innerfile'):
								if innerfile.get(r'refid') in implementation_header_mappings:
									compounddef.remove(innerfile)
									changed = True

					# files
					if compounddef.get(r'kind') == r'file':

						# simplify the XML by removing junk not used by mcss
						if not context.xml_only:
							for tag in (r'includes', r'includedby', r'incdepgraph', r'invincdepgraph'):
								for t in compounddef.findall(tag):
									compounddef.remove(t)
									changed = True

						# get any macros for the syntax highlighter
						for sectiondef in [tag for tag in compounddef.findall(r'sectiondef') if tag.get(r'kind') == r'define']:
							for memberdef in [tag for tag in sectiondef.findall(r'memberdef') if tag.get(r'kind') == r'define']:
								macro = memberdef.find(r'name').text
								if not tentative_macros.fullmatch(macro):
									macros.add(macro)

						# rip the good bits out of implementation headers
						if context.implementation_headers:
							iid = compounddef.get(r'id')
							if iid in implementation_header_mappings:
								hid = implementation_header_mappings[iid][2]
								innernamespaces = compounddef.findall(r'innernamespace')
								if innernamespaces:
									implementation_header_innernamespaces[hid] = implementation_header_innernamespaces[hid] + innernamespaces
									extracted_implementation = True
									if iid in implementation_header_unused_values:
										del implementation_header_unused_values[iid]
									for tag in innernamespaces:
										compounddef.remove(tag)
										changed = True
								sectiondefs = compounddef.findall(r'sectiondef')
								if sectiondefs:
									implementation_header_sectiondefs[hid] = implementation_header_sectiondefs[hid] + sectiondefs
									extracted_implementation = True
									if iid in implementation_header_unused_values:
										del implementation_header_unused_values[iid]
									for tag in sectiondefs:
										compounddef.remove(tag)
										changed = True

					# groups and namespaces
					if compounddef.get(r'kind') in (r'group', r'namespace'):

						# fix inner(class|namespace|group) sorting
						inners = [tag for tag in compounddef.iterchildren() if tag.tag.startswith(r'inner')]
						if inners:
							changed = True
							for tag in inners:
								compounddef.remove(tag)
							inners.sort(key=lambda tag: tag.text)
							for tag in inners:
								compounddef.append(tag)

				if changed:
					write_xml_to_file(xml, xml_file)

			# add to syntax highlighter
			context.code_blocks.namespaces.add(cpp_tree.matcher(CppTree.NAMESPACES))
			context.code_blocks.types.add(cpp_tree.matcher(CppTree.TYPES))
			context.code_blocks.enums.add(cpp_tree.matcher(CppTree.ENUM_VALUES))
			for macro in macros:
				context.code_blocks.macros.add(macro)

			# merge extracted implementations
			if extracted_implementation:
				for (hp, hfn, hid, impl) in implementation_header_data:
					xml_file = Path(context.xml_dir, rf'{hid}.xml')
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
					delete_file(Path(context.xml_dir, rf'{iid}.xml'), logger=context.verbose_logger)

		# scan through the files and substitute impl header ids and paths as appropriate
		if 1 and context.implementation_headers:
			xml_files = get_all_files(context.xml_dir, any=('*.xml'))
			for xml_file in xml_files:
				context.verbose(rf"Re-linking implementation headers in '{xml_file}'")
				xml_text = read_all_text_from_file(xml_file, logger=context.verbose_logger)
				for (hp, hfn, hid, impl) in implementation_header_data:
					for (ip, ifn, iid) in impl:
						#xml_text = xml_text.replace(f'refid="{iid}"',f'refid="{hid}"')
						xml_text = xml_text.replace(rf'compoundref="{iid}"',f'compoundref="{hid}"')
						xml_text = xml_text.replace(ip,hp)
				with BytesIO(bytes(xml_text, 'utf-8')) as b:
					xml = etree.parse(b, parser=xml_parser)
					write_xml_to_file(xml, xml_file)



_worker_context = None
def _initialize_worker(context):
	global _worker_context
	_worker_context = context



def postprocess_html_file(path, context=None):
	assert path is not None
	assert isinstance(path, Path)
	assert path.is_absolute()
	assert path.exists()

	if context is None:
		global _worker_context
		context = _worker_context
	assert context is not None
	assert isinstance(context, project.Context)

	context.info(rf'Post-processing {path}')
	changed = False
	try:
		for fix in context.fixers:
			if isinstance(fix, fixers.HTMLFixer):
				doc = soup.HTMLDocument(path, logger=context.verbose_logger)
				if fix(doc, context):
					doc.smooth()
					doc.flush()
					changed = True
			elif isinstance(fix, fixers.PlainTextFixer):
				doc = [ read_all_text_from_file(path, logger=context.verbose_logger), path ]
				if fix(doc, context):
					context.verbose(rf'Writing {path}')
					with open(path, 'w', encoding='utf-8', newline='\n') as f:
						f.write(doc[0])
					changed = True

	except Exception as e:
		context.info(rf'{type(e).__name__} raised while post-processing {path}')
		raise
	except:
		context.info(rf'Error occurred while post-processing {path}')
		raise

	return changed



def postprocess_html(context):
	assert context is not None
	assert isinstance(context, project.Context)

	files = filter_filenames(
		get_all_files(context.html_dir, any=('*.html', '*.htm')),
		context.html_include,
		context.html_exclude
	)
	if not files:
		return

	threads = min(len(files), context.threads, 8) # diminishing returns after 8

	with ScopeTimer(rf'Post-processing {len(files)} HTML files', print_start=True, print_end=context.verbose_logger):
		context.fixers = (
			fixers.MarkTOC(),
			fixers.CodeBlocks(),
			fixers.Banner(),
			fixers.Modifiers1(),
			fixers.Modifiers2(),
			fixers.TemplateTemplate(),
			fixers.StripIncludes(),
			fixers.AutoDocLinks(),
			fixers.Links(),
			fixers.CustomTags(),
			fixers.EmptyTags(),
			fixers.ImplementationDetails(),
			fixers.MarkdownPages(),
		)
		context.verbose(rf'Post-processing {len(files)} HTML files...')
		if threads > 1:
			with futures.ProcessPoolExecutor(max_workers=threads, initializer=_initialize_worker, initargs=(context,)) as executor:
				jobs = [ executor.submit(postprocess_html_file, file) for file in files ]
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
	return {
		r'stdout' : stdout.read().strip(),
		r'stderr' : stderr.read().strip()
	}



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
_warnings_trim_suffixes = (
	r'Skipping it...',
)
_warnings_substitutions = (
	(r'does not exist or is not a file', r'did not exist or was not a file'),
)
_warnings_ignored = (
	r'inline code has multiple lines, fallback to a code block',
	r'libgs not found'
)
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



__all__.append(r'run')
def run(config_path='.',
		output_dir='.',
		threads=-1,
		cleanup=True,
		verbose=False,
		mcss_dir=None,
		doxygen_path=None,
		logger=None,
		dry_run=False,
		xml_only=False,
		html_include=None,
		html_exclude=None,
		treat_warnings_as_errors=None,
		theme=None
	):

	with project.Context(
		config_path = config_path,
		output_dir = output_dir,
		threads = threads,
		cleanup = cleanup,
		verbose = verbose,
		mcss_dir = mcss_dir,
		doxygen_path = doxygen_path,
		logger = logger,
		dry_run = dry_run,
		xml_only = xml_only,
		html_include = html_include,
		html_exclude = html_exclude,
		treat_warnings_as_errors = treat_warnings_as_errors,
		theme=theme
	) as context:

		# preprocess the doxyfile
		preprocess_doxyfile(context)
		context.verbose_object(r'Context.warnings', context.warnings)

		if context.dry_run:
			return

		# resolve any uri tagfiles
		if context.unresolved_tagfiles:
			with ScopeTimer(r'Resolving remote tagfiles', print_start=True, print_end=context.verbose_logger) as t:
				for source, (file, _) in context.tagfiles.items():
					if file.exists() or not is_uri(source):
						continue
					context.verbose(rf'Downloading {source} => {file}')
					response = requests.get(
						source,
						allow_redirects=True,
						stream=False,
						timeout=30
					)
					context.verbose(rf'Writing {file}')
					with open(file, 'w', encoding='utf-8', newline='\n') as f:
						f.write(response.text)

		make_temp_file = lambda: tempfile.SpooledTemporaryFile(mode='w+', newline='\n', encoding='utf-8')

		# precondition the change log page (at this point it is already a temp copy)
		if context.changelog:
			text = read_all_text_from_file(context.changelog, logger=context.verbose_logger).strip()
			text = text.replace('\r\n', 			'\n')
			text = re.sub(r'\n<br[ \t]*/?><br[ \t]*/?>\n',	r'', text)
			if context.github:
				text = re.sub(r'#([0-9]+)', 		rf'[#\1](https://github.com/{context.github}/issues/\1)', text)
				text = re.sub(r'@([a-zA-Z0-9_-]+)',	rf'[@\1](https://github.com/\1)', text)
			text = text.replace(r'&amp;',			r'__poxy_thiswasan_amp')
			text = text.replace(r'&#xFE0F;', 		r'__poxy_thiswasan_fe0f')
			text = text.replace(r'@',				r'__poxy_thiswasan_at')
			if text.find(r'@tableofcontents') == -1 and text.find('\\tableofcontents') == -1 and text.find(r'[TOC]') == -1:
				#text = f'[TOC]\n\n{text}'
				nlnl = text.find(r'\n\n')
				if nlnl != -1:
					text = f'{text[:nlnl]}\n\n\\tableofcontents\n\n{text[nlnl:]}'
				pass
			text += '\n\n'
			with open(context.changelog, r'w', encoding=r'utf-8', newline='\n') as f:
				f.write(text)

		# run doxygen to generate the xml
		if 1:
			with ScopeTimer(r'Generating XML files with Doxygen', print_start=True, print_end=context.verbose_logger) as t:
				with make_temp_file() as stdout, make_temp_file() as stderr:
					try:
						subprocess.run(
							[str(context.doxygen_path), str(context.doxyfile_path)],
							check=True,
							stdout=stdout,
							stderr=stderr,
							cwd=context.input_dir
						)
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
				if context.tagfile_path is not None and context.tagfile_path.exists():
					text = read_all_text_from_file(context.tagfile_path, logger=context.verbose_logger)
					text = re.sub(r'\n\s*?<path>.+?</path>\s*?\n', '\n', text, re.S)
					context.verbose(rf'Writing {context.tagfile_path}')
					with open(context.tagfile_path, 'w', encoding='utf-8', newline='\n') as f:
						f.write(text)

		# post-process xml files
		if 1:
			postprocess_xml(context)

		if context.xml_only:
			return

		context.verbose_object(r'Context.code_blocks', context.code_blocks)

		# compile regexes
		# (done here because doxygen and xml preprocessing adds additional values to these lists)
		context.code_blocks.namespaces = regex_or(context.code_blocks.namespaces, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
		context.code_blocks.types = regex_or(context.code_blocks.types, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
		context.code_blocks.enums = regex_or(context.code_blocks.enums, pattern_prefix='(?:::)?')
		context.code_blocks.string_literals = regex_or(context.code_blocks.string_literals)
		context.code_blocks.numeric_literals = regex_or(context.code_blocks.numeric_literals)
		context.code_blocks.macros = regex_or(context.code_blocks.macros)
		context.autolinks = tuple([(re.compile('(?<![a-zA-Z_])' + expr + '(?![a-zA-Z_])'), uri) for expr, uri in context.autolinks])

		# run m.css to generate the html
		if 1:
			with ScopeTimer(r'Generating HTML files with m.css', print_start=True, print_end=context.verbose_logger) as t:
				with make_temp_file() as stdout, make_temp_file() as stderr:
					doxy_args = [str(context.mcss_conf_path), r'--no-doxygen', r'--sort-globbed-files']
					if context.is_verbose():
						doxy_args.append(r'--debug')
					try:
						run_python_script(
							Path(context.mcss_dir, r'documentation/doxygen.py'),
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

		# copy extra_files
		with ScopeTimer(r'Copying extra_files', print_start=True, print_end=context.verbose_logger) as t:
			for dest_name, source_path in context.extra_files.items():
				dest_path = Path(context.html_dir, dest_name).resolve()
				dest_path.parent.mkdir(exist_ok=True)
				copy_file(source_path, dest_path, logger=context.verbose_logger)

		# copy fonts
		with ScopeTimer(r'Copying fonts', print_start=True, print_end=context.verbose_logger) as t:
			copy_tree(str(Path(find_generated_dir(), r'fonts')), str(Path(context.assets_dir, r'fonts')))

		# move the tagfile into the html directory
		if context.generate_tagfile:
			if context.tagfile_path.exists():
				move_file(context.tagfile_path, Path(context.output_dir, r'html'), logger=context.verbose_logger)
			else:
				context.warning(rf'Doxygen tagfile {context.tagfile_path} not found!')

		# post-process html files
		if 1:
			postprocess_html(context)
