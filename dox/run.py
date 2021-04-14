#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

try:
	from dox.utils import *
	import dox.project as project
	import dox.doxygen as doxygen
	import dox.soup as soup
	import dox.fixers as fixers
except:
	from utils import *
	import project
	import doxygen
	import soup
	import fixers

import sys
import os
import re
import subprocess
import concurrent.futures as futures
import argparse
from lxml import etree
from io import BytesIO
from pathlib import Path



#=======================================================================================================================
# PRE/POST PROCESSORS
#=======================================================================================================================

__doxygen_overrides  = (
		(r'ALLOW_UNICODE_NAMES',	False),
		(r'AUTOLINK_SUPPORT',		True),
		(r'CLASS_DIAGRAMS',			False),
		(r'CPP_CLI_SUPPORT',		False),
		(r'CREATE_SUBDIRS',			False),
		(r'DOXYFILE_ENCODING',		r'UTF-8'),
		(r'ENABLE_PREPROCESSING',	True),
		(r'EXPAND_ONLY_PREDEF', 	False),
		(r'EXTRACT_ANON_NSPACES',	False),
		(r'EXTRACT_LOCAL_CLASSES',	False),
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
		(r'GENERATE_TESTLIST',		False),
		(r'GENERATE_TODOLIST',		False),
		(r'GENERATE_TREEVIEW',		False),
		(r'GENERATE_XML',			True),
		(r'HIDE_UNDOC_CLASSES',		True),
		(r'HIDE_UNDOC_MEMBERS',		True),
		(r'HTML_FILE_EXTENSION',	r'.html'),
		(r'HTML_OUTPUT',			r'html'),
		(r'IDL_PROPERTY_SUPPORT',	False),
		(r'INLINE_INHERITED_MEMB',	True),
		(r'INPUT_ENCODING',			r'UTF-8'),
		(r'LOOKUP_CACHE_SIZE',		2),
		(r'MACRO_EXPANSION',		True),
		(r'MARKDOWN_SUPPORT',		True),
		(r'OPTIMIZE_FOR_FORTRAN',	False),
		(r'OPTIMIZE_OUTPUT_FOR_C',	False),
		(r'OPTIMIZE_OUTPUT_JAVA',	False),
		(r'OPTIMIZE_OUTPUT_SLICE',	False),
		(r'OPTIMIZE_OUTPUT_VHDL',	False),
		(r'RESOLVE_UNNAMED_PARAMS',	True),
		(r'SHORT_NAMES',			False),
		(r'SIP_SUPPORT',			False),
		(r'SKIP_FUNCTION_MACROS', 	False),
		(r'SORT_BRIEF_DOCS',		False),
		(r'SORT_BY_SCOPE_NAME',		True),
		(r'SORT_GROUP_NAMES',		True),
		(r'SORT_MEMBER_DOCS',		False),
		(r'SORT_MEMBERS_CTORS_1ST',	True),
		(r'SOURCE_BROWSER',			False),
		(r'TAB_SIZE',				4),
		(r'TYPEDEF_HIDES_STRUCT',	False),
		(r'WARN_IF_DOC_ERROR',		True),
		(r'WARN_IF_INCOMPLETE_DOC',	True),
		(r'WARN_LOGFILE',			''),
		(r'XML_NS_MEMB_FILE_SCOPE',	True),
		(r'XML_OUTPUT',				r'xml'),
		(r'XML_PROGRAMLISTING',		False),
	)



