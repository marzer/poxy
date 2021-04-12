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

_worker_context = None
def _initialize_worker(context):
	global _worker_context
	_worker_context = context



def _preprocess_doxyfile(context):
	assert context is not None
	assert isinstance(context, project.Context)
	
	with doxygen.Doxyfile(context.doxyfile_path, context=context, temp=True, temp_file_name=context.temp_file_name) as f:
		context.doxyfile_path = f.path

		# .. do stuff



def _preprocess_xml(context):
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
	write_xml_to_file = lambda x, f: x.write(f, encoding='utf-8', xml_declaration=True, pretty_print=pretty_print_xml)

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
		for xml_file in xml_files:
			print(f'Pre-processing {xml_file}')
			xml = etree.parse(str(xml_file), parser=xml_parser)
			changed = False
			
			# the doxygen index
			if xml.getroot().tag == 'doxygenindex':
				scopes = [tag for tag in xml.getroot().findall('compound') if tag.get('kind') in ('namespace', 'class', 'struct', 'union')]
				for scope in scopes:
					scope_name = scope.find('name').text
					if scope.get('kind') in ('class', 'struct', 'union'):
						context.highlighting.types.add(scope_name)
					elif scope.get('kind') == 'namespace':
						context.highlighting.namespaces.add(scope_name)
					# nested enums
					enums = [tag for tag in scope.findall('member') if tag.get('kind') in ('enum', 'enumvalue')]
					enum_name = ''
					for enum in enums:
						if enum.get('kind') == 'enum':
							enum_name = rf'{scope_name}::{enum.find("name").text}'
							context.highlighting.types.add(enum_name)
						else:
							assert enum_name
							context.highlighting.enums.add(rf'{enum_name}::{enum.find("name").text}')
					# nested typedefs
					typedefs = [tag for tag in scope.findall('member') if tag.get('kind') == 'typedef']
					for typedef in typedefs:
						context.highlighting.types.add(rf'{scope_name}::{typedef.find("name").text}')

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

				# header files
				if compounddef.get('kind') == 'file' and context.implementation_headers:
					# remove junk not required by m.css
					for tag in ('includes', 'includedby', 'incdepgraph', 'invincdepgraph'):
						tags = compounddef.findall(tag)
						if tags:
							for t in tags:
								compounddef.remove(t)
								changed = True

					# rip the good bits out of implementation headers
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



def _postprocess_html_file(path, context=None):
	assert path is not None
	assert isinstance(path, Path)
	assert path.is_absolute()
	assert path.exists()

	if context is None:
		global _worker_context
		context = _worker_context
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



def _postprocess_html(context):
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
				jobs = [ executor.submit(_postprocess_html_file, file) for file in files ]
				for future in futures.as_completed(jobs):
					try:
						future.result()
					except:
						executor.shutdown(wait=False, cancel_futures=True)
						raise

		else:
			for file in files:
				_postprocess_html_file(file, context)



#=======================================================================================================================
# RUN
#=======================================================================================================================

def run(config_path='.', threads=-1, cleanup=True, cwd='.', verbose=False, mcss_dir=None, temp_file_name=None):

	context = project.Context(
		config_path = config_path,
		threads = threads,
		cleanup = cleanup,
		cwd = cwd,
		verbose = verbose,
		mcss_dir = mcss_dir,
		temp_file_name = temp_file_name
	)

	with ScopeTimer('All tasks') as all_tasks_timer:

		# delete any leftovers from the previous run
		if 1:
			delete_directory(context.xml_dir)
			delete_directory(context.html_dir)

		# copy the doxyfile to preprocess it separately
		_preprocess_doxyfile(context)
		try:

			# run doxygen to generate the xml
			if 1:
				with ScopeTimer('Generating XML files with Doxygen') as t:
					subprocess.run(
						['doxygen', str(context.doxyfile_path)],
						check=True,
						shell=True,
						cwd=context.cwd
					)

			# fix some shit that's broken in the xml
			if 1:
				with ScopeTimer('Pre-processing XML files') as t:
					_preprocess_xml(context)

			# compile regexes
			# (done here because doxygen and xml preprocessing adds additional values to these lists)
			context.highlighting.namespaces = regex_or(context.highlighting.namespaces, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
			context.highlighting.types = regex_or(context.highlighting.types, pattern_prefix='(?:::)?', pattern_suffix='(?:::)?')
			context.highlighting.enums = regex_or(context.highlighting.enums, pattern_prefix='(?:::)?')
			context.highlighting.string_literals = regex_or(context.highlighting.string_literals)
			context.highlighting.numeric_literals = regex_or(context.highlighting.numeric_literals)
			context.highlighting.macros = regex_or(context.highlighting.macros)
			context.autolinks = tuple([(re.compile('(?<![a-zA-Z_])' + expr + '(?![a-zA-Z_])'), uri) for expr, uri in context.autolinks])

			# run doxygen.py (m.css) to generate the html
			if 1:
				with ScopeTimer('Generating HTML files with m.css') as t:
					doxy_args = [str(context.doxyfile_path), '--no-doxygen']
					if context.is_verbose():
						doxy_args.append('--debug')
					run_python_script(
						Path(context.mcss_dir, 'documentation/doxygen.py'),
						*doxy_args,
						cwd=context.cwd
					)
				
			# copy additional files
			if 1:
				copy_file(Path(context.mcss_dir, 'css/m-dark+documentation.compiled.css'), Path(context.html_dir, 'm-dark+documentation.compiled.css'))
				copy_file(Path(context.data_dir, 'dox.css'), Path(context.html_dir, 'dox.css'))
				copy_file(Path(context.data_dir, 'github-icon.png'), Path(context.html_dir, 'github-icon.png'))

			# delete the xml
			if context.cleanup:
				delete_directory(context.xml_dir)

			# post-process html files
			if 1:
				_postprocess_html(context)

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
