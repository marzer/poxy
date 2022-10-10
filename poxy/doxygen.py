#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with Doxygen.
"""

import subprocess
from lxml import etree
from .utils import *
from . import graph

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
	name = name.replace('\\', '_0c')
	name = name.replace('@', '_0d')
	name = name.replace(']', '_0e')
	name = name.replace('[', '_0f')
	name = name.replace('#', '_0g')
	name = re.sub(r'[A-Z]', lambda m: '_' + m[0].lower(), name)
	return name



def format_for_doxyfile(val):
	if val is None:
		return ''
	elif isinstance(val, str):
		return '"' + val.replace('"', '\\"') + '"'
	elif isinstance(val, Path):
		return format_for_doxyfile(str(val))
	elif isinstance(val, bool):
		return r'YES' if val else r'NO'
	elif isinstance(val, (int, float)):
		return str(val)
	else:
		assert False



#=======================================================================================================================
# Doxyfile
#=======================================================================================================================



class Doxyfile(object):

	def __init__(self, input_path=None, output_path=None, cwd=None, logger=None, doxygen_path=None, flush_at_exit=True):
		self.__logger = logger
		self.__dirty = True
		self.__text = ''
		self.__autoflush = bool(flush_at_exit)

		# doxygen
		self.__cwd = Path.cwd() if cwd is None else coerce_path(cwd).resolve()
		assert_existing_directory(self.__cwd)
		self.__doxygen = r'doxygen' if doxygen_path is None else coerce_path(doxygen_path)

		# the input + output
		self.__input_path = input_path
		if self.__input_path is not None:
			self.__input_path = coerce_path(self.__input_path)
		self.__output_path = output_path
		if self.__output_path is not None:
			self.__output_path = coerce_path(self.__output_path)

		# read in doxyfile
		if self.__input_path is not None:
			if not self.__input_path.is_file():
				raise Error(rf'{self.__input_path} was not a file')
			self.__text = read_all_text_from_file(self.__input_path, logger=self.__logger).strip()
			self.cleanup()  # expands includes

		# ...or generate one
		else:
			result = subprocess.run([str(self.__doxygen), r'-s', r'-g', r'-'],
				check=True,
				capture_output=True,
				cwd=self.__cwd,
				encoding='utf-8')
			self.__text = result.stdout.strip()

		# simplify regex searches by ensuring there's always leading and trailing newlines
		self.__text = f'\n{self.__text}\n'

	def cleanup(self):
		if not self.__dirty:
			return
		if 1:
			log(self.__logger, rf'Invoking doxygen to clean doxyfile')
			result = subprocess.run([str(self.__doxygen), r'-s', r'-u', r'-'],
				check=True,
				capture_output=True,
				cwd=self.__cwd,
				encoding=r'utf-8',
				input=self.__text)
			self.__text = result.stdout.strip()
		self.__dirty = False

	def flush(self):
		self.cleanup()
		if self.__output_path is not None:
			log(self.__logger, rf'Writing {self.__output_path}')
			with open(self.__output_path, 'w', encoding='utf-8', newline='\n') as f:
				f.write(self.__text)

	def hash(self):
		return sha1(self.__text)

	def contains(self, text):
		assert text is not None
		return self.__text.find(text) != -1

	def get_value(self, key, fallback=None):
		pattern = re.compile(rf'\n\s*{key}\s*=(.*?)\n', flags=re.S)
		text = self.__text
		m = pattern.search(text)
		while m:
			# doxygen allows values to appear multiple times and only accepts the last one, hence the loop
			text = text[m.end():]
			n = pattern.search(text)
			if not n:
				break
			m = n
		if m:
			val = m[1].strip(' "')
			return val if val else fallback
		return fallback

	def get_boolean(self, key, fallback=False):
		val = self.get_value(key)
		if val is None:
			return fallback
		return val.upper() == 'YES'

	def append(self, *args, end='\n', sep=' '):
		self.__text = rf'{self.__text}{sep.join(args)}{end}'
		self.__dirty = True
		return self

	def add_value(self, key, value=None):
		if value is not None:
			if isinstance(value, (list, tuple, set)):
				if value:
					for v in value:
						if v is not None:
							self.append(rf'{key:<23}+= {format_for_doxyfile(v)}')
			else:
				self.append(rf'{key:<23}+= {format_for_doxyfile(value)}')
			self.__dirty = True
		return self

	def set_value(self, key, value=None):
		if value is not None and isinstance(value, (list, tuple, set)):
			if not value:
				self.append(rf'{key:<23}=')
			else:
				first = True
				for v in value:
					if first:
						self.append(rf'{key:<23}=  {format_for_doxyfile(v)}')
					else:
						self.add_value(key, v)
					first = False
		else:
			self.append(rf'{key:<23}=  {format_for_doxyfile(value)}')
		self.__dirty = True
		return self

	def get_text(self):
		return self.__text

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if traceback is None and self.__autoflush:
			self.flush()



#=======================================================================================================================
# XML <=> Graph
#=======================================================================================================================

COMPOUNDS = {r'dir', r'file', r'group', r'page', r'class', r'struct', r'union', r'concept', r'namespace'}
KINDS = {*COMPOUNDS, r'typedef', r'enum', r'enumvalue', r'variable', r'function', r'define'}
KINDS_TO_NODE_TYPES = {
	r'dir': graph.Directory,
	r'file': graph.File,
	r'group': graph.Group,
	r'class': graph.Class,
	r'struct': graph.Struct,
	r'union': graph.Union,
	r'concept': graph.Concept,
	r'namespace': graph.Namespace,
	r'typedef': graph.Typedef,
	r'enum': graph.Enum,
	r'enumvalue': graph.EnumValue,
	r'variable': graph.Variable,
	r'function': graph.Function,
	r'define': graph.Define
}
NODE_TYPES_TO_KINDS = {t: k for k, t in KINDS_TO_NODE_TYPES.items()}



def _to_kind(node_type) -> str:
	if node_type is None:
		return None
	global NODE_TYPES_TO_KINDS
	assert node_type in NODE_TYPES_TO_KINDS
	return NODE_TYPES_TO_KINDS[node_type]



def _to_node_type(kind: str):
	if kind is None:
		return None
	global KINDS_TO_NODE_TYPES
	assert kind in KINDS_TO_NODE_TYPES
	return KINDS_TO_NODE_TYPES[kind]



def _parse_xml_file(g: graph.Graph, path: Path, parser: etree.XMLParser, log_func=None):
	assert g is not None
	assert path is not None
	assert parser is not None

	root = etree.fromstring(read_all_text_from_file(path, logger=log_func).encode(r'utf-8'), parser=parser)

	def extract_qualified_name(elem):
		assert elem is not None
		for tag in (r'qualifiedname', r'compoundname', r'name'):
			n = elem.find(tag)
			if n is not None:
				n = n.text.strip()
			if n:
				return n
		return None

	if root.tag not in (r'doxygenindex', r'doxygen'):
		return

	if not hasattr(g, r'doxygen_version') and root.get(r'doxygen_version'):
		g.doxygen_version = root.get(r'doxygen_version')
	if not hasattr(g, r'doxygen_version') and root.get(r'version'):
		g.doxygen_version = root.get(r'version')

	# <compound>
	# (these are doxygen's version of 'forward declarations')
	for compound in root.findall(r'compound'):
		node = g.get_or_create_node(compound.get(r'refid'))
		node.type = _to_node_type(compound.get(r'kind'))
		node.qualified_name = extract_qualified_name(compound)

	# <compounddef>
	for compound in root.findall(r'compounddef'):
		node = g.get_or_create_node(compound.get(r'id'))
		node.type = _to_node_type(compound.get(r'kind'))
		node.qualified_name = extract_qualified_name(compound)
		node.protection_level = compound.get(r'prot')

		# inners
		for inner_suffix in (r'class', r'namespace', r'concept', r'file', r'dir'):
			for inner_elem in compound.findall(rf'inner{inner_suffix}'):
				inner = g.get_or_create_node(inner_elem.get(r'refid'))
				if inner_suffix == r'class':
					if inner.id.startswith(r'class'):
						inner.type = graph.Class
					elif inner.id.startswith(r'struct'):
						inner.type = graph.Struct
					elif inner.id.startswith(r'union'):
						inner.type = graph.Union
				else:
					inner.type = _to_node_type(inner_suffix)
				inner.qualified_name = inner_elem
				node.connect_to(inner)



def read_graph_from_xml(folder, log_func=None) -> graph.Graph:
	assert folder is not None
	folder = coerce_path(folder).resolve()
	parser = etree.XMLParser(
		remove_blank_text=True,  #
		recover=True,
		remove_comments=True,
		ns_clean=True,
		encoding=r'utf-8'
	)
	g = graph.Graph()
	for path in get_all_files(folder, all=r"*.xml"):
		_parse_xml_file(g=g, path=path, parser=parser, log_func=log_func)
	if not hasattr(g, r'doxygen_version'):
		g.doxygen_version = r'1.9.0'
	return g



def write_graph_to_xml(g: graph.Graph, folder: Path, log_func=None):
	assert folder is not None
	folder.mkdir(exist_ok=True, parents=True)
	parser = etree.XMLParser(
		remove_blank_text=True,  #
		recover=True,
		remove_comments=False,
		ns_clean=True,
		strip_cdata=True
	)

	version = getattr(g, r'doxygen_version', r'1.9.0')

	global COMPOUNDS
	global KINDS_TO_NODE_TYPES
	global NODE_TYPES_TO_KINDS

	def find_containing_file(node):
		nonlocal g
		assert node.type is not graph.File

	# serialize the compound nodes
	for id, node in g:
		if not node:
			continue
		kind = _to_kind(node.type)
		if kind not in COMPOUNDS:
			continue
		path = Path(folder, rf'{node.id}.xml')
		xml = etree.ElementTree(
			etree.XML(
			rf'''<doxygen
						xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
						xsi:noNamespaceSchemaLocation="compound.xsd"
						version="{version}"
						xml:lang="en-US">
					<!-- This file was created by Poxy - https://github.com/marzer/poxy -->
					<compounddef id="{node.id}" kind="{kind}" language="C++">
						<compoundname>{node.qualified_name}</compoundname>
					</compounddef>
				</doxygen>''',
			parser=parser
			)
		)

		compounddef = xml.getroot().find(r'compounddef')
		if node.type not in (graph.Namespace, graph.Directory, graph.File):
			compounddef.set(r'prot', node.protection_level.name.lower())

		# figure out what file this belongs to (if any)
		files = [f.qualified_name for _, f in g.iterator(graph.File) if (f and f is not node and node in f)]
		for f in files:
			elem = etree.SubElement(compounddef, rf'includes')
			elem.set(r'local', r'no')
			elem.text = f

		# add the inners
		for inner_id, inner_node in node.iterator(
			graph.Namespace, graph.Class, graph.Struct, graph.Union, graph.Concept, graph.Directory, graph.File
		):
			if not inner_node:
				continue
			kind = NODE_TYPES_TO_KINDS[inner_node.type]
			if inner_node.type in (graph.Struct, graph.Union):
				kind = r'class'
			inner_elem = etree.SubElement(compounddef, rf'inner{kind}')
			inner_elem.set(r'refid', inner_id)
			if node.type not in (graph.Namespace, graph.Directory, graph.File):
				inner_elem.set(r'prot', inner_node.protection_level.name.lower())
			inner_elem.text = inner_node.qualified_name

		if log_func:
			log_func(rf'Writing {path}')
		xml.write(
			str(path),  #
			encoding=r'utf-8',
			pretty_print=True,
			xml_declaration=True,
			standalone=False
		)