def __preprocess_doxyfile(context):
	assert context is not None
	assert isinstance(context, project.Context)
	
	with doxygen.Doxyfile(
			doxyfile_path=context.doxyfile_path,
			cwd=context.input_dir) as df:

		df.append()
		df.append(r'#---------------------------------------------------------------------------')
		df.append(r'# marzer/dox')
		df.append(r'#---------------------------------------------------------------------------')

		# apply regular doxygen settings
		if 1:
			if not context.name:
				context.name = df.get_value(r'PROJECT_NAME', fallback='')
			df.set_value(r'PROJECT_NAME', context.name)

			if not context.description:
				context.description = df.get_value(r'PROJECT_BRIEF', fallback='')
			df.set_value(r'PROJECT_BRIEF', context.description)

			df.set_value(r'OUTPUT_DIRECTORY', context.output_dir)

			if context.show_includes is None:
				context.show_includes = df.get_boolean(r'SHOW_INCLUDE_FILES', fallback=True)
			df.set_value(r'SHOW_INCLUDE_FILES', context.show_includes)

			if context.warnings.enabled is None:
				context.warnings.enabled = df.get_boolean(r'WARNINGS', fallback=True)
			df.set_value(r'WARNINGS', context.warnings.enabled)

			if context.warnings.treat_as_errors is None:
				context.warnings.treat_as_errors = df.get_boolean(r'WARN_AS_ERROR', fallback=False)
			df.set_value(r'WARN_AS_ERROR', context.warnings.treat_as_errors)

			if context.warnings.undocumented is None:
				context.warnings.undocumented = df.get_boolean(r'WARN_IF_UNDOCUMENTED', fallback=True)
			df.set_value(r'WARN_IF_UNDOCUMENTED', context.warnings.undocumented)

			if context.generate_tagfile:
				context.tagfile_path = Path(context.output_dir, rf'{context.name.replace(" ","_")}.tagfile.xml' if context.name else r'tagfile.xml')
				df.set_value(r'GENERATE_TAGFILE', context.tagfile_path)
			else:
				df.set_value(r'GENERATE_TAGFILE')

			global __doxygen_overrides
			df.append()
			for k, v in __doxygen_overrides:
				df.set_value(k, v)
			df.set_value(r'NUM_PROC_THREADS', context.threads)
			df.add_value(r'CLANG_OPTIONS', rf'-std=c++{context.cpp%100}')
			df.add_value(r'CLANG_OPTIONS', r'-Wno-everything')

			df.append()
			df.add_value(r'TAGFILES', [rf'{k}={v}' for k,v in context.tagfiles.items()])

			df.append()
			df.add_value(r'ALIASES', [rf'{k}={v}' for k,v in context.aliases.items()])

			df.append()
			df.add_value(r'PREDEFINED', [rf'{k}={v}' for k,v in context.defines.items()])

		# apply m.css stuff
		if 1:
			df.append()
			df.append(r'##!')
			if not df.contains(r'M_LINKS_NAVBAR1') and not df.contains(r'M_LINKS_NAVBAR2'):
				if context.navbar:
					bar = [v for v in context.navbar]
					for i in range(len(bar)):
						if bar[i] == 'github':
							bar[i] = rf'"<a target=\"_blank\" href=\"https://github.com/{context.github}/\" class=\"github\">Github</a>"'
					split = min(max(int(len(bar)/2) + len(bar)%2, 2), len(bar))
					for b, i in ((bar[:split], 1), (bar[split:], 2)):
						if b:
							df.append(rf'##! M_LINKS_NAVBAR{i}            = ''\\')
							for j in range(len(b)):
								df.append(rf'##!     {b[j]}' + (' \\' if j+1 < len(b) else ''))
						else:
							df.append(rf'##! M_LINKS_NAVBAR{i}            = ')
						df.append(r'##!')
				else:
					df.append(r'##! M_LINKS_NAVBAR1            = ')
					df.append(r'##! M_LINKS_NAVBAR2            = ')
					df.append(r'##!')
			if not df.contains(r'M_CLASS_TREE_EXPAND_LEVELS'):
				df.append(r'##! M_CLASS_TREE_EXPAND_LEVELS = 3')
				df.append(r'##!')
			if not df.contains(r'M_FILE_TREE_EXPAND_LEVELS'):
				df.append(r'##! M_FILE_TREE_EXPAND_LEVELS  = 3')
				df.append(r'##!')
			if not df.contains(r'M_SEARCH_DOWNLOAD_BINARY'):
				df.append(r'##! M_SEARCH_DOWNLOAD_BINARY   = NO')
				df.append(r'##!')
			if not df.contains(r'M_FAVICON'):
				df.append(rf'##! M_FAVICON   = "{context.favicon if context.favicon is not None else ""}"')
				df.append(r'##!')
			if not df.contains(r'M_HTML_HEADER'):
				df.append(r'##! M_HTML_HEADER              = ''\\')
				for k, v in context.meta.items():
					df.append(rf'##!    <meta name="{k}" content="{v}"> ''\\')
				df.append(r'##!    <link href="dox.css" rel="stylesheet"/>')
				df.append(r'##!')
			if not df.contains(r'M_PAGE_FINE_PRINT'):
				df.append(r'##! M_PAGE_FINE_PRINT          = ''\\')
				top_row = []
				if context.github:
					top_row.append(rf'<a href="https://github.com/{context.github}/">Github</a>')
					top_row.append(rf'<a href="https://github.com/{context.github}/issues">Report an issue</a>')
				if context.generate_tagfile:
					top_row.append(rf'<a href="{context.tagfile_path.name}" target="_blank">Doxygen tagfile</a>')
				if top_row:
					for i in range(len(top_row)):
						df.append(rf'##!     {" &bull; " if i else ""}{top_row[i]} ''\\')
					df.append(r'##!     <br><br> ''\\')
				df.append(r'##!     Documentation created using ''\\')
				df.append(r'##!     <a href="https://www.doxygen.nl/index.html">Doxygen</a> ''\\')
				df.append(r'##!     + <a href="https://mcss.mosra.cz/documentation/doxygen/">mosra/m.css</a> ''\\')
				df.append(r'##!     + <a href="https://github.com/marzer/dox/">marzer/dox</a>')
				df.append(r'##!')

		# move to a temp file path
		if context.temp_file_name:
			df.path = Path(context.output_dir, context.temp_file_name)
		else:
			df.path = Path(context.output_dir, df.path.name + rf'.{df.hash()}.temp')
		context.doxyfile_path = df.path
		context.verbose_value(r'Context.doxyfile_path', context.doxyfile_path)



def __preprocess_xml(context):
	assert context is not None
	assert isinstance(context, project.Context)

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
		inline_namespace_ids = [f'namespace{doxygen.mangle_name(ns)}' for ns in context.inline_namespaces]

	implementation_header_data = None
	implementation_header_mappings = None
	implementation_header_innernamespaces = None
	implementation_header_sectiondefs = None
	if context.implementation_headers:
		implementation_header_data = [
			(
				hp,
				os.path.basename(hp),
				doxygen.mangle_name(os.path.basename(hp)),
				[(i, os.path.basename(i), doxygen.mangle_name(os.path.basename(i))) for i in impl]
			)
			for hp, impl in context.implementation_headers
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
		xml_files = get_all_files(context.xml_dir, any=('*.xml'))
		tentative_macros = regex_or(context.highlighting.macros)
		macros = set()
		cpp_tree = CppTree()
		for xml_file in xml_files:
			print(f'Pre-processing {xml_file}')
			xml = etree.parse(str(xml_file), parser=xml_parser)
			changed = False

			# the doxygen index
			if xml.getroot().tag == 'doxygenindex':
				# extract namespaces, types and enum values for syntax highlighting
				scopes = [tag for tag in xml.getroot().findall('compound') if tag.get('kind') in ('namespace', 'class', 'struct', 'union')]
				for scope in scopes:
					scope_name = scope.find('name').text

					# skip template members because they'll break the regex matchers
					if scope_name.find('<') != -1:
						continue

					# regular types and namespaces
					if scope.get('kind') in ('class', 'struct', 'union'):
						cpp_tree.add_type(scope_name)
					elif scope.get('kind') == 'namespace':
						cpp_tree.add_namespace(scope_name)

					# nested enums
					enum_tags = [tag for tag in scope.findall('member') if tag.get('kind') in ('enum', 'enumvalue')]
					enum_name = ''
					for tag in enum_tags:
						if tag.get('kind') == 'enum':
							enum_name = rf'{scope_name}::{tag.find("name").text}'
							cpp_tree.add_type(enum_name)
						else:
							assert enum_name
							cpp_tree.add_enum_value(rf'{enum_name}::{tag.find("name").text}')

					# nested typedefs
					typedefs = [tag for tag in scope.findall('member') if tag.get('kind') == 'typedef']
					for typedef in typedefs:
						cpp_tree.add_type(rf'{scope_name}::{typedef.find("name").text}')

			# some other compound definition
			else:
				compounddef = xml.getroot().find('compounddef')
				assert compounddef is not None
				compoundname = compounddef.find('compoundname')
				assert compoundname is not None
				assert compoundname.text

				# merge user-defined sections with the same name
				if compounddef.get('kind') in ('namespace', 'class', 'struct', 'enum', 'file'):
					sectiondefs = [s for s in compounddef.findall('sectiondef') if s.get('kind') == "user-defined"]
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
								compounddef.remove(section)
								changed = True

				# namespaces
				if compounddef.get('kind') == 'namespace' and context.inline_namespaces:
					for nsid in inline_namespace_ids:
						if compounddef.get("id") == nsid:
							compounddef.set("inline", "yes")
							changed = True
							break

				# dirs
				if compounddef.get('kind') == "dir" and context.implementation_headers:
					innerfiles = compounddef.findall('innerfile')
					for innerfile in innerfiles:
						if innerfile.get('refid') in implementation_header_mappings:
							compounddef.remove(innerfile)
							changed = True

				# files
				if compounddef.get('kind') == 'file':

					# simplify the XML by removing unnecessary junk
					for tag in ('includes', 'includedby', 'incdepgraph', 'invincdepgraph'):
						tags = compounddef.findall(tag)
						if tags:
							for t in tags:
								compounddef.remove(t)
								changed = True

					# get any macros for the syntax highlighter
					define_sections = [tag for tag in compounddef.findall('sectiondef') if tag.get('kind') == r'define']
					for define_section in define_sections:
						defines = [tag for tag in define_section.findall('memberdef') if tag.get('kind') == r'define']
						for define in defines:
							# if (define.find('briefdescription').text.strip()
							# 		or define.find('detaileddescription').text.strip()
							# 		or define.find('inbodydescription').text.strip()):
							macro = define.find('name').text
							if not tentative_macros.fullmatch(macro):
								macros.add(macro)

					# rip the good bits out of implementation headers
					if context.implementation_headers:
						if compounddef.get("id") in implementation_header_mappings:
							hid = implementation_header_mappings[compounddef.get("id")][2]
							innernamespaces = compounddef.findall('innernamespace')
							if innernamespaces:
								implementation_header_innernamespaces[hid] = implementation_header_innernamespaces[hid] + innernamespaces
								extracted_implementation = True
								for tag in innernamespaces:
									compounddef.remove(tag)
									changed = True
							sectiondefs = compounddef.findall('sectiondef')
							if sectiondefs:
								implementation_header_sectiondefs[hid] = implementation_header_sectiondefs[hid] + sectiondefs
								extracted_implementation = True
								for tag in sectiondefs:
									compounddef.remove(tag)
									changed = True

			if changed:
				write_xml_to_file(xml, xml_file)

		# add to syntax highlighter
		context.highlighting.namespaces.add(cpp_tree.matcher(CppTree.NAMESPACES))
		context.highlighting.types.add(cpp_tree.matcher(CppTree.TYPES))
		context.highlighting.enums.add(cpp_tree.matcher(CppTree.ENUM_VALUES))
		for macro in macros:
			context.highlighting.macros.add(macro)

		# merge extracted implementations
		if extracted_implementation:
			for (hp, hfn, hid, impl) in implementation_header_data:
				xml_file = Path(context.xml_dir, f'{hid}.xml')
				print(f'Merging implementation nodes into {xml_file}')
				xml = etree.parse(str(xml_file), parser=xml_parser)
				compounddef = xml.getroot().find('compounddef')
				changed = False

				innernamespaces = compounddef.findall('innernamespace')
				for new_tag in implementation_header_innernamespaces[hid]:
					matched = False
					for existing_tag in innernamespaces:
						if existing_tag.get('refid') == new_tag.get('refid'):
							matched = True
							break
					if not matched:
						compounddef.append(new_tag)
						innernamespaces.append(new_tag)
						changed = True

				sectiondefs = compounddef.findall('sectiondef')
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
						compounddef.append(new_section)
						sectiondefs.append(new_section)
						changed = True

				if changed:
					write_xml_to_file(xml, xml_file)

	# delete the impl header xml files
	if 1 and context.implementation_headers:
		for hdata in implementation_header_data:
			for (ip, ifn, iid) in hdata[3]:
				delete_file(Path(context.xml_dir, rf'{iid}.xml'))

	# scan through the files and substitute impl header ids and paths as appropriate
	if 1 and context.implementation_headers:
		xml_files = get_all_files(context.xml_dir, any=('*.xml'))
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



__worker_context = None
def _initialize_worker(context):
	global __worker_context
	__worker_context = context



def __postprocess_html_file(path, context=None):
	assert path is not None
	assert isinstance(path, Path)
	assert path.is_absolute()
	assert path.exists()

	if context is None:
		global __worker_context
		context = __worker_context
	assert context is not None
	assert isinstance(context, project.Context)

	print(f'Post-processing {path}')
	changed = False
	doc = soup.HTMLDocument(path)
	for fix in context.fixers:
		if fix(doc, context):
			doc.smooth()
			changed = True
	if (changed):
		doc.flush()
	return changed



def __postprocess_html(context):
	assert context is not None
	assert isinstance(context, project.Context)

	files = get_all_files(context.html_dir, any=('*.html', '*.htm'))
	if not files:
		return

	threads = min(len(files), context.threads, 4)
	
	with ScopeTimer(rf'Post-processing {len(files)} HTML files'):
		context.fixers = (
			fixers.DeadLinksFix()
			, fixers.CustomTagsFix()
			, fixers.CodeBlockFix()
			, fixers.IndexPageFix()
			, fixers.ModifiersFix1()
			, fixers.ModifiersFix2()
			, fixers.AutoDocLinksFix()
			, fixers.LinksFix()
			, fixers.TemplateTemplateFix()
		)

		context.verbose(rf'Post-processing {len(files)} HTML files...')
		if threads > 1:
			with futures.ProcessPoolExecutor(max_workers=threads, initializer=_initialize_worker, initargs=(context,)) as executor:
				jobs = [ executor.submit(__postprocess_html_file, file) for file in files ]
				for future in futures.as_completed(jobs):
					try:
						future.result()
					except:
						executor.shutdown(wait=False, cancel_futures=True)
						raise

		else:
			for file in files:
				__postprocess_html_file(file, context)



#=======================================================================================================================
# RUN
#=======================================================================================================================

def run(config_path='.', output_dir='.', threads=-1, cleanup=True, verbose=False, mcss_dir=None, temp_file_name=None):

	context = project.Context(
		config_path = config_path,
		output_dir = output_dir,
		threads = threads,
		cleanup = cleanup,
		verbose = verbose,
		mcss_dir = mcss_dir,
		temp_file_name = temp_file_name
	)

	with ScopeTimer('All tasks') as all_tasks_timer:

		# delete any leftovers from the previous run
		if 1:
			delete_directory(context.xml_dir)
			delete_directory(context.html_dir)

		# preprocess the doxyfile
		__preprocess_doxyfile(context)
		context.verbose_object(r'Context.warnings', context.warnings)

		# preprocessing the doxyfile creates a temp copy; this is the cleanup block.
		try:

			# run doxygen to generate the xml
			if 1:
				with ScopeTimer('Generating XML files with Doxygen') as t:
					subprocess.run(
						['doxygen', str(context.doxyfile_path)],
						check=True,
						shell=True,
						cwd=context.input_dir
					)

					# remove the local paths from the tagfile since they're meaningless (and a privacy breach)
					if context.tagfile_path is not None and context.tagfile_path.exists():
						text = read_all_text_from_file(context.tagfile_path)
						text = re.sub(r'\n\s*?<path>.+?</path>\s*?\n', '\n', text, re.S)
						with open(context.tagfile_path, 'w', encoding='utf-8', newline='\n') as f:
							f.write(text)

			# fix some shit that's broken in the xml
			if 1:
				with ScopeTimer('Pre-processing XML files') as t:
					__preprocess_xml(context)

			context.verbose_object(r'Context.highlighting', context.highlighting)

			# compile regexes
			# (done here because doxygen and xml preprocessing adds additional values to these lists)
			context.highlighting.namespaces = regex_or(context.highlighting.namespaces, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
			context.highlighting.types = regex_or(context.highlighting.types, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
			context.highlighting.enums = regex_or(context.highlighting.enums, pattern_prefix='(?:::)?')
			context.highlighting.string_literals = regex_or(context.highlighting.string_literals)
			context.highlighting.numeric_literals = regex_or(context.highlighting.numeric_literals)
			context.highlighting.macros = regex_or(context.highlighting.macros)
			context.autolinks = tuple([(re.compile('(?<![a-zA-Z_])' + expr + '(?![a-zA-Z_])'), uri) for expr, uri in context.autolinks])

			# run m.css to generate the html
			if 1:
				with ScopeTimer('Generating HTML files with m.css') as t:
					doxy_args = [str(context.doxyfile_path), '--no-doxygen']
					if context.is_verbose():
						doxy_args.append('--debug')
					run_python_script(
						Path(context.mcss_dir, 'documentation/doxygen.py'),
						*doxy_args,
						cwd=context.input_dir
					)

			# copy extra_files
			for f in context.extra_files:
				copy_file(f, Path(context.html_dir, f.name))

			# delete the xml
			if context.cleanup:
				delete_directory(context.xml_dir)

			# move the tagfile into the html directory
			if context.generate_tagfile:
				shutil.move(str(context.tagfile_path), str(Path(context.output_dir, 'html')))

			# post-process html files
			if 1:
				__postprocess_html(context)

		# delete the temp doxyfile
		finally:
			if context.cleanup:
				delete_file(context.doxyfile_path)



def main():
	verbose = False
	try:
		args = argparse.ArgumentParser(
			description='Generate fancy C++ documentation.',
			formatter_class=argparse.RawTextHelpFormatter
		)
		args.add_argument('config', type=Path, nargs='?', default=Path('.'))
		args.add_argument('--verbose', '-v', action='store_true')
		args.add_argument(
			'--threads',
			type=int,
			nargs='?',
			default=0,
			metavar='N',
			help=r"sets the number of threads used (default: %(default)s (automatic))"
		)
		args.add_argument('--mcss',
			type=Path,
			default=None,
			metavar='<dir path>',
			help=r"overrides the version of m.css used for documentation generation"
		)
		args.add_argument('--nocleanup', action='store_true', help=argparse.SUPPRESS)
		args.add_argument('--temp_file_name', type=str, default=None, metavar='<file name>', help=argparse.SUPPRESS)
		args = args.parse_args()
		verbose = args.verbose
		result = run(
			config_path = args.config,
			output_dir = Path.cwd(),
			threads = args.threads,
			cleanup = not args.nocleanup,
			verbose = verbose,
			mcss_dir = args.mcss,
			temp_file_name = args.temp_file_name
		)
		if result is None or bool(result):
			sys.exit(0)
		else:
			sys.exit(1)
	except Exception as err:
		print_exception(err, include_type=verbose, include_traceback=verbose, skip_frames=1)
		sys.exit(-1)



if __name__ == '__main__':
	main()
